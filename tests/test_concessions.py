import unittest
from src.engine import concessions


class TestConcessions(unittest.TestCase):
    def test_low_stock_triggers_restock(self):
        snap = {"concessions": {
            "F1": {"id": "F1", "name": "Stand 1", "location": "x", "stock_pct": 15, "queue_length": 2, "staff_count": 2},
        }}
        recs = concessions.evaluate(snap)
        self.assertTrue(any(r["action"] == "restock" for r in recs))

    def test_long_queue_triggers_add_staff(self):
        snap = {"concessions": {
            "F1": {"id": "F1", "name": "Stand 1", "location": "x", "stock_pct": 80, "queue_length": 20, "staff_count": 2},
        }}
        recs = concessions.evaluate(snap)
        self.assertTrue(any(r["action"] == "add_staff" for r in recs))

    def test_reassign_from_quiet_to_busy(self):
        snap = {"concessions": {
            "F1": {"id": "F1", "name": "Busy", "location": "x", "stock_pct": 80, "queue_length": 20, "staff_count": 2},
            "F2": {"id": "F2", "name": "Quiet", "location": "y", "stock_pct": 80, "queue_length": 1, "staff_count": 2},
        }}
        recs = concessions.evaluate(snap)
        self.assertTrue(any(r["action"] == "reassign_staff" and r["target"] == "F2->F1" for r in recs))

    def test_healthy_stand_no_recommendations(self):
        snap = {"concessions": {
            "F1": {"id": "F1", "name": "Stand 1", "location": "x", "stock_pct": 90, "queue_length": 4, "staff_count": 2},
        }}
        recs = concessions.evaluate(snap)
        self.assertEqual(recs, [])


if __name__ == "__main__":
    unittest.main()
