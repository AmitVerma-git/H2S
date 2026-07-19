import unittest
from src.engine import crowd_flow


def make_snapshot(gates):
    return {"gates": gates}


class TestCrowdFlow(unittest.TestCase):
    def test_gate_over_close_threshold_gets_closed(self):
        snap = make_snapshot({
            "A": {"id": "A", "name": "Gate A", "capacity": 100, "current_count": 98, "status": "open", "density": 0.98},
        })
        recs = crowd_flow.evaluate(snap)
        actions = [r["action"] for r in recs]
        self.assertIn("close_gate", actions)

    def test_gate_over_restrict_threshold_gets_restricted(self):
        snap = make_snapshot({
            "A": {"id": "A", "name": "Gate A", "capacity": 100, "current_count": 90, "status": "open", "density": 0.90},
        })
        recs = crowd_flow.evaluate(snap)
        self.assertTrue(any(r["action"] == "restrict_gate" for r in recs))

    def test_low_density_gate_left_alone(self):
        snap = make_snapshot({
            "A": {"id": "A", "name": "Gate A", "capacity": 100, "current_count": 20, "status": "open", "density": 0.20},
        })
        recs = crowd_flow.evaluate(snap)
        self.assertEqual(recs, [])

    def test_restricted_gate_reopens_when_density_drops(self):
        snap = make_snapshot({
            "A": {"id": "A", "name": "Gate A", "capacity": 100, "current_count": 40, "status": "restricted", "density": 0.40},
        })
        recs = crowd_flow.evaluate(snap)
        self.assertTrue(any(r["action"] == "reopen_gate" for r in recs))

    def test_redirect_suggested_when_imbalanced(self):
        snap = make_snapshot({
            "A": {"id": "A", "name": "Gate A", "capacity": 100, "current_count": 90, "status": "open", "density": 0.90},
            "B": {"id": "B", "name": "Gate B", "capacity": 100, "current_count": 10, "status": "open", "density": 0.10},
        })
        recs = crowd_flow.evaluate(snap)
        self.assertTrue(any(r["action"] == "redirect_arrivals" for r in recs))


if __name__ == "__main__":
    unittest.main()
