"""
StadiumOps AI — the orchestrator.

This is the "smart, dynamic assistant" itself. It does NOT hardcode a
single behaviour: what it does depends on WHO is asking (role) and WHAT
the current state looks like. That's the "logical decision making based
on user context" piece:

  - security      -> always runs the security triage module
  - ops_manager   -> runs crowd_flow + security + concessions (full picture)
  - concessions   -> runs concessions module only
  - fan           -> runs fan_qa module only, grounded in live state

The rule-based engine modules are the source of truth for WHAT to do.
Claude (if an API key is configured) is used only to turn that structured
output into a clear natural-language answer — it never invents facts,
it explains the recommendations it's given. If no API key is set, a
plain-text fallback formatter is used instead, so the assistant is fully
functional offline.
"""
from __future__ import annotations

import os
from typing import Optional

from .engine import crowd_flow, security, concessions, fan_qa
from .state import StadiumState

VALID_ROLES = {"ops_manager", "security", "concessions", "fan"}


def _fallback_format(role: str, recs: list[dict]) -> str:
    """No-API-key text formatter, grouped by priority."""
    if not recs:
        return "All clear — no notable recommendations right now."
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    recs_sorted = sorted(recs, key=lambda r: order.get(r["priority"], 5))
    lines = [f"[{r['priority'].upper()}] {r['action']} ({r['target']}): {r['reason']}" for r in recs_sorted]
    return "\n".join(lines)


def _call_claude(role: str, query: str, recs: list[dict]) -> Optional[str]:
    """Best-effort natural-language explanation layer. Returns None if no
    API key is configured or the call fails, so the caller can fall back."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic  # imported lazily so the package is optional
    except ImportError:
        return None

    system = (
        "You are StadiumOps AI, an assistant for live event operations staff and fans. "
        "You are given a JSON list of recommendations already produced by a rule-based "
        "decision engine (source of truth) for the given role. Do not invent new facts, "
        "gates, incidents or numbers beyond what is provided. Write a concise, actionable "
        "response in plain language appropriate for the given role. Ops/security roles want "
        "terse, prioritized action items. Fans want a short, friendly direct answer."
    )
    user_msg = f"Role: {role}\nQuery: {query or '(status check)'}\nRecommendations: {recs}"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text").strip()
    except Exception:
        return None


def handle_request(role: str, state: StadiumState, query: str = "") -> dict:
    """Main entry point. Returns a dict with the raw recommendations
    (always available, for logging/UI) plus a human-readable `answer`."""
    if role not in VALID_ROLES:
        raise ValueError(f"Unknown role '{role}'. Expected one of {sorted(VALID_ROLES)}")

    snapshot = state.snapshot()
    recs: list[dict] = []

    if role == "ops_manager":
        recs += crowd_flow.evaluate(snapshot)
        recs += security.evaluate(snapshot)
        recs += concessions.evaluate(snapshot)
    elif role == "security":
        recs += security.evaluate(snapshot)
        # ops-relevant crowd context matters for security too (e.g. overcrowding)
        recs += [r for r in crowd_flow.evaluate(snapshot) if r["priority"] in ("critical", "high")]
    elif role == "concessions":
        recs += concessions.evaluate(snapshot)
    elif role == "fan":
        recs += fan_qa.evaluate(snapshot, query)

    answer = _call_claude(role, query, recs) or _fallback_format(role, recs)
    return {"role": role, "query": query, "recommendations": recs, "answer": answer}
