# Lesson 3 — API Endpoints, Advanced (Structured Output & Context)

This lesson picks up where Lesson 2 left off. Lesson 2 was about **calling** the model — the endpoint, the SDK, the prompt, streaming, reasoning. This one is about the harder, more useful half: getting **machine-reliable structured data out** of the model, and **engineering the context you feed in**. Four exercises that build on each other, all on the same call-summary task so you can diff between them.

> **Prerequisite: Lesson 2 (API Endpoints).** You should be comfortable making a Bedrock Converse call, the `system`/`user` split, and reading a response. The AWS setup carries over — if you're starting fresh from this lesson, `code/00-aws-setup.md` walks you through it again.

Everything lives under [`code/`](code/): a setup walkthrough (`00-aws-setup.md`), then four runnable exercises.

## The exercises

- **00 — [`00-aws-setup.md`](code/00-aws-setup.md)** — One-time AWS/Bedrock setup (same as Lesson 2 — skip if your `.env` already works). No Python.
- **01 — `01-structured-output.py`** — Force the model to emit JSON matching a schema via **tool-forcing**. Tiny inline schema (4 flat fields) so the mechanic is the whole lesson.
- **02 — `02-rich-schema.py`** — Same mechanic as 01, but the schema graduates to a production shape: nested objects, arrays of objects, enums, nullable fields, `minItems`. Teaches schema design.
- **03 — `03-validate-and-retry.py`** — Productionize 02: validate the model's output with `jsonschema`, and wrap the call with `tenacity` to retry on transient AWS errors or validation failures (with a discriminating predicate).
- **04 — `04-context-enrichment.py`** — Enrich the prompt with **CRM context**. A static system prompt (cache-friendly) plus a dynamic, per-customer user prompt built in `enrichment_prompts_04.py`, producing an extended schema whose new fields (churn risk, next actions, cross-sell) only fill well *because* of the context.

The arc: 01 establishes the tool-forcing mechanic → 02 grows the schema into a production contract → 03 hardens it (validate + retry) → 04 shifts the focus from *the schema* to *what you feed the model* — context engineering.

## Learning objectives

By the end of this lesson you should be able to answer:

- How do you force a model to return JSON matching a schema on Bedrock (and why is it tool-forcing, not a "JSON mode")?
- What does a production schema look like — nested objects, arrays, enums, nullable fields, `additionalProperties: false`?
- How do you validate model output against a schema, and how do you retry intelligently (which failures are worth retrying vs. fail-fast)?
- How does enriching the prompt with external context (a CRM record) change the output, and where does that context-assembly logic belong in your code?

## Prerequisites

- **Lesson 2 (API Endpoints)** — this lesson assumes you can already make and read a Converse call.
- Python 3.11+
- An AWS account with Bedrock model access (`00-aws-setup.md` walks you through it)

## How to run

> **On Windows?** Run every lab command from **Git Bash**, not PowerShell or cmd — they can't source a `.sh` file. Easiest: open this project in VS Code and set the integrated terminal to Git Bash (`Ctrl+Shift+P` → *Terminal: Select Default Profile* → *Git Bash*). No Git Bash? Install [Git for Windows](https://git-scm.com/download/win), or use [WSL](https://learn.microsoft.com/windows/wsl/install). Started in PowerShell by mistake? Run `.\setup.ps1` and it'll point you to Git Bash. macOS/Linux: the commands work as-is.

Confirm Bedrock works (or re-confirm from Lesson 2) by sourcing `setup.sh` from the `code/` folder:

```bash
git clone https://github.com/ProciGen-AI/lesson-03-api-endpoints-advanced.git
cd lesson-03-api-endpoints-advanced/code
source setup.sh
```

That leaves you in `code/` — run each exercise from there:

```bash
python 01-structured-output.py
python 02-rich-schema.py
python 03-validate-and-retry.py
python 04-context-enrichment.py
```

Prefer exploring by chatting with a coding agent? [`code/PROMPTS.md`](code/PROMPTS.md) has sample explore-and-modify prompts for each exercise.

## Build it yourself (spec-driven rebuild)

Once you've studied the lab above, practice *producing* the culminating exercise from a spec rather than reading it — see **[`SDD/`](SDD/)**. You build in a separate **clean** repo (so your coding agent gets no answer key and no rubric to game), driven by [`SDD/PROMPT.md`](SDD/PROMPT.md), then score yourself with the `validate-lab` skill from `SDD/`.

Start here: **[`SDD/README.md`](SDD/README.md)**.

## Homework

[`homework/README.md`](homework/README.md) is a single capstone — an **AI-subscription advisor** you build from a blank file — that takes the whole lesson (tool-forcing, schema design, validate + retry) to a brand-new domain, plus an optional stretch. The transfer test: design your own schema and rebuild the engine of `03` for it, then have a coding agent stress-test it and compare it against the reference.
