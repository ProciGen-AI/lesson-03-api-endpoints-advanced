#!/usr/bin/env python3
"""Deterministic checks for the Lesson 3 culminating build (validate + retry).

The culminating exercise is `03-validate-and-retry.py`: a tool-forced
structured-output call wrapped with (a) jsonschema validation of the model's
output and (b) a *discriminating* retry. Those two are the load-bearing skills,
so this harness asserts them WITHOUT a real Bedrock call — it imports the build
and feeds it crafted model output through a stub `boto3` client:

  - inject VALID output   -> the build extracts + validates it and returns it.
  - inject INVALID output  -> the build's validation must REJECT it (raise).
  - call the retry predicate with sample exceptions -> transient retries;
    permanent / unrelated fail fast.

Only the final happy-path check makes a real (cheap) Bedrock call; it auto-skips
when BEDROCK_MODEL_ID isn't set. (`time.sleep` is patched out during the
injection checks, so a build that retries invalid output doesn't actually wait
through its backoff.)

This is grey-box: it imports the student's module and locates their summarize
function + retry predicate by name (see the CONFIG block). When a build's shape
defeats that, the affected checks SKIP with a clear message instead of failing —
fall back to the by-hand steps in SKILL.md.

Usage:
    python run_checks.py [BUILD] [--ref-dir DIR] [--skip-live]

BUILD is the student's build file or its folder; with no args it self-tests the
reference (../../code/03-validate-and-retry.py).
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import jsonschema
from botocore.exceptions import ClientError

# ===== CONFIG — reconcile with SDD/PROMPT.md and the reference =================
BUILD_FILE = "03-validate-and-retry.py"      # default student script name
# The build's retry predicate — the function tenacity (or a hand loop) gates on.
PREDICATE_NAMES = ("_should_retry", "should_retry", "_is_retryable", "is_retryable", "_retryable")
# The build's "make one structured call and return the validated dict" function.
SUMMARIZE_NAMES = ("summarize_structured", "summarize_call_structured", "summarize_call", "summarize", "get_summary")
# Bedrock error codes the predicate SHOULD retry (transient) ...
TRANSIENT_CODES = ("ThrottlingException", "ServiceUnavailableException", "InternalServerException", "ModelTimeoutException")
# ... and codes it must NOT retry (permanent / deterministic — a re-attempt fails identically).
PERMANENT_CODES = ("AccessDeniedException", "ValidationException")
SCHEMA_REL = "data/call_summary_schema.json"
TRANSCRIPT_REL = "data/call1.txt"
TOOL_NAME = "emit_summary"                    # only used to shape the stub response
# =============================================================================

HERE = Path(__file__).resolve().parent
DEFAULT_REF_DIR = HERE.parent.parent / "code"   # SDD/validate-lab -> lesson/code

# A model output that satisfies call_summary_schema.json. Each "bad" case below
# is this dict with exactly ONE rule broken, so a failing check pinpoints which
# constraint the build's validation missed.
GOOD_OUTPUT = {
    "participants": {"agent_name": "Marcus", "customer_name": "David Miller"},
    "main_topics": ["unexpected premium increase"],
    "outcomes": ["waived the late fee"],
    "action_items": [{"who": "agent", "action": "escalate the open claim", "due": None}],
    "sentiment": "positive",
    "reference_ids": ["88-Delta-4922"],
}


def bad_outputs():
    """Four single-rule violations drawn from the real schema."""
    missing = copy.deepcopy(GOOD_OUTPUT); del missing["sentiment"]
    bad_enum = copy.deepcopy(GOOD_OUTPUT); bad_enum["sentiment"] = "angry"
    extra = copy.deepcopy(GOOD_OUTPUT); extra["participants"]["foo"] = "bar"
    empty_topics = copy.deepcopy(GOOD_OUTPUT); empty_topics["main_topics"] = []
    return [
        ("missing required key (drop `sentiment`)", missing),
        ('bad enum value (`sentiment: "angry"`)', bad_enum),
        ("extra key under additionalProperties:false (`participants.foo`)", extra),
        ("empty `main_topics` (violates minItems:1)", empty_topics),
    ]


class StubClient:
    """Stands in for a bedrock-runtime client: every .converse() returns the same
    crafted toolUse response and counts calls (so we can see retries happen)."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def converse(self, **kwargs):
        self.calls += 1
        return {
            "output": {"message": {"content": [
                {"toolUse": {"name": TOOL_NAME, "toolUseId": "tu_1", "input": self.payload}},
            ]}},
            "stopReason": "tool_use",
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        }


