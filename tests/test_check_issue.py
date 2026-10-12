import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_issue", ROOT / "scripts/check_issue.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IssueRules(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "examples/teaching-issue.json").read_text(encoding="utf-8"))

    def codes(self, base=None):
        return {e["code"] for e in module.check(self.data, base)["errors"]}

    def test_valid_with_failed_coverage(self):
        result = module.check(self.data)
        self.assertTrue(result["ok"])
        self.assertEqual(result["coverage"]["completion_rate"], .5)
        self.assertFalse(result["web_facts_verified"])

    def test_retrospective_does_not_become_prospective_proof(self):
        self.data["coverage_plan"]["origin"] = "retrospective"
        self.data["coverage_plan"]["locked_at"] = None
        result = module.check(self.data)
        self.assertTrue(result["ok"])
        self.assertIn("retrospective_plan", {w["code"] for w in result["warnings"]})

    def test_missing_source(self):
        self.data["claims"][0]["source_ids"] = ["S-NOT-THERE"]
        self.assertIn("broken_ref", self.codes())

    def test_duplicate_id(self):
        self.data["sources"].append(copy.deepcopy(self.data["sources"][0]))
        self.assertIn("duplicate_id", self.codes())

    def test_tier_conflict(self):
        self.assertIn("tier_conflict", self.codes({"competitors": [{"competitor_id": "CMP-DEMO-A", "tier": "Tier 3"}]}))

    def test_ambiguous_alias(self):
        self.data["competitors"][1]["aliases"] = ["OLD-A"]
        self.assertIn("ambiguous_alias", self.codes())

    def test_aliases_field_required(self):
        self.data["competitors"][0].pop("aliases")
        self.assertIn("invalid_aliases", self.codes())

    def test_issue_competitor_missing_from_base(self):
        self.assertIn("competitor_missing_from_base", self.codes({"competitors": []}))

    def test_duplicate_base_id(self):
        obj = copy.deepcopy(self.data["competitors"][0])
        self.assertIn("duplicate_base_id", self.codes({"competitors": [obj, obj]}))

    def test_event_claim_link_is_bidirectional(self):
        self.data["claims"][0]["event_id"] = None
        self.assertIn("claim_event_conflict", self.codes())

    def test_legacy_schema_rejected_without_mutation(self):
        old = {"schema_version": "old", "facts": ["unchanged"]}
        before = copy.deepcopy(old)
        result = module.check(old)
        self.assertFalse(result["ok"])
        self.assertEqual(old, before)

    def test_background_cannot_be_marked_new(self):
        self.data["events"][1]["weekly_status"] = "new"
        self.assertIn("false_weekly_increment", self.codes())

    def test_progress_needs_new_evidence_date(self):
        self.data["events"][1]["weekly_status"] = "progress"
        self.assertIn("false_weekly_increment", self.codes())
        self.data["events"][1]["new_evidence_date"] = "2026-10-08"
        self.assertNotIn("false_weekly_increment", self.codes())

    def test_after_frozen_cutoff(self):
        self.data["events"][0]["event_date"] = "2026-10-10T09:01:00+08:00"
        self.assertIn("after_cutoff", self.codes())

    def test_known_date_range_without_fabricated_single_date(self):
        self.data["events"][0].update(event_date=None, event_date_range={"start": "2026-10-05", "end": "2026-10-09"})
        self.assertNotIn("false_weekly_increment", self.codes())
        self.data["events"][0]["event_date_range"]["start"] = "2026-10-03"
        self.assertIn("false_weekly_increment", self.codes())

    def test_failed_source_cannot_complete_unit(self):
        self.data["coverage_plan"]["cells"][1].update(status="completed", checked_scope="pretended read")
        self.assertIn("unsupported_completion", self.codes())

    def test_not_applicable_needs_reason(self):
        self.data["coverage_plan"]["cells"][1].update(status="not_applicable", reason=None)
        self.assertIn("unexplained_exclusion", self.codes())

    def test_missing_read_scope_not_auto_filled(self):
        self.data["sources"][0].pop("read_scope")
        result = module.check(self.data)
        self.assertIn("unknown_read_scope", {w["code"] for w in result["warnings"]})
        self.assertNotIn("read_scope", self.data["sources"][0])

    def test_unknown_kiq(self):
        self.data["coverage_plan"]["cells"][0]["kiq_ids"] = ["Q-NOT-THERE"]
        self.assertIn("broken_kiq", self.codes())

    def test_rank_reason_and_continuity(self):
        self.data["editorial"]["must_read"][0].update(rank=2, reason=None)
        self.assertTrue({"missing_text", "noncontinuous_ranks"}.issubset(self.codes()))

    def test_selected_event_needs_claim(self):
        self.data["events"][0]["claim_ids"] = []
        self.assertIn("selected_event_without_claim", self.codes())

    def test_failed_sources_cannot_support_selected_claim(self):
        self.data["claims"][0]["source_ids"] = ["S-3"]
        self.assertIn("selected_claim_without_read_source", self.codes())

    def test_old_voice_cannot_be_claimed_weekly(self):
        self.data["voices"][0]["weekly_eligible"] = True
        self.assertIn("false_weekly_voice", self.codes())

    def test_inference_refs_must_exist(self):
        self.data["inferences"][0]["voice_ids"] = ["V-NOT-THERE"]
        self.assertIn("broken_ref", self.codes())

    def test_bad_field_types_report_errors(self):
        for group, key, value in [("claims", "event_id", []), ("events", "claim_ids", 3), ("sources", "access_status", None)]:
            with self.subTest(group=group, key=key):
                altered = copy.deepcopy(self.data)
                altered[group][0][key] = value
                self.assertFalse(module.check(altered)["ok"])


if __name__ == "__main__":
    unittest.main()
