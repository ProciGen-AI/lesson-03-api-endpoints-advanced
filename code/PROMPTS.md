# Sample prompts for Lesson 3 — API Endpoints, Advanced

These prompts let you explore and modify the lab using a coding agent. Open this `code/` folder as the agent's working directory; `data/` holds `call1.txt`, the schema files, and `customer_crm.json`.

## Explore — understand what each exercise does

- **"In `01-structured-output.py`, walk through what `toolChoice` does. What would happen if I deleted it? Show me the exact response shape difference."**
  The `toolChoice` line is the load-bearing piece of "structured output" on Bedrock — most students skim past it.

- **"Compare the inline `SCHEMA` dict in `01-structured-output.py` against `data/call_summary_schema.json` used by `02-rich-schema.py`. List the schema features that 02 introduces (nested objects, arrays of objects, enums, nullables, etc.) and what each one buys you."**
  Makes the simple-vs-production schema jump explicit so students see schema design as its own concern.

- **"In `03-validate-and-retry.py`, the `_should_retry` predicate retries on schema-validation errors. Why is that a reasonable thing to do? When would it be a bad idea?"**
  Surfaces the trust-but-verify pattern and its limits (e.g., a deterministically-wrong prompt won't fix itself by retrying).

- **"Compare `02-rich-schema.py` and `03-validate-and-retry.py` side by side. Which lines in 03 are about validation, which are about retrying, and what would break if you kept the retries but dropped the schema validation?"**
  Forces the student to separate the two productionization concerns and see that they're independent layers.

- **"In `03-validate-and-retry.py` the `@retry` decorator sets `reraise=True`. What does tenacity raise when all attempts are exhausted *without* it, and why would that make `main()`'s `except jsonschema.ValidationError` silently miss the failure?"**
  Surfaces the tenacity gotcha: without `reraise`, exhausted retries raise a `RetryError`, not the original exception.

- **"In `04-context-enrichment.py`, the prompt is split into a static `SYSTEM_PROMPT` (in `enrichment_prompts_04.py`) and a dynamic `build_user_prompt()`. Why is that split the whole point of the exercise? What goes in each half, and what breaks if you move CRM data into the system prompt?"**
  Surfaces the static-prefix (cache-friendly) vs. dynamic-payload distinction — the core idea of 04.

- **"In `enrichment_prompts_04.py`, `build_user_prompt()` reads CRM data passed in as a dict. The docstring calls it the 'retrieve → assemble → render' seam. If the CRM came from a live API instead of `customer_crm.json`, what would change in this function — and what wouldn't? Why is that a good property?"**
  Drives home that data access belongs in the builder, and rendering stays pure.

- **"In `04`'s output for `call1.txt`, `cross_sell_opportunities` is the one new field the schema does *not* require — and it often comes back empty. Trace the rules in `SYSTEM_PROMPT` that produced that. Where did the cross-sell reasoning go instead?"**
  Shows the system-prompt rules genuinely shaping output — the model deferred the upsell into `personalized_next_actions` because a claim is open.

## Modify — change the code to see a concept in action

- **"In `01-structured-output.py`, add a fifth field `escalation_needed` (boolean) to the inline `SCHEMA` dict and update the system prompt to ask for it. Run the script. Did the model fill it in correctly for `call1.txt`?"**
  Practices the smallest edit cycle for structured output: add a field, update the prompt, observe.

- **"In `02-rich-schema.py`, edit `data/call_summary_schema.json` to add a required field `urgency` with enum `[low, medium, high]`. Run the script. Did the model fill it in? How would you verify it's not just guessing?"**
  Teaches that the schema is a contract the model will follow — and forces them to think about ground truth.

- **"Add a fifth retry case to `03-validate-and-retry.py`'s `_should_retry`: retry if the model returned a `text` block instead of a `toolUse` block. Force the failure by temporarily changing `toolChoice` to `{\"auto\": {}}`. Verify the retry kicks in."**
  Drives home the difference between `toolChoice: tool` (forced) and `toolChoice: auto` (suggested).

- **"In `04`, edit `data/customer_crm.json` so the customer already holds `auto` and `life` (add them to `products_held`). Re-run. How do `cross_sell_opportunities` and `personalized_next_actions` change? This shows the model reading the CRM, not guessing."**
  The cleanest demonstration that the enrichment is doing work — change the data, watch the recommendations follow.

- **"In `04`, change `customer_crm.json` to a brand-new customer (`tenure_years: 0`, no open claims, no churn signals). Re-run and compare `churn_risk` and the recommendations to the original. What did the CRM context change?"**
  Isolates the effect of the relationship context on the assessment.

- **"In `enrichment_prompts_04.py`, the static `SYSTEM_PROMPT` says 'never recommend a product the customer already holds.' Delete that rule and re-run `04` with the original CRM. Did the model start recommending homeowners (which they hold)? What does that tell you about how load-bearing each rule line is?"**
  Makes the system prompt's rules tangible by removing one and watching the output drift.

- **"In `04-context-enrichment.py`, wrap `analyze_call` in `tenacity` retry the way `03` does. What exceptions should trigger a retry here, and which should fail fast? Explain your `_should_retry` predicate."**
  Connects 04 back to 03's productionization — 04 deliberately left retry out to stay focused.
