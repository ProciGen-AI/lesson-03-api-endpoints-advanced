# Homework — Lesson 3 (Structured Output)

One capstone that asks you to take the whole lesson — tool-forcing (01), schema design (02), validate + retry (03) — to a **brand-new domain**, from a blank file. The lab walked you through every step on the call-summary task; here the rails come off and the subject changes, so you can't pattern-match your way through. Budget ~60–90 minutes. Drive it yourself, or hand each step to a coding agent with the starter prompts below.

## Capstone — an AI-subscription advisor

**Goal.** Prove you can *transfer* the lesson, not just reproduce it. You'll build the structured-output core of a different agent — one that recommends which AI product and plan a buyer should purchase — designing your own schema and hardening the call with validation + retry, no reference to copy from. This is a step up from the lab's pure extraction: the model has to *decide* and *justify*, then hand you that decision as machine-reliable JSON. Then you'll have a coding agent stress-test your validation and compare your robustness *pattern* against the lesson's reference.

**What to build.**

**1. The concept + a sample input.** You're building the decision core of an agent that recommends an AI subscription. The **input** is a short free-text profile of a prospective buyer — their role and how they'd use AI; the **output** is a structured `purchase` recommendation.

The buyer falls into one of four segments: **occasional** (a few times a month), **business** (team / work workflows), **designer** (image & creative work), **programmer** (coding / agentic work). You'll get five sample profiles — one buyer each — to run against in step 3.

Your `purchase` output should carry at least:

- `recommended_model` — which AI product, e.g. `chatgpt`, `claude`, `gemini`,
- `plan` — the subscription tier, e.g. `free`, `plus`, `pro`, `ultra`, `max_100`, `max_200`, `team`,
- `user_segment` — the model's read of the buyer (one of the four above),
- `email` — pulled from the profile, **nullable** (`null` when the profile gives none — the model must never invent contact info),
- `reasoning` — why this model + plan fits this buyer.

Pinning down each field's type, plus at least one array or nested object, is step 2.

**2. Design the schema yourself.** This is the core of the exercise — *do not* copy the call-summary schema. Look at `code/data/call_summary_schema.json` for the *shape*, then formalize the `purchase` fields above into a real production schema. At minimum it must use:

- `additionalProperties: false` and a `required` list,
- an **enum** wherever a field has a small, fixed set of valid values — several fields above qualify; spotting which (and nailing down the exact values) is part of the design,
- the **nullable** `email` (`"type": ["string", "null"]`),
- at least one **nested object _or_ array of objects** — e.g. `matched_needs`, an array of `{need, plan_feature}` pairs tying each stated need to the feature that satisfies it,
- a `description` on every field — those act as slot-level mini-prompts (see the note in `code/01-structured-output.py`); here they're how you tell the model what each enum value *means* and when to pick it.

**3. Build the call — structured output + validate + retry.** Force the model to read a buyer profile and emit your `purchase` schema via tool-forcing, validate the output with `jsonschema`, and wrap the call so it retries the *right* failures (schema-invalid output, transient AWS errors) and fails fast on everything else. You're rebuilding the engine of `code/03-validate-and-retry.py` for your own schema — ideally without opening it first.

Run it against these five profiles — they span the segments and deliberately vary (some give an email, some don't; budgets differ), so they exercise different branches of your schema. Watch profile 2 land `email: null`:

> 1. "I'm a freelance UI designer. I use AI most days for moodboards, image generation, and rewriting client emails. Budget's around $40/month. Reach me at jane@studio.design."
> 2. "Honestly I barely use this stuff — maybe twice a month to draft an email or summarize an article. I don't want to pay much, free is ideal. No need to contact me."
> 3. "I run ops at a 30-person marketing agency. I want the whole team on one AI tool for docs, research, and client decks, with admin controls and SSO. Budget isn't the blocker. Bill it to ops@brightwave.io."
> 4. "Staff software engineer — I'm in AI all day for coding, large refactors, and agentic workflows across big repos. I want the most capable model and the highest usage tier; money's no object. dan.k@protonmail.com"
> 5. "Solo content creator. Thumbnails, short scripts, and image edits a few times a week. Around $20/month feels right. hey@reels.tv"

**4. Have the agent stress-test your validation.** Don't just assume validation works — ask your coding agent to feed your validator deliberately broken outputs and confirm each is caught: an **invalid `plan` enum value**, a **missing required field**, and an **extra property**. This is the cheap way to prove your `enum` / `required` / `additionalProperties` constraints actually bite, and that a validation failure routes *into* your retry path rather than slipping past it. Letting the agent construct the bad inputs is the point — your job is to direct it and judge the result, not to hand-write a test harness.

**5. Compare against the reference — the *pattern*, not the *output*.** Now open `code/03-validate-and-retry.py` and ask the agent to compare. Your domain differs, so don't expect a line-by-line match — check that you reproduced the *robustness engineering*:

- a **discriminating** retry predicate (retryable vs. fail-fast), not "retry everything",
- Bedrock's **built-in retries switched off** so retry lives in exactly one place,
- the **right validator + JSON Schema draft** for the `$schema` you declared,
- `reraise=True` so the original error surfaces cleanly after the final attempt.

**Starter prompts.**

> *(schema)* "I'm building an AI-subscription advisor: given a free-text buyer profile, the model recommends a product and plan. Help me design a JSON Schema (draft 2020-12) for the `purchase` output with enums for `recommended_model`, `plan`, and `user_segment` (`occasional` / `business` / `designer` / `programmer`); a nullable `email`; a `reasoning` string; an array of `matched_needs` objects; `additionalProperties: false`; a `required` list; and a `description` on every field. Just the schema for now — no calling code yet."
>
> *(build)* "Now write `homework-advisor.py`: force the model (Bedrock Converse, model id from `BEDROCK_MODEL_ID`) to read a buyer profile and emit a `purchase` recommendation matching this schema via a forced `toolChoice` tool, validate the result with `jsonschema`'s `Draft202012Validator`, and wrap the call with `tenacity` so it retries schema-validation failures and transient Bedrock errors but fails fast on everything else. Turn off boto3's built-in retries. Don't look at the course reference."
>
> *(stress-test)* "Write a small throwaway check that feeds my validator three bad `purchase` objects — an invalid `plan` enum value, a missing required field, and an extra property — and confirm each one raises. I want proof my constraints catch violations and that a validation failure hits my retry path."
>
> *(compare)* "Now compare my script's robustness pattern against `code/03-validate-and-retry.py`. Ignore the schema/domain differences — tell me where my retry classification, built-in-retry handling, validator/draft choice, or `reraise` behavior differs from the reference, and whether mine is correct."

## Stretch (optional) — make the retry loop actually fire

Tighten your schema so the *live model* struggles to satisfy it — drop the obviously-right tier from the `plan` enum, or add a `required` field the profile never provides (a `coupon_code`, say). Run it a few times: watch the retry loop re-roll, then exhaust its attempts and fail *cleanly* (a clear message, not a raw traceback). The point is to confirm the machinery you built in step 3 is real, not decorative.

> "Tighten one field in my schema so the model can't reliably satisfy it from this profile, run the script, and show me the retry attempts firing and the clean final failure after the last attempt."
