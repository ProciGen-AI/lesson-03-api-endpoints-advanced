"""Exercise 03 — Productionize the structured-output call: validate + retry.

Diff against 02-rich-schema.py: same Converse + tool-forcing call with the
same production schema, now wrapped with two pieces of robustness you'd
want before this code touches a real system.

  1. Validate the model's output against the schema with `jsonschema`.
     Tool-forcing strongly constrains the shape, but the model can still
     produce e.g. a wrong enum value or violate `additionalProperties`.
     Trust but verify.

  2. Wrap the call in `tenacity` so YOU own the retry policy, in one place.
     We retry exactly the two failure classes a re-attempt can fix:
       - schema-validation failures: the model returned the wrong shape, and a
         re-roll (temperature > 0) may come back valid.
       - transient service errors: throttling or a server-side blip.
     Everything else (bad credentials, unknown model, malformed request) is
     permanent — we let it raise at once instead of burning retries on it.

We switch off the Bedrock client's own built-in retries (the `Config` below)
so retry lives in exactly ONE place you control: `_should_retry`. Backoff is
exponential so we ease off under throttling instead of hammering the API.
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

load_dotenv(find_dotenv())

DATA_PATH = Path(__file__).resolve().parent / "data" / "call1.txt"
SCHEMA_PATH = Path(__file__).resolve().parent / "data" / "call_summary_schema.json"


def _should_retry(exc: BaseException) -> bool:
    """Classify each failure: is it worth retrying, or should we fail now?

    This is the heart of the exercise. tenacity calls it on every exception the
    wrapped function raises and retries only when it returns True. The skill
    being taught is that *you* decide — per exception — what a re-attempt could
    actually fix. We say yes to exactly two classes:

      - jsonschema.ValidationError — the model returned the wrong shape; a
        re-roll (temperature > 0) may come back valid.
      - a *transient* service error — throttling or a server-side blip that
        often clears on its own.

    Everything else (bad credentials, an unknown model, a malformed request) is
    permanent: it will fail identically every time, so we return False and let
    it raise NOW instead of burning all 6 attempts plus backoff on it.
    """
    if isinstance(exc, jsonschema.ValidationError):
        return True
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        # If `code` is one of these transient codes, the test is True -> retry.
        return code in {
            "ThrottlingException",
            "ServiceUnavailableException",
            "InternalServerException",
            "ModelTimeoutException",
        }
    # Fail fast: returning False means "permanent — don't retry." The
    # non-transient AWS codes above already returned False here; this catch-all
    # treats anything else (a bug in our code, an unexpected exception) the same.
    return False


# A decorator (`@`) wraps the function below to add behavior without changing its body.

# tenacity re-runs this function whenever _should_retry approves the exception:
#   stop    — cap at 6 total attempts, then give up (6 attempts = 5 sleeps).
#   wait    — exponential backoff that DOUBLES each step, clamped to [4s, 45s].
#             The 5 sleeps between the 6 attempts are:
#                 4s -> 8s -> 16s -> 32s -> 45s
#             The 5th is really 64s (4 x 2^4), but the 45s ceiling clamps it —
#             so we ease off under throttling without ever sleeping absurdly
#             long. (multiplier=4 sets the starting step; max=45 the cap.)
#   retry   — gate on _should_retry; an exception it rejects propagates at once.
#   reraise — on the final failed attempt re-raise the ORIGINAL exception (e.g.
#             jsonschema.ValidationError). WITHOUT this, tenacity wraps it in a
#             tenacity.RetryError, and main()'s `except ValidationError` below
#             would miss it — you'd get a raw traceback instead of a clean message.
@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=4, min=4, max=45),
    retry=retry_if_exception(_should_retry),
    reraise=True,
)
def summarize_structured(transcript: str, model_id: str, region: str) -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "emit_summary",
                    "description": "Emit the call summary as structured data.",
                    "inputSchema": {"json": schema},
                }
            }
        ],
        "toolChoice": {"tool": {"name": "emit_summary"}},
    }

    # Retry lives in exactly one place we control — the @retry above — so we
    # switch off the client's own built-in retries (max_attempts=1 = one try,
    # no retries). Every retry decision then runs through _should_retry.
    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"mode": "standard", "max_attempts": 1}),
    )
    response = client.converse(
        modelId=model_id,
        system=[
            {
                "text": (
                    "You are a precise assistant that summarizes call transcripts. "
                    "Extract participants, main topics, outcomes, action items, "
                    "overall sentiment, and any policy/claim/reference IDs."
                )
            }
        ],
        messages=[{"role": "user", "content": [{"text": transcript}]}],
        inferenceConfig={"maxTokens": 1024, "temperature": 0.2},
        toolConfig=tool_config,
    )

    data = None
    for block in response["output"]["message"]["content"]:
        if "toolUse" in block:
            data = block["toolUse"]["input"]
            break
    if data is None:
        raise RuntimeError("Model did not emit a tool call.")

    # Trust-but-verify: tool-forcing constrains the shape, but the model can
    # still break a rule (wrong enum, missing required field, extra property).
    # Draft202012Validator matches the $schema declared in the schema file;
    # .validate() raises jsonschema.ValidationError on the FIRST violation.
    # _should_retry treats that as retryable, so a failure here re-rolls the
    # whole call instead of returning bad data.
    jsonschema.Draft202012Validator(schema).validate(data)
    return data


def main() -> None:
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not model_id:
        print("Error: BEDROCK_MODEL_ID not set. See 00-aws-setup.md.", file=sys.stderr)
        sys.exit(1)

    transcript = DATA_PATH.read_text(encoding="utf-8").strip()
    try:
        summary = summarize_structured(transcript, model_id=model_id, region=region)
    except jsonschema.ValidationError as e:
        # Reached only if all 6 attempts produced schema-invalid output. Because
        # the decorator sets reraise=True, the original ValidationError surfaces
        # here (not a tenacity.RetryError), so we exit cleanly with the failing
        # rule instead of dumping a traceback.
        print(f"Schema validation failed after retries: {e.message}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
