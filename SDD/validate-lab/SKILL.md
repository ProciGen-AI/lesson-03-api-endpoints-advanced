---
name: validate-lab
description: Validate a student's finished rebuild of Lesson 3 exercise 03 (validate-and-retry) against the reference lab. Scores the build out of 100 (can exceed 100 if it beats the reference), reports what's missing, weaker, or better per check, and offers a cheat prompt to close the gap.
---

# Validate Lab — Lesson 3, exercise 03 (validate + retry)

Score a finished `03-validate-and-retry.py` against the reference build — out of
100 — and report where it's missing, weaker, or better.

## What you're validating

The student's job was to build one script that (1) gets **tool-forced structured
output** matching `data/call_summary_schema.json`, (2) **validates** that output
against the schema, and (3) **retries** the call on failures worth retrying, with
backoff. The interesting, load-bearing decisions are in (2) and (3); (1) is the
foundation they were given.

## Locate the two builds

You're running from the lesson's **reference repo**, inside its `SDD/` folder — so
the answer key is local (`../code/`) and the student's build lives in a separate repo.

- **Student build:** the student built in a **separate** clean repo (the `…-sdd`
  repo they cloned). **Ask them for the path to it**, then read
  `<their-path>/03-validate-and-retry.py` — it reads its inputs from
  `<their-path>/data/call1.txt` and `<their-path>/data/call_summary_schema.json`.
  If they've `cd`'d into that repo the path may just be `.`; if there's more than
  one `.py` there, ask which is theirs.
- **Reference build:** `../code/03-validate-and-retry.py` — the worked answer
  sitting beside this `SDD/` folder in the same reference repo (its data is at
  `../code/data/`). If `../code/` isn't there, tell the student you're validating
  structure-and-behavior only, and skip the side-by-side semantic comparison.

---

## Check 1 — Structural / behavioral comparison (40 pts)

Read both files and confirm the student's build has the load-bearing pieces.
Award points; note anything missing concretely.

- **Tool-forced structured output (8):** declares one tool whose `inputSchema` is
  the loaded schema, and sets `toolChoice` to force that tool. Reads the result
  out of the `toolUse` block (not `text`), and raises if no tool call came back.
- **Schema loaded from the file (4):** `data/call_summary_schema.json` is read at
  runtime, not copy-pasted inline. (Inline is weaker — note it but don't fail it.)
- **Validation against the schema (12):** the returned object is validated against
  the schema *before* it's trusted, using a real JSON Schema validator (e.g.
  `jsonschema`) bound to the draft the file declares
  (`https://json-schema.org/draft/2020-12/schema` → `Draft202012Validator`). A
  validator that ignores the draft, or a hand-rolled "check a couple of keys"
  pass, is weaker — it won't catch enum/`additionalProperties`/`minItems`
  violations. Score on how completely it enforces the schema.
- **Retry with backoff (12):** the call is wrapped so it retries on a *defined set*
  of failures, with exponential (or at least incremental) backoff and a cap on
  attempts. Using `tenacity` is the reference path; a correct hand-rolled loop is
  fine and can score full marks.
- **A retry predicate that discriminates (4):** retries are gated by a predicate
  that distinguishes retryable from non-retryable failures — **not** a blanket
  "retry on any Exception." Blanket retry loses most of these points.
- **Config from env + dotenv (bonus, up to +3):** reads `BEDROCK_MODEL_ID` /
  `AWS_REGION` from the environment, loads `.env` via `find_dotenv()`, and fails
  with a clear message when the model ID is unset.

## Check 2 — Deterministic behavior (40 pts)

These have knowable answers and don't depend on model wording, so they're
**automated** by `run_checks.py` (next to this skill). Run it:

```bash
python validate-lab/run_checks.py <their-path>   # their build dir, or its .py
# no path → self-tests the reference; --skip-live drops the real-Bedrock check
```

It imports the student's build, feeds it crafted model output through a **stub
`boto3` client** (so 2a/2b make **no** API calls), exercises the cases below, and
prints a PASS/FAIL table with a per-check detail line (exit 0 = all passed). Score
this section from that table. If a block **SKIP**s — the harness couldn't find the
student's summarize fn or retry predicate by name (see the CONFIG block atop
`run_checks.py`) — reconcile the names there, or fall back to checking that block
by hand.

