"""
Crowd flow & gate/exit management.

Pure function: dict in (state snapshot) -> list[dict] recommendations out.
No I/O, no randomness -> fully unit-testable with hand-built snapshots.
"""
from __future__ import annotations

DENSITY_RESTRICT = 0.85
DENSITY_CLOSE = 0.97
DENSITY_REOPEN = 0.55


def evaluate(snapshot: dict) -> list[dict]:
    gates = snapshot.get("gates", {})
    recs: list[dict] = []

    open_gates = [g for g in gates.values() if g["status"] != "closed"]
    avg_density = (sum(g["density"] for g in open_gates) / len(open_gates)) if open_gates else 0

    for g in gates.values():
        density = g["density"]

        if density >= DENSITY_CLOSE and g["status"] != "closed":
            recs.append({
                "domain": "crowd_flow",
                "action": "close_gate",
                "target": g["id"],
                "priority": "critical",
                "reason": f"{g['name']} at {density:.0%} capacity — unsafe to keep admitting.",
            })
        elif density >= DENSITY_RESTRICT and g["status"] == "open":
            recs.append({
                "domain": "crowd_flow",
                "action": "restrict_gate",
                "target": g["id"],
                "priority": "high",
                "reason": f"{g['name']} at {density:.0%} capacity — slow intake, redirect overflow.",
            })
        elif density <= DENSITY_REOPEN and g["status"] in ("restricted", "closed"):
            recs.append({
                "domain": "crowd_flow",
                "action": "reopen_gate",
                "target": g["id"],
                "priority": "low",
                "reason": f"{g['name']} back down to {density:.0%} — safe to reopen/lift restriction.",
            })

    # suggest redirecting overflow toward the least-loaded open gate
    if open_gates:
        quietest = min(open_gates, key=lambda g: g["density"])
        busiest = max(gates.values(), key=lambda g: g["density"])
        if busiest["density"] - quietest["density"] > 0.30 and busiest["id"] != quietest["id"]:
            recs.append({
                "domain": "crowd_flow",
                "action": "redirect_arrivals",
                "target": f"{busiest['id']}->{quietest['id']}",
                "priority": "medium",
                "reason": (
                    f"{busiest['name']} ({busiest['density']:.0%}) is far busier than "
                    f"{quietest['name']} ({quietest['density']:.0%}); steer new arrivals there."
                ),
            })

    if avg_density >= 0.80:
        recs.append({
            "domain": "crowd_flow",
            "action": "general_alert",
            "target": "all_gates",
            "priority": "high",
            "reason": f"Average gate density is {avg_density:.0%} — consider venue-wide overcrowding protocol.",
        })

    return recs
