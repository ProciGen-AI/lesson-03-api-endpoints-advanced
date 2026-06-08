"""Prompts for exercise 04 — as code, not a config file.

Two halves, on purpose:

  - SYSTEM_PROMPT is a static module-level constant. It never changes per
    request, so it stays byte-for-byte identical across calls — which is
    exactly what prompt caching rewards (a large, stable prefix). Keep
    anything dynamic OUT of here. (Homework 2 turns this into a real
    `cachePoint`; in production this prompt would live in a versioned prompt
    store such as Bedrock Prompt Management.)

  - build_user_prompt() is a function. This is the dynamic half — the
    "retrieve -> assemble -> render" seam. Today the CRM data is read from a
    JSON file; in a real system this function is where you'd call a CRM API
    or a history-summarization service. Putting that logic in Python (rather
    than inside a self-fetching template) keeps rendering pure and the data
    access testable.

Why prompts-as-Python here instead of a YAML/JSON prompt file: this exercise
is about *programmatic enrichment*, and Python gives the most flexibility for
that — helper functions compose the prompt, and the data-access seam is
explicit. The trade-off is that prompts-in-code aren't editable by non-engineers;
when prompts become content that a non-dev owns, a declarative prompt store wins.
"""

SYSTEM_PROMPT = """You are a post-call analyst for EverGuard Insurance.

For each call you receive two things:
  1. A CRM record for the customer (profile, products held, open claims,
     payment history, recent interactions, and churn signals).
  2. The transcript of the call.

Produce a structured post-call summary AND a CRM-informed assessment, using
the tool you are given. Follow these rules — they are why the CRM record matters:

  - Assess churn risk from the WHOLE relationship: tenure, loyalty tier,
    lifetime value, open-claim friction, and any churn_signals — not just the
    tone of this one call.
  - When churn signals are present, your recommendations are retention-first.
  - Never recommend a product the customer already holds. Cross-sell only from
    products the carrier offers that the customer does NOT currently hold.
  - Do not push an upsell the customer has deferred, or any upsell, while a
    claim is open and unresolved — note the better moment instead.
  - Ground every rationale in a SPECIFIC CRM fact or transcript moment. No
    generic advice.
"""


def _format_open_claims(crm: dict) -> str:
    claims = crm.get("open_claims") or []
    if not claims:
        return "  none on file"
    lines = []
    for c in claims:
        lines.append(
            f"  - {c['claim_id']}: {c['type']} "
            f"(status: {c['status']}, ~${c['estimate_usd']:,}, {c['opened_days_ago']}d old)"
        )
    return "\n".join(lines)


def _format_history(crm: dict) -> str:
    interactions = crm.get("recent_interactions") or []
    if not interactions:
        return "  no prior interactions on file"
    return "\n".join(
        f"  - {i['date']} ({i['channel']}): {i['summary']}" for i in interactions
    )


def build_user_prompt(transcript: str, crm: dict) -> str:
    """Assemble the dynamic user turn from CRM context + the call transcript.

    This is the enrichment seam. Every field below changes per customer, so it
    belongs in the user message, not the cached system prompt.
    """
    held = ", ".join(crm["products_held"])
    offered = ", ".join(crm["products_offered_by_carrier"])
    churn = "; ".join(crm.get("churn_signals") or []) or "none on file"

    return f"""CUSTOMER PROFILE
  Name:           {crm['full_name']}  (id {crm['customer_id']}, policy {crm['policy_number']})
  Tenure / tier:  {crm['tenure_years']} years, {crm['loyalty_tier']}
  Lifetime value: ${crm['lifetime_value_usd']:,}
  Products held:  {held}
  Carrier offers: {offered}
  Payment:        {crm['payment']['history']}; {crm['payment']['recent_issue']}
  Preferred contact: {crm['preferred_contact']}
  Account note:   {crm['account_note']}

OPEN CLAIMS
{_format_open_claims(crm)}

RECENT INTERACTIONS (most recent first)
{_format_history(crm)}

CHURN SIGNALS
  {churn}

CALL TRANSCRIPT
{transcript}
"""


if __name__ == "__main__":
    # Standalone inspect helper: print the user prompt with an EMPTY transcript,
    # so you can see the CRM enrichment scaffold on its own — everything the
    # builder wraps around the call, minus the transcript itself. The module
    # stays import-clean (no I/O at import time); only this demo reads the file.
    #   python enrichment_prompts_04.py
    import json
    from pathlib import Path

    crm = json.loads(
        (Path(__file__).resolve().parent / "data" / "customer_crm.json").read_text(encoding="utf-8")
    )
    print(build_user_prompt("", crm))
