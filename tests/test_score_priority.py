"""Offline numeric and invalid-input cases; all evidence labels are synthetic."""
import copy
import importlib.util
import itertools
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("score_priority", ROOT / "scripts/score_priority.py")
score_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score_module)


def fixture(model="CPS", values=None):
    names = list(score_module.MODELS[model])
    values = values if values is not None else [None] * len(names)
    return {"model": model, "scope": "教学数值案例，同任务同地区参照，非真实竞品评分",
            "ratings": {name: {"score": value,
                               "reason": "教学模拟依据" if value is not None else None,
                               "evidence_refs": ["TEST-EVIDENCE"] if value is not None else []}
                        for name, value in zip(names, values)}}


class ScoringTests(unittest.TestCase):
    def test_user_example_is_82(self):
        result = score_module.calculate(fixture(values=[4, 5, 3, 4, 5, 3]))
        self.assertEqual(result["score"], 82)
        self.assertEqual(result["threat_score"], 100)
        self.assertEqual(result["learning_score"], 60)

    def test_minimum_and_maximum(self):
        for model in ["CPS", "TOS"]:
            size = len(score_module.MODELS[model])
            self.assertEqual(score_module.calculate(fixture(model, [1] * size))["score"], 20)
            self.assertEqual(score_module.calculate(fixture(model, [5] * size))["score"], 100)

    def test_uniform_tos(self):
        self.assertEqual(score_module.calculate(fixture("TOS", [3] * 7))["score"], 60)

    def test_unknown_is_not_zero(self):
        result = score_module.calculate(fixture())
        self.assertIsNone(result["score"])
        self.assertIsNone(result["score_bounds"])
        self.assertEqual(result["weighted_coverage"], 0)

    def test_partial_overlap_does_not_become_100(self):
        result = score_module.calculate(fixture(values=[5, None, None, None, None, None]))
        self.assertIsNone(result["score"])
        self.assertEqual(result["weighted_coverage"], .25)
        self.assertEqual(result["score_bounds"], [40, 100])
        self.assertIsNone(result["threat_score"])

    def test_bounds_contain_all_unknown_completions(self):
        partial = fixture(values=[4, None, 3, 4, None, 2])
        low, high = score_module.calculate(partial)["score_bounds"]
        for threat, relevance in itertools.product(range(1, 6), repeat=2):
            point = score_module.calculate(fixture(values=[4, threat, 3, 4, relevance, 2]))["score"]
            self.assertGreaterEqual(point, low)
            self.assertLessEqual(point, high)

    def test_invalid_scores(self):
        for value in [0, 6, True, False, "4", 2.5]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                score_module.calculate(fixture(values=[value, None, None, None, None, None]))

    def test_scored_dimension_needs_evidence(self):
        data = fixture(values=[4, None, None, None, None, None])
        data["ratings"]["customer_overlap"]["evidence_refs"] = []
        with self.assertRaises(ValueError):
            score_module.calculate(data)

    def test_scored_dimension_needs_reason(self):
        data = fixture(values=[4, None, None, None, None, None])
        data["ratings"]["customer_overlap"]["reason"] = ""
        with self.assertRaises(ValueError):
            score_module.calculate(data)

    def test_missing_dimension_rejected(self):
        data = fixture()
        del data["ratings"]["growth_momentum"]
        with self.assertRaises(ValueError):
            score_module.calculate(data)

    def test_bad_weights_rejected(self):
        for bad in [25, float("nan"), True, 0, -.25]:
            data = fixture()
            data["weights"] = copy.deepcopy(score_module.MODELS["CPS"])
            data["weights"]["customer_overlap"] = bad
            data["weight_version"] = "TEST"
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                score_module.calculate(data)

    def test_custom_weights_need_version(self):
        data = fixture()
        data["weights"] = copy.deepcopy(score_module.MODELS["CPS"])
        with self.assertRaises(ValueError):
            score_module.calculate(data)

    def test_scope_required(self):
        data = fixture()
        data["scope"] = ""
        with self.assertRaises(ValueError):
            score_module.calculate(data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
