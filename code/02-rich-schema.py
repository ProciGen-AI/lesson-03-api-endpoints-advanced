"""Exercise 02 — Scale the schema up to something production-grade.

Diff against 01-structured-output.py: same tool-forced Converse call, same
extraction code. The only things that change are (a) the schema is large
enough that it moves out of the .py file and into `data/`, and (b) the
system prompt grows to match what the new schema demands.

Open `data/call_summary_schema.json` and compare it to the inline SCHEMA
dict in 01. The new features:

  - Nested objects (`participants` has its own required fields).
  - Arrays of objects (`action_items` is a list, each item with its own shape).
  - Nullable fields (`action_items.due` can be a string OR null when no
    due date was mentioned).
  - `minItems: 1` on `main_topics` — empty arrays fail validation.

The model handles all of this through the same tool-forcing mechanism.
This exercise teaches schema *design*; the structured-output mechanic
is identical to 01.

Still no validation here — we add that in 03. For now, trust the model
and inspect the output yourself.
"""

import json
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DATA_PATH = Path(__file__).resolve().parent / "data" / "call1.txt"
SCHEMA_PATH = Path(__file__).resolve().parent / "data" / "call_summary_schema.json"


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

    client = boto3.client("bedrock-runtime", region_name=region)
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
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
