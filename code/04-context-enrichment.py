"""Exercise 04 — Enrich the prompt with CRM context.

This is where the lab stops being about "the API call" and starts being about
"what you put in front of the model." Same tool-forced structured-output
mechanic as 01-03 — but now the prompt is built from two halves:

  - a STATIC system prompt (enrichment_prompts_04.SYSTEM_PROMPT) — the analyst's
    role and rules, identical on every call, so it's prompt-cache-friendly; and
  - a DYNAMIC user prompt (enrichment_prompts_04.build_user_prompt) — assembled
    per customer from a CRM record loaded from `data/customer_crm.json`.

The schema also grows: `data/enriched_summary_schema.json` keeps the six
base fields from 02/03 and adds four CRM-driven ones — churn_risk,
churn_risk_rationale, personalized_next_actions, cross_sell_opportunities.
Those last fields are the point of the exercise: the model can only fill them
*well* because it was handed the CRM context. Try running once, then delete a
CRM section from the user prompt (e.g. products_held) and watch
cross_sell_opportunities degrade — that's the enrichment "doing work."

cross_sell_opportunities is the one new field the schema does NOT mark
`required`. When the CRM context implies now is a bad time to cross-sell (the
open claim here), the model legitimately has nothing to suggest — and tool-use
models tend to express "none" by dropping the field rather than emitting an
empty `[]`. Marking it optional lets that valid "nothing right now" outcome
validate, instead of failing the run on a missing field ~1 in 3 times.

This is the "real deal": it carries 03's full robustness — schema validation
AND the discriminating retry (tenacity, with boto's own retries switched off so
we own a single retry layer) — and layers the enrichment on top. Diff it against
03 and the retry machinery is identical; what's new is the two-part prompt and
the four CRM-driven schema fields.
"""

import json
import os
import sys
from pathlib import Path

import boto3
import jsonschema
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv, find_dotenv
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# enrichment_prompts_04.py lives next to this script — the static system prompt
# and the dynamic user-prompt builder.
from enrichment_prompts_04 import SYSTEM_PROMPT, build_user_prompt

load_dotenv(find_dotenv())

DATA_DIR = Path(__file__).resolve().parent / "data"
TRANSCRIPT_PATH = DATA_DIR / "call1.txt"
CRM_PATH = DATA_DIR / "customer_crm.json"
SCHEMA_PATH = DATA_DIR / "enriched_summary_schema.json"


def _should_retry(exc: BaseException) -> bool:
    """Same discriminating retry predicate as 03 — see 03-validate-and-retry.py
    for the line-by-line rationale. Retry the two failures a re-attempt can fix;
    fail fast on everything permanent.

      - jsonschema.ValidationError — wrong shape; a re-roll may come back valid.
      - a *transient* Bedrock error (throttling / server blip) — often clears.

    Everything else (bad creds, unknown model, malformed request, a bug in our
    own code) is permanent, so we return False and let it raise at once.
    """
    if isinstance(exc, jsonschema.ValidationError):
        return True
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        # True -> one of the transient codes -> retry; otherwise fall to fail-fast.
        return code in {
            "ThrottlingException",
            "ServiceUnavailableException",
            "InternalServerException",
            "ModelTimeoutException",
        }
    return False


# Same retry policy as 03: cap at 6 attempts with doubling backoff (4 -> 8 -> 16
# -> 32 -> 45s, the last clamped by max=45), gated on _should_retry, and reraise
# so main()'s `except ValidationError` sees the ORIGINAL error, not a RetryError.
@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=4, min=4, max=45),
    retry=retry_if_exception(_should_retry),
    reraise=True,
)
def analyze_call(transcript: str, crm: dict, schema: dict, model_id: str, region: str) -> dict:
    tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "emit_enriched_summary",
                    "description": "Emit the post-call summary and CRM-informed assessment.",
                    "inputSchema": {"json": schema},
                }
            }
        ],
        "toolChoice": {"tool": {"name": "emit_enriched_summary"}},
    }

    # Single retry layer (the @retry above) — switch off boto's built-in retries
    # so _should_retry is the only thing deciding what to retry (same as 03).
    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"mode": "standard", "max_attempts": 1}),
    )
    response = client.converse(
        modelId=model_id,
        # Static prefix (cacheable) vs. dynamic payload (per-customer) — the
        # whole point of splitting the prompt into a constant + a builder.
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": build_user_prompt(transcript, crm)}]}],
        inferenceConfig={"maxTokens": 1500, "temperature": 0.2},
        toolConfig=tool_config,
    )

    data = None
    for block in response["output"]["message"]["content"]:
        if "toolUse" in block:
            data = block["toolUse"]["input"]
            break
    if data is None:
        raise RuntimeError("Model did not emit a tool call.")

    jsonschema.Draft202012Validator(schema).validate(data)
    return data


def main() -> None:
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not model_id:
        print("Error: BEDROCK_MODEL_ID not set. See 00-aws-setup.md.", file=sys.stderr)
        sys.exit(1)

    transcript = TRANSCRIPT_PATH.read_text(encoding="utf-8").strip()
    crm = json.loads(CRM_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    # Show the dynamic half of the prompt with the transcript omitted, so the
    # CRM enrichment scaffold is readable on its own. The actual call below
    # sends the same prompt WITH the full transcript spliced in.
    print("=== USER PROMPT (CRM enrichment scaffold; transcript omitted) ===")
    print(build_user_prompt("", crm))

    try:
        result = analyze_call(transcript, crm, schema, model_id=model_id, region=region)
    except jsonschema.ValidationError as e:
        # Reached only if all 6 attempts still produced schema-invalid output;
        # reraise=True surfaces the original error, so we exit clean (no traceback).
        print(f"Schema validation failed after retries: {e.message}", file=sys.stderr)
        sys.exit(1)

    print("=== STRUCTURED RESPONSE ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
