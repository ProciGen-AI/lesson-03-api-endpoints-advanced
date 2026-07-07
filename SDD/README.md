# Lesson 3 — API Endpoints, Advanced · Spec-Driven Build (SDD)

The build-it-yourself half of Lesson 3. You've studied the worked lab in
[`../code/`](../code/); now **rebuild** its culminating script —
`03-validate-and-retry.py` — from a spec, driving a coding agent with `PROMPT.md`,
then score yourself with the `validate-lab` skill.

## How it works

You build in a **separate, clean repo** so your agent starts from a blank slate —
no answer key, no rubric to game, no dependency hints. This `SDD/` folder (inside
the lesson repo) holds the **task** (`PROMPT.md`) and the **validator**
(`validate-lab/`); the building happens in the other repo.

## 1. Get a clean build workspace

```bash
git clone https://github.com/ProciGen-AI/lesson-03-api-endpoints-advanced-sdd.git
cd lesson-03-api-endpoints-advanced-sdd
# copy or create a working .env in this folder (your AWS creds + BEDROCK_MODEL_ID) before the next line
source setup.sh                  # venv + base deps (boto3, python-dotenv) + Bedrock smoke test
mv CLAUDE.md-example CLAUDE.md   # activate the build conventions your agent reads
```

> The build repo is deliberately bare — **setup + data + conventions only**, no
> `PROMPT.md`, no `requirements.txt`, no answer. It has no `.env.example` either:
> **bring your own `.env`** — copy the one you already filled in for this lesson
> (e.g. `cp ../lesson-03-api-endpoints-advanced/.env .env`, adjust the path to
> wherever you cloned the lesson repo).
>
> Your agent will need `jsonschema` and `tenacity` for this lab — let it install
> those as it goes (the base setup only ships boto3 + python-dotenv).
>
> **On Windows?** Run these from Git Bash (easiest via VS Code's integrated terminal).

## 2. Build

Hand your agent the task — **`PROMPT.md` in this `SDD/` folder** (open it and paste
it, or point your agent at it). It's a *partial* spec; the load-bearing decisions
are yours (the `▢ YOU DECIDE` block). Build `03-validate-and-retry.py` in the build
repo, run it, iterate:

```bash
python 03-validate-and-retry.py
```

## 3. Validate

Back here in the lesson repo's `SDD/` folder, invoke the **validate-lab** skill. It
asks for the path to your build repo, then scores your `03-validate-and-retry.py`
against the reference `../code/03-validate-and-retry.py` out of 100 — naming what's
missing / weaker / better, with a cheat prompt if you're out of time.
