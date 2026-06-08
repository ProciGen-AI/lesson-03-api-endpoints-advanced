# Homework — Lesson 3 (Structured Output & Context)

Three optional extensions that push the lab's concepts further. Each one is a 30–60 minute exercise you can drive yourself or hand to a coding agent using the included prompt hint.

## 1. Stream a structured-output call

**Goal.** See where the `toolUse` data shows up when you *stream* a tool-forced call — structured output and streaming aren't mutually exclusive, but the event shape is different from plain text.

**What to build.** Take `code/01-structured-output.py` and switch `converse` → `converse_stream`, keeping the forced `toolChoice`. The tool's input arrives across `contentBlockDelta` events as a *partial JSON string* (not a dict), in a `toolUse` delta. Accumulate those fragments, parse the assembled JSON at the end, and print it. Compare the event sequence to the plain-text stream you saw in Lesson 2.

**Prompt hint.**
> "Starting from `code/01-structured-output.py`, build `homework-stream-structured.py` that uses `converse_stream` with the same forced `toolChoice`. Iterate the stream; for each `contentBlockDelta` with a `toolUse` field, append `delta['toolUse']['input']` (a partial JSON string) to a buffer. After the stream ends, `json.loads` the buffer and print the object. Note in a comment why you can't parse until the stream completes."

## 2. Report *all* schema violations at once

**Goal.** The reference validator (`.validate()`) raises on the *first* violation. For debugging a flaky model, you often want every problem at once.

**What to build.** In a copy of `code/03-validate-and-retry.py`, replace the single `.validate()` call with `Draft202012Validator(schema).iter_errors(data)`, collect all errors, and print each one's `json_path` + message. Feed it a deliberately broken object (a bad enum *and* a missing required field *and* an extra property) to prove it reports all three, not just the first.

**Prompt hint.**
> "In a copy of `code/03-validate-and-retry.py`, swap `.validate(data)` for `list(Draft202012Validator(schema).iter_errors(data))`. If the list is non-empty, raise (so the retry still fires), but first print each error's `.json_path` and `.message`. Then write a tiny harness that validates a hand-built object breaking three rules at once, and confirm all three are reported."

## 3. Add a new enrichment signal end-to-end

**Goal.** Feel the full "context → schema → output" loop: a new fact in the CRM should be able to change a new field in the structured output.

**What to build.** Add a field to `data/customer_crm.json` (e.g. `"recent_nps": 3`), surface it in `enrichment_prompts_04.py`'s `build_user_prompt()`, and add a matching output field to `data/enriched_summary_schema.json` (e.g. `"detractor_flag"` with a rationale). Re-run `code/04-context-enrichment.py` and confirm the new input actually moves the new output. Then change the NPS to a 9 and watch it flip.

**Prompt hint.**
> "In `04-context-enrichment.py`'s data: add `recent_nps` to `customer_crm.json`, render it in `build_user_prompt()` (in `enrichment_prompts_04.py`), and add a `detractor_flag` boolean (+ `detractor_rationale`) to `enriched_summary_schema.json`. Keep `cross_sell_opportunities` optional. Run it with `recent_nps: 3`, then `recent_nps: 9`, and compare `detractor_flag` and `churn_risk` across the two runs — does the new signal actually move the output?"
