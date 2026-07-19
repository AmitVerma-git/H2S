"""
Security incident triage & escalation.

Severity + type drive escalation tier and required response. Kept as a
lookup + simple rules rather than a black box, so ops staff can audit
exactly why something was escalated (important for a real deployment).
"""
from __future__ import annotations

ESCALATE_SEVERITIES = {"high", "critical"}
AUTO_DISPATCH_TYPES = {"suspicious_item", "altercation"}


def evaluate(snapshot: dict) -> list[dict]:
    incidents = snapshot.get("incidents", [])
    recs: list[dict] = []

    open_incidents = [i for i in incidents if i["status"] == "open"]

    for inc in open_incidents:
        severity = inc["severity"]
        should_escalate = severity in ESCALATE_SEVERITIES or inc["type"] in AUTO_DISPATCH_TYPES

        if severity == "critical":
            action = "dispatch_emergency_services"
            priority = "critical"
        elif should_escalate:
            action = "dispatch_security_team"
            priority = "high"
        elif severity == "medium":
            action = "dispatch_nearest_steward"
            priority = "medium"
        else:
            action = "log_and_monitor"
            priority = "low"

        recs.append({
            "domain": "security",
            "action": action,
            "target": inc["id"],
            "priority": priority,
            "reason": f"{inc['id']}: {inc['type']} ({severity}) at {inc['location']}.",
        })

    critical_count = sum(1 for i in open_incidents if i["severity"] == "critical")
    if critical_count >= 2:
        recs.append({
            "domain": "security",
            "action": "activate_incident_command",
            "target": "venue",
            "priority": "critical",
            "reason": f"{critical_count} concurrent critical incidents — activate full incident command structure.",
        })

    return recs
