import unittest
from src.engine import security


class TestSecurity(unittest.TestCase):
    def test_critical_incident_dispatches_emergency_services(self):
        snap = {"incidents": [
            {"id": "INC-1", "type": "suspicious_item", "location": "Gate C", "severity": "critical", "status": "open"},
        ]}
        recs = security.evaluate(snap)
        self.assertEqual(recs[0]["action"], "dispatch_emergency_services")
        self.assertEqual(recs[0]["priority"], "critical")

    def test_low_severity_just_logged(self):
        snap = {"incidents": [
            {"id": "INC-2", "type": "lost_child", "location": "Gate A", "severity": "low", "status": "open"},
        ]}
        recs = security.evaluate(snap)
        self.assertEqual(recs[0]["action"], "log_and_monitor")

    def test_resolved_incidents_ignored(self):
        snap = {"incidents": [
            {"id": "INC-3", "type": "medical", "location": "Gate B", "severity": "high", "status": "resolved"},
        ]}
        recs = security.evaluate(snap)
        self.assertEqual(recs, [])

    def test_multiple_criticals_trigger_incident_command(self):
        snap = {"incidents": [
            {"id": "INC-4", "type": "suspicious_item", "location": "Gate A", "severity": "critical", "status": "open"},
            {"id": "INC-5", "type": "altercation", "location": "Gate B", "severity": "critical", "status": "open"},
        ]}
        recs = security.evaluate(snap)
        self.assertTrue(any(r["action"] == "activate_incident_command" for r in recs))


if __name__ == "__main__":
    unittest.main()