def load_build(path: Path):
    spec = importlib.util.spec_from_file_location("student_build", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # safe: build guards real work behind __main__
    return mod


def find_callable(mod, names):
    for n in names:
        fn = getattr(mod, n, None)
        if callable(fn):
            return n, fn
    return None, None


def client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": f"stub {code}"}}, "Converse")


def call_summarize(fn, transcript: str):
    """Call the build's summarize fn, tolerating signature differences. The stub
    client makes model_id/region irrelevant, so we pass placeholders for them."""
    try:
        return fn(transcript)
    except TypeError:
        pass  # needs more than transcript — fill the rest from the signature
    kwargs = {}
    for p in list(inspect.signature(fn).parameters.values())[1:]:
        low = p.name.lower()
        if "model" in low:
            kwargs[p.name] = "stub-model-id"
        elif "region" in low:
            kwargs[p.name] = "us-east-1"
    return fn(transcript, **kwargs)


def probe(predicate, exc):
    """Call the predicate defensively so one crash doesn't sink the other checks."""
    try:
        return predicate(exc), None
    except Exception as e:  # a predicate that blows up on an unexpected exc is itself a finding
        return None, e


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build", nargs="?", default=str(DEFAULT_REF_DIR / BUILD_FILE),
                    help="student build .py (or its folder); default self-tests the reference")
    ap.add_argument("--ref-dir", default=str(DEFAULT_REF_DIR),
                    help="reference code/ dir — source of truth for the schema + transcript")
    ap.add_argument("--skip-live", action="store_true", help="skip the real-Bedrock happy-path check")
    args = ap.parse_args()

    build_path = Path(args.build).resolve()
    if build_path.is_dir():
        build_path = build_path / BUILD_FILE
    if not build_path.is_file():
        print(f"ERROR: build file not found: {build_path}", file=sys.stderr)
        sys.exit(2)

    ref = Path(args.ref_dir).resolve()
    schema = json.loads((ref / SCHEMA_REL).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(GOOD_OUTPUT)  # sanity: our own fixture must be valid
    transcript = (ref / TRANSCRIPT_REL).read_text(encoding="utf-8").strip()

    results: list[tuple[str, str, str]] = []

    def record(name: str, status: str, detail: str = "") -> None:
        results.append((name, status, detail))

    import boto3  # patched per-check below; restored in finally
    try:
        mod = load_build(build_path)
    except Exception as e:
        print(f"ERROR: could not import {build_path.name}: {e!r}", file=sys.stderr)
        sys.exit(2)

    pred_name, predicate = find_callable(mod, PREDICATE_NAMES)
    summ_name, summarize = find_callable(mod, SUMMARIZE_NAMES)

    # ---- Injection checks: validation accepts good / rejects bad (no creds) ------
    if summarize is None:
        record("locate summarize function", "SKIP",
               f"none of {SUMMARIZE_NAMES} found — check extraction/validation by hand")
    else:
        record("locate summarize function", "PASS", f"using `{summ_name}`")
        orig_client = boto3.client
        try:
            stub = StubClient(GOOD_OUTPUT)
            boto3.client = lambda *a, **k: stub
            try:
                with mock.patch("time.sleep"):
                    out = call_summarize(summarize, transcript)
                ok = isinstance(out, dict)
                if ok:
                    validator.validate(out)
                same = isinstance(out, dict) and out == GOOD_OUTPUT
                record("valid model output → accepted & schema-valid", "PASS" if ok else "FAIL",
                       f"returned {type(out).__name__}" + (", matches injected toolUse input" if same else ""))
            except Exception as e:
                record("valid model output → accepted & schema-valid", "FAIL", f"raised {e!r}")

            for label, bad in bad_outputs():
                stub = StubClient(bad)
                boto3.client = lambda *a, **k: stub
                try:
                    with mock.patch("time.sleep"):
                        call_summarize(summarize, transcript)
                    record(f"rejects {label}", "FAIL",
                           f"returned without raising ({stub.calls} call(s)) — validation too shallow")
                except jsonschema.ValidationError:
                    record(f"rejects {label}", "PASS", f"raised ValidationError after {stub.calls} call(s)")
                except Exception as e:
                    record(f"rejects {label}", "FAIL",
                           f"raised {type(e).__name__}, not ValidationError: {e}")
        finally:
            boto3.client = orig_client

    # ---- Retry predicate classification ------------------------------------------
    if predicate is None:
        record("locate retry predicate", "SKIP",
               f"none of {PREDICATE_NAMES} found — inspect retry gating by hand")
    else:
        record("locate retry predicate", "PASS", f"using `{pred_name}`")

        decisions = {c: probe(predicate, client_error(c)) for c in TRANSIENT_CODES}
        ok = all(err is None and val for val, err in decisions.values())
        record("predicate retries transient Bedrock errors", "PASS" if ok else "FAIL",
               ", ".join(f"{c}={'ERR' if e else v}" for c, (v, e) in decisions.items()))

        decisions = {c: probe(predicate, client_error(c)) for c in PERMANENT_CODES}
        ok = all(err is None and not val for val, err in decisions.values())
        record("predicate fails fast on permanent Bedrock errors", "PASS" if ok else "FAIL",
               ", ".join(f"{c}={'ERR' if e else v}" for c, (v, e) in decisions.items()))

        val, err = probe(predicate, KeyError("boom"))
        record("predicate fails fast on unrelated exceptions (e.g. KeyError)",
               "PASS" if err is None and not val else "FAIL",
               f"KeyError={'raised ' + repr(err) if err else val}")

        val, err = probe(predicate, jsonschema.ValidationError("stub"))
        record("predicate's call on jsonschema.ValidationError", "INFO",
               f"{'raised ' + repr(err) if err else val} — reference retries it (True); "
               "a justified False is also defensible (see SKILL.md 2b)")

    # ---- Live happy path (real, cheap Bedrock call) ------------------------------
    if args.skip_live:
        record("live happy path (real Bedrock call)", "SKIP", "--skip-live")
    elif not os.environ.get("BEDROCK_MODEL_ID"):
        record("live happy path (real Bedrock call)", "SKIP",
               "BEDROCK_MODEL_ID unset — source the reference lab's code/setup.sh to enable")
    else:
        try:
            proc = subprocess.run([sys.executable, str(build_path)],
                                  capture_output=True, text=True, timeout=180)
            ok, detail = False, f"exit {proc.returncode}"
            if proc.returncode == 0 and "{" in proc.stdout:
                try:
                    payload = json.loads(proc.stdout[proc.stdout.index("{"):proc.stdout.rindex("}") + 1])
                    validator.validate(payload)
                    ok, detail = True, "exit 0, stdout JSON is schema-valid"
                except (ValueError, jsonschema.ValidationError) as e:
                    detail = f"exit 0 but output not schema-valid: {e}"
            elif proc.returncode != 0:
                detail = f"exit {proc.returncode}: {proc.stderr.strip()[:200]}"
            record("live happy path (real Bedrock call)", "PASS" if ok else "FAIL", detail)
        except subprocess.TimeoutExpired:
            record("live happy path (real Bedrock call)", "FAIL", "timed out after 180s")

    # ---- Report ------------------------------------------------------------------
    print("\n  RESULT  CHECK")
    print("  ------  ----------------------------------------------------------")
    n_pass = n_fail = 0
    for name, status, detail in results:
        n_pass += status == "PASS"
        n_fail += status == "FAIL"
        print(f"  [{status}]  {name}")
        if detail:
            print(f"          → {detail}")
    scored = n_pass + n_fail
    extra = len(results) - scored
    print(f"\n  {n_pass}/{scored} pass/fail checks passed"
          + (f"  ({extra} informational/skipped)" if extra else ""))
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
