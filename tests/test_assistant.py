import os
import unittest
from src.engine import fan_qa
from src.assistant import handle_request
from src.state import build_seed_state


class TestFanQA(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "gates": {
                "A": {"id": "A", "name": "Gate A", "capacity": 100, "current_count": 20, "status": "open", "density": 0.20},
                "B": {"id": "B", "name": "Gate B", "capacity": 100, "current_count": 90, "status": "open", "density": 0.90},
            },
            "schedule": [
                {"id": "E1", "name": "Main Event", "location": "Field", "start_time": "19:00", "end_time": "21:00"},
            ],
        }

    def test_gate_question_suggests_quietest(self):
        recs = fan_qa.evaluate(self.snapshot, "which gate has the shortest line?")
        self.assertTrue(any(r["action"] == "suggest_gate" and r["target"] == "A" for r in recs))

    def test_schedule_question_returns_event(self):
        recs = fan_qa.evaluate(self.snapshot, "when does it start?")
        self.assertTrue(any(r["action"] == "schedule_info" for r in recs))

    def test_unrelated_question_gives_generic_help(self):
        recs = fan_qa.evaluate(self.snapshot, "asdfghjkl")
        self.assertEqual(recs[0]["action"], "generic_help")


class TestAssistantRoleRouting(unittest.TestCase):
    """No ANTHROPIC_API_KEY in the test environment -> exercises the
    offline fallback path, which also proves the assistant works without
    any external API dependency."""

    def setUp(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.state = build_seed_state()

    def test_invalid_role_raises(self):
        with self.assertRaises(ValueError):
            handle_request("mascot", self.state)

    def test_fan_role_only_runs_fan_qa(self):
        result = handle_request("fan", self.state, "where can I get food?")
        self.assertTrue(all(r["domain"] == "fan_qa" for r in result["recommendations"]))

    def test_ops_manager_sees_cross_domain_recommendations(self):
        # push a gate to critical density so crowd_flow definitely fires
        self.state.gates["C"].current_count = self.state.gates["C"].capacity
        result = handle_request("ops_manager", self.state)
        domains = {r["domain"] for r in result["recommendations"]}
        self.assertIn("crowd_flow", domains)

    def test_answer_is_non_empty_string(self):
        result = handle_request("security", self.state)
        self.assertIsInstance(result["answer"], str)
        self.assertTrue(len(result["answer"]) > 0)


if __name__ == "__main__":
    unittest.main()
