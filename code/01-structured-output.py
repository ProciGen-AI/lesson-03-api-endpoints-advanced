"""Exercise 01 — Force the model to emit JSON matching a schema.

Bedrock has no portable "give me JSON in this shape" parameter. The
cross-provider idiom is tool-forced output: declare one tool whose
inputSchema is your target shape, then force the model to call it via
`toolChoice`. The structured data arrives in a `toolUse` block, not `text`.

The schema lives right next to the call — a flat object with four fields
(customer_name, agent_name, summary, resolved). Read the dict, then read
the Converse call: that's the whole structured-output mechanic on one
screen. 02 graduates the schema into its own file and adds nested
objects, arrays of objects, enums, and nullable fields.
"""

import json
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DATA_PATH = Path(__file__).resolve().parent / "data" / "call1.txt"

# The model "reads" this schema as a sub-prompt: field names are semantic
# hints ("customer_name" tells it what belongs in that slot), and types +
# constraints (required, additionalProperties, enum, ...) are instructions.
#
# Notice there are no `description` fields here — we're relying on the field
# names being self-explanatory. In real schemas, each property usually has a
# `description`, and those descriptions act as slot-level mini-prompts. For
# example:
#     "who": {"type": "string", "description": "Party responsible: 'customer', 'agent', or 'company'"}
# would push the model to emit "who": "agent" instead of "who": "Marcus".
# 02 uses descriptions throughout — compare the two and you'll feel the
# difference.
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["customer_name", "agent_name", "summary", "resolved"],
    "properties": {
        "customer_name": {"type": "string"},
        "agent_name": {"type": "string"},
        "summary": {"type": "string"},
        "resolved": {"type": "boolean"},
    },
}


def summarize_structured(transcript: str, model_id: str, region: str) -> dict:
    # `toolChoice` makes this tool the ONLY allowed response — without it
    # the model could still reply with plain text.
    tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": "emit_summary",
                    "description": "Emit the call summary as structured data.",
                    "inputSchema": {"json": SCHEMA},
                }
            }
        ],
        # "toolChoice": {"tool": {"name": "XXXXXX"}} - 'tool' forces this exact tool. 
        # Alternatives: `auto` (model picks a tool or plain text)
        #               `any` (must call some tool, model picks which).
        "toolChoice": {"tool": {"name": "emit_summary"}},
    }

    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.converse(
        modelId=model_id,
        system=[
            {
                "text": (
                    "You summarize customer support calls. Extract the customer "
                    "and agent names, a short summary of the call, and whether "
                    "the customer's issue was fully resolved."
                )
            }
        ],
        messages=[{"role": "user", "content": [{"text": transcript}]}],
        inferenceConfig={"maxTokens": 1024, "temperature": 0.2},
        toolConfig=tool_config,
    )

    # Lab teaching aid: dump the whole Converse response so you can see the
    # envelope your structured data is wrapped in. The part that matters is
    # output.message.content — with tool-forcing the payload is a `toolUse`
    # block whose `input` holds your JSON, NOT a `text` block like 02–04
    # returned. You also see stopReason="tool_use", token usage, and request
    # metadata. Production code drops this and goes straight to the extraction.
    print("=== RAW CONVERSE RESPONSE ===")
    print(json.dumps(response, indent=2, default=str))

    # Bedrock returns a list of content blocks. With tool-forcing, the one we
    # want is the `toolUse` block — its `input` field holds the structured data.
    for block in response["output"]["message"]["content"]:
        if "toolUse" in block:
            return block["toolUse"]["input"]
    raise RuntimeError("Model did not emit a tool call.")


def main() -> None:
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not model_id:
        print("Error: BEDROCK_MODEL_ID not set. See 00-aws-setup.md.", file=sys.stderr)
        sys.exit(1)

    transcript = DATA_PATH.read_text(encoding="utf-8").strip()
    summary = summarize_structured(transcript, model_id=model_id, region=region)

    # The same data after extraction: just your four fields as a clean Python
    # dict, ready to use. Compare it to the `toolUse` block in the raw dump above.
    print("\n=== EXTRACTED STRUCTURED DATA (the toolUse input) ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
