"""
Fan-facing Q&A: wayfinding, schedule, and "where's it quiet" style
questions. Unlike the other three modules this one is query-driven
rather than always-on — it looks at the free-text query plus current
state to decide what's relevant to surface.
"""
from __future__ import annotations


def evaluate(snapshot: dict, query: str = "") -> list[dict]:
    q = query.lower()
    gates = snapshot.get("gates", {})
    schedule = snapshot.get("schedule", [])
    recs: list[dict] = []

    if any(k in q for k in ("gate", "enter", "in", "shortest", "fastest", "line", "queue")):
        open_gates = [g for g in gates.values() if g["status"] == "open"]
        if open_gates:
            quietest = min(open_gates, key=lambda g: g["density"])
            recs.append({
                "domain": "fan_qa",
                "action": "suggest_gate",
                "target": quietest["id"],
                "priority": "info",
                "reason": f"{quietest['name']} currently has the shortest line ({quietest['density']:.0%} full).",
            })

    if any(k in q for k in ("schedule", "start", "when", "time", "kick off", "kickoff")):
        for ev in schedule:
            recs.append({
                "domain": "fan_qa",
                "action": "schedule_info",
                "target": ev["id"],
                "priority": "info",
                "reason": f"{ev['name']} — {ev['start_time']} to {ev['end_time']} ({ev['location']}).",
            })

    if any(k in q for k in ("food", "eat", "drink", "concession", "snack")):
        recs.append({
            "domain": "fan_qa",
            "action": "concessions_info",
            "target": "all",
            "priority": "info",
            "reason": "Check the nearest concourse food court; wait times are shown on the app map.",
        })

    if not recs:
        recs.append({
            "domain": "fan_qa",
            "action": "generic_help",
            "target": "n/a",
            "priority": "info",
            "reason": "Ask about gates/lines, event schedule, or food & drink and I can point you the right way.",
        })

    return recs
