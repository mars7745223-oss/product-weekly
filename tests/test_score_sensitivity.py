import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("score_priority", ROOT / "scripts/score_priority.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SensitivityRules(unittest.TestCase):
    def setUp(self):
        self.data = {"model": "CPS", "scope": "fictional same-scope comparison",
                     "ratings": {k: {"score": v, "reason": "teaching", "evidence_refs": ["DEMO"]}
                                 for k, v in zip(module.MODELS["CPS"], [5, 2, 3, 3, 4, 4])}}
        self.scenarios = json.loads((ROOT / "examples/weight-scenarios.json").read_text(encoding="utf-8"))

    def test_declared_weights_change_arithmetic_without_ranking(self):
        result = module.compare_scenarios(self.data, self.scenarios)
        self.assertEqual(result["baseline"]["score"], 69)
        self.assertEqual([s["result"]["score"] for s in result["scenarios"]], [72, 66])
        self.assertIsNone(result["ranking_decision"])

    def test_unknown_score_stays_unknown(self):
        self.data["ratings"]["competitive_threat"]["score"] = None
        result = module.compare_scenarios(self.data, self.scenarios)
        self.assertIsNone(result["baseline"]["score"])
        self.assertTrue(all(x["score_change"] is None for x in result["scenarios"]))

    def test_duplicate_scenario_versions_rejected(self):
        with self.assertRaises(ValueError):
            module.compare_scenarios(self.data, [self.scenarios[0], self.scenarios[0]])

    def test_reason_required(self):
        self.scenarios[0]["reason"] = ""
        with self.assertRaises(ValueError):
            module.compare_scenarios(self.data, self.scenarios)


if __name__ == "__main__":
    unittest.main()
