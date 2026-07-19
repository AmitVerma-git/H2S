"""
Concessions & resource/staffing allocation.

Balances two independent signals per stand — stock level and queue
length — into staffing/restock recommendations, and looks across stands
to suggest moving staff from quiet stands to busy ones rather than
requesting new headcount first.
"""
from __future__ import annotations

STOCK_LOW = 20
QUEUE_LONG = 15
QUEUE_QUIET = 3


def evaluate(snapshot: dict) -> list[dict]:
    stands = snapshot.get("concessions", {})
    recs: list[dict] = []

    for s in stands.values():
        if s["stock_pct"] <= STOCK_LOW:
            recs.append({
                "domain": "concessions",
                "action": "restock",
                "target": s["id"],
                "priority": "high" if s["stock_pct"] <= 10 else "medium",
                "reason": f"{s['name']} stock at {s['stock_pct']}% — restock before it sells out.",
            })
        if s["queue_length"] >= QUEUE_LONG:
            recs.append({
                "domain": "concessions",
                "action": "add_staff",
                "target": s["id"],
                "priority": "high",
                "reason": f"{s['name']} queue at {s['queue_length']} people — add staff to cut wait time.",
            })

    busy = [s for s in stands.values() if s["queue_length"] >= QUEUE_LONG]
    quiet = [s for s in stands.values() if s["queue_length"] <= QUEUE_QUIET and s["staff_count"] > 1]
    for b in busy:
        if quiet:
            donor = min(quiet, key=lambda s: s["queue_length"])
            recs.append({
                "domain": "concessions",
                "action": "reassign_staff",
                "target": f"{donor['id']}->{b['id']}",
                "priority": "medium",
                "reason": (
                    f"{donor['name']} is quiet (queue {donor['queue_length']}); "
                    f"move a staffer to {b['name']} (queue {b['queue_length']}) instead of calling in extra hands."
                ),
            })

    return recs
