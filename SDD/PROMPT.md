<!-- ──────────────────────────────────────────────────────────────────────────
  HOW TO USE THIS FILE  (guidance to you, the student — NOT part of the prompt)

  Everything inside these <!-- ... --> comments is for you. Your editor greys
  them out, so what's left in plain text is the prompt itself.

  1. Rename CLAUDE.md-example -> CLAUDE.md so your agent reads the conventions.
  2. The plain text below is a *partial* prompt. Hand it to your coding agent
     to build 03-validate-and-retry.py.
  3. It's deliberately incomplete. The decisions listed at the bottom are left
     out on purpose — that's the exercise. Work them into the prompt (or into
     follow-up turns with the agent) yourself.
  4. When you think it's done: run `python 03-validate-and-retry.py`, then
     invoke the validate-lab skill to score it against the reference.
─────────────────────────────────────────────────────────────────────────── -->

# Build: 03-validate-and-retry.py

Summarize a customer-support call transcript that matches the provided schema.

Write the script as `03-validate-and-retry.py` at the root of your build repo
(your working directory) — that's where you'll run it from.

<!-- ▢ YOU DECIDE — left out of the prompt on purpose; this is the exercise.
     The filename is the brief: this build has to VALIDATE the model's output
     and RETRY. The prompt above doesn't spell that out — work out the how and
     fold it in:
       - do you validate the output against the schema before trusting it, and
         with which library/validator + which JSON Schema draft?
       - which Bedrock failures are "transient" (worth a retry) vs. ones that
         fail identically every time (fail fast)?
       - is a *validation* failure something you'd retry the model on? justify.
       - backoff curve + how many attempts before you give up?
     Leave them out and you'll build exercise 02 — that gap is exactly what
     validate-lab scores. -->