**2a. The validator actually enforces the schema (16).** The harness injects four
single-rule violations from the real schema — a missing required key (`sentiment`),
a bad `enum` (`sentiment: "angry"`), an extra key under `additionalProperties:
false` (`participants.foo`), and an empty `main_topics` (`minItems: 1`) — and
asserts the build **rejects each** (raises). Full marks when all four `rejects …`
lines PASS; subtract ~4 per FAIL. A `returned without raising` detail means the
validation is too shallow to catch that constraint — name the exact one in your
report.

**2b. Retry classification (16).** The harness calls the build's retry predicate
with sample exceptions and asserts it **discriminates**:
- transient Bedrock errors (`ThrottlingException`, `ServiceUnavailableException`,
  `InternalServerException`, `ModelTimeoutException`) → retried;
- permanent ones (`AccessDeniedException`, `ValidationException`) and unrelated
  exceptions (`KeyError`) → fail fast.
Full marks when those three lines PASS. A blanket predicate surfaces as
`fails fast … → …=True` FAILs — the classic anti-pattern; score low. The
`jsonschema.ValidationError` decision is reported as an **INFO** line, *not* scored:
the reference retries it (a re-roll may self-correct), but a student who
deliberately *doesn't* and can justify it (a deterministically-wrong prompt won't
fix itself) keeps the marks. Penalize only an unconsidered choice.

**2c. Happy path (8).** The harness's `live happy path` line runs the build
end-to-end and asserts it exits 0 and prints schema-valid JSON. This makes a real
Bedrock call, so it needs a working `.env` (`source ../code/setup.sh`); with
`BEDROCK_MODEL_ID` unset it **SKIP**s — award 2c by running the build yourself, or
note it unverified rather than guessing.

## Check 3 — Semantic comparison of model output (20 pts)

Run **both** builds — the student's as `python <their-path>/03-validate-and-retry.py`,
the reference as `python ../code/03-validate-and-retry.py` (each
resolves its own `data/call1.txt`) — capture both JSON summaries, and judge them
for *semantic* equality. The content is model-generated, so don't expect a
literal match. Compare field by field:

- `participants` — same agent (Marcus) and customer (David Miller);
- `sentiment` — same value, or an adjacent defensible one (`mixed`/`positive`);
- `main_topics` / `outcomes` — cover the same real events (premium increase &
  expired protective-device discount, the waived late fee + expired card,
  the escalated open claim, the declined water-backup upsell);
- `action_items` — capture the customer emailing the alarm certificate and the
  agent escalating the claim, with `due` correctly null where no date was given;
- `reference_ids` — include the policy number `88-Delta-4922` (and the claim if
  present).

Award full marks when the student's summary is as faithful as the reference's;
note any field where it's thinner or hallucinates something not in the transcript.

---

## Scoring and report

Total the four buckets into a score **out of 100** — and **let it exceed 100**
when the student's build is genuinely better than the reference. Award the bonus
for real improvements, e.g.:
- a cleaner / more readable retry predicate, or one that also handles the
  "model returned a `text` block instead of `toolUse`" case;
- clearer failure messages when retries are exhausted (distinguishing "gave up
  after transient errors" from "output never validated");
- validating with the streamed/iterative validator to report *all* schema errors
  at once instead of just the first;
- thoughtful handling the reference skips.

Report back, concretely and anchored in *this* exercise (never a generic diff):

1. **Score** (e.g. `92 / 100`, or `108` if it beats the reference) with a one-line
   justification per check.
2. **What's missing or weaker**, per check — name the exact gap ("your validator
   passed the bad-enum object through, so `sentiment: 'angry'` wouldn't be
   caught"; "you retry on `AccessDeniedException`, which will just burn all 6
   attempts on a permissions problem").
3. **What's better than the reference**, if anything — say so explicitly.

Then **offer a cheat prompt** the student can paste to bring their build up to (or
past) the reference — but tell them to use it **only if they're out of time**,
since closing the gap themselves is the whole point. The cheat prompt should name
the specific gaps you found, e.g.:

> "Update `03-validate-and-retry.py`: load `data/call_summary_schema.json` and
> validate the model's `toolUse` output with `jsonschema.Draft202012Validator`
> before returning it. Wrap the call with `tenacity` —
> `stop_after_attempt(6)`, `wait_exponential(multiplier=4, min=4, max=45)` — and a
> `retry_if_exception` predicate that retries on `jsonschema.ValidationError` and
> on `ClientError`s whose code is one of ThrottlingException /
> ServiceUnavailableException / InternalServerException / ModelTimeoutException,
> and fails fast on everything else. In `main`, catch a final `ValidationError`
> and exit non-zero with a clear message."
