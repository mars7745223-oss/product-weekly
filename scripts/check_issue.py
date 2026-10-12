"""Check issue records and links, not web truth, market recall or reader value."""
import argparse
import json
from datetime import date, datetime
from pathlib import Path

SCHEMA = "product-weekly-issue/2"
GROUPS = {
    "competitors": "competitor_id", "sources": "source_id", "events": "event_id",
    "claims": "claim_id", "voices": "voice_id", "research": "research_id",
    "inferences": "inference_id",
}
ACCESS = {"read", "partial", "failed", "not_attempted", "unknown"}
COVERAGE = {"completed", "partial", "failed", "not_checked", "not_applicable", "unknown"}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def enum_value(value, choices):
    return isinstance(value, str) and value in choices


def parse_date(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("date must be ISO string or null")
    if len(value) == 10:
        return date.fromisoformat(value)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def check(data, base=None):
    errors, warnings = [], []

    def add(level, code, path, message):
        (errors if level == "error" else warnings).append(
            {"code": code, "path": path, "message": message})

    def err(code, path, message):
        add("error", code, path, message)

    def warn(code, path, message):
        add("warning", code, path, message)

    def textfield(obj, key, path):
        if not nonempty(obj.get(key)):
            err("missing_text", path + "." + key, "nonempty text required")

    def dated(value, path):
        try:
            return parse_date(value)
        except (ValueError, TypeError):
            err("invalid_date", path, "use ISO date/time or null")
            return None

    def finish(metrics=None):
        return {"schema_version": "product-weekly-check/1", "ok": not errors,
                "validation_scope": "record_structure_and_consistency_only",
                "web_facts_verified": False, "recall_measured": False,
                "errors": errors, "warnings": warnings, "coverage": metrics}

    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA:
        err("unsupported_schema", "$", "explicit migration to " + SCHEMA + " required")
        return finish()
    issue = data.get("issue")
    if not isinstance(issue, dict):
        err("missing_issue", "issue", "object required")
        issue = {}
    for key in ["issue_id", "scope_id", "window_start", "window_end", "cutoff_at", "timezone"]:
        textfield(issue, key, "issue")
    start = dated(issue.get("window_start"), "issue.window_start")
    end = dated(issue.get("window_end"), "issue.window_end")
    cutoff = dated(issue.get("cutoff_at"), "issue.cutoff_at")
    if start and end and start > end:
        err("reversed_window", "issue", "window_start must not exceed window_end")
    if end and cutoff and cutoff != end:
        err("cutoff_window_mismatch", "issue.cutoff_at", "cutoff day must match window_end")

    indexed = {}
    for group, key in GROUPS.items():
        items = data.get(group)
        indexed[group] = {}
        if not isinstance(items, list):
            err("missing_array", group, "array required; use [] when no objects")
            continue
        for n, obj in enumerate(items):
            path = f"{group}[{n}]"
            if not isinstance(obj, dict):
                err("invalid_object", path, "object required")
                continue
            value = obj.get(key)
            if not nonempty(value):
                err("missing_id", path + "." + key, "canonical ID required")
            elif value in indexed[group]:
                err("duplicate_id", path + "." + key, "duplicate " + value)
            else:
                indexed[group][value] = obj

    def refs(obj, key, target, path, required=False):
        values = obj.get(key)
        if not isinstance(values, list):
            err("missing_refs", path + "." + key, "array required")
            return []
        good = []
        if required and not values:
            err("empty_refs", path + "." + key, "at least one reference required")
        for value in values:
            if not nonempty(value) or value not in indexed[target]:
                err("broken_ref", path + "." + key, "unknown " + target + " reference: " + str(value))
            elif value in good:
                warn("duplicate_ref", path + "." + key, "duplicate reference " + value)
            else:
                good.append(value)
        return good

    def competitor(obj, path):
        value = obj.get("competitor_id")
        if value is not None and (not nonempty(value) or value not in indexed["competitors"]):
            err("broken_competitor", path, "canonical competitor_id or null required")

    aliases = {}
    for cid, obj in indexed["competitors"].items():
        for key in ["product_line", "tier"]:
            textfield(obj, key, "competitors." + cid)
        if not isinstance(obj.get("tier_history"), list):
            err("missing_history", "competitors." + cid, "tier_history array required")
        values = obj.get("aliases")
        if not isinstance(values, list):
            err("invalid_aliases", "competitors." + cid, "aliases array required")
            continue
        for alias in values:
            if not nonempty(alias):
                err("invalid_alias", "competitors." + cid, "aliases must be nonempty strings")
            elif (alias in aliases and aliases[alias] != cid) or (alias in indexed["competitors"] and alias != cid):
                err("ambiguous_alias", "competitors." + cid, "alias shared by different products: " + alias)
            else:
                aliases[alias] = cid
    if base is not None:
        if not isinstance(base, dict) or not isinstance(base.get("competitors"), list):
            err("invalid_base", "base", "base.competitors array required")
        else:
            base_ids = set()
            for obj in base["competitors"]:
                if not isinstance(obj, dict):
                    err("invalid_base_competitor", "base", "competitor object required")
                    continue
                cid = obj.get("competitor_id")
                if not nonempty(cid):
                    err("invalid_base_competitor", "base", "canonical competitor ID required")
                    continue
                if cid in base_ids:
                    err("duplicate_base_id", "base." + cid, "duplicate competitor in base")
                base_ids.add(cid)
                if cid in indexed["competitors"] and obj.get("tier") != indexed["competitors"][cid].get("tier"):
                    err("tier_conflict", "base." + cid, "issue and current base Tier differ")
                elif cid not in indexed["competitors"] and cid in aliases:
                    err("base_uses_alias", "base." + cid, "base should use canonical competitor ID")
            for cid in indexed["competitors"]:
                if cid not in base_ids:
                    err("competitor_missing_from_base", "base." + cid, "issue competitor absent from supplied base; provide complete matching base version")

    for sid, obj in indexed["sources"].items():
        if not enum_value(obj.get("access_status"), ACCESS):
            err("invalid_access", "sources." + sid, "unsupported access_status")
        textfield(obj, "url", "sources." + sid)
        if enum_value(obj.get("access_status"), {"read", "partial"}) and not nonempty(obj.get("read_scope")):
            warn("unknown_read_scope", "sources." + sid, "actual read scope not recorded")

    for group in ["events", "claims", "voices"]:
        for ident, obj in indexed[group].items():
            path = group + "." + ident
            competitor(obj, path)
            refs(obj, "source_ids", "sources", path)
            if group == "claims" and obj.get("event_id") is not None:
                if not nonempty(obj["event_id"]) or obj["event_id"] not in indexed["events"]:
                    err("broken_event", path, "unknown event_id")
                elif not isinstance(indexed["events"][obj["event_id"]].get("claim_ids"), list) or ident not in indexed["events"][obj["event_id"]]["claim_ids"]:
                    err("asymmetric_event_claim", path, "claim missing from linked event.claim_ids")
            if group == "voices":
                published = dated(obj.get("published_at"), path + ".published_at")
                dated(obj.get("collected_at"), path + ".collected_at")
                if obj.get("weekly_eligible") is True and (published is None or not start or not end or not start <= published <= end):
                    err("false_weekly_voice", path, "a weekly voice needs a known publication date within window")

    for eid, obj in indexed["events"].items():
        path = "events." + eid
        refs(obj, "claim_ids", "claims", path)
        status = obj.get("weekly_status")
        when = dated(obj.get("event_date"), path + ".event_date")
        progress = dated(obj.get("new_evidence_date"), path + ".new_evidence_date")
        if not enum_value(status, {"new", "progress", "background", "outside", "unknown"}):
            err("invalid_weekly_status", path, "unsupported weekly_status")
        target = progress if status == "progress" else when
        if enum_value(status, {"new", "progress"}):
            valid_interval = False
            interval = obj.get("event_date_range")
            if status == "new" and target is None and isinstance(interval, dict):
                left = dated(interval.get("start"), path + ".event_date_range.start")
                right = dated(interval.get("end"), path + ".event_date_range.end")
                valid_interval = bool(left and right and start and end and start <= left <= right <= end)
            if not valid_interval and (target is None or not start or not end or not start <= target <= end):
                err("false_weekly_increment", path, "new/progress needs dated evidence within window")
            raw = obj.get("new_evidence_date" if status == "progress" else "event_date")
            try:
                if raw and len(raw) > 10 and len(issue.get("cutoff_at", "")) > 10:
                    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    stop = datetime.fromisoformat(issue["cutoff_at"].replace("Z", "+00:00"))
                    if dt.tzinfo and stop.tzinfo and dt > stop:
                        err("after_cutoff", path, "timestamp is after frozen cutoff")
            except (ValueError, TypeError):
                pass
        elif status == "outside" and (target is None or (start and end and start <= target <= end)):
            err("invalid_outside", path, "outside needs known date outside window")
        for clid in obj.get("claim_ids", []) if isinstance(obj.get("claim_ids"), list) else []:
            if nonempty(clid) and clid in indexed["claims"]:
                linked = indexed["claims"][clid].get("event_id")
                if linked != eid:
                    err("claim_event_conflict", path, "claim points to another event")

    for rid, obj in indexed["research"].items():
        refs(obj, "source_ids", "sources", "research." + rid)
    for iid, obj in indexed["inferences"].items():
        path = "inferences." + iid
        linked = []
        for key, group in [("claim_ids", "claims"), ("voice_ids", "voices"), ("research_ids", "research")]:
            linked.extend(refs(obj, key, group, path))
        if not linked:
            warn("unbridged_inference", path, "no linked evidence; not verified by this script")

    plan = data.get("coverage_plan")
    metrics = {"plan_origin": None, "required_applicable": 0, "completed_required": 0,
               "completion_rate": None, "states": {}, "not_market_recall": True}
    if not isinstance(plan, dict):
        err("missing_plan", "coverage_plan", "object required")
        plan = {}
    origin = plan.get("origin")
    metrics["plan_origin"] = origin
    if not enum_value(origin, {"prospective", "retrospective"}):
        err("invalid_plan_origin", "coverage_plan", "prospective or retrospective required")
    textfield(plan, "plan_version", "coverage_plan")
    if plan.get("locked_at") is None:
        warn("plan_time_unknown", "coverage_plan", "do not infer a prospective lock time")
    else:
        dated(plan["locked_at"], "coverage_plan.locked_at")
    if origin == "retrospective":
        warn("retrospective_plan", "coverage_plan", "completion is retrospective diagnosis, not prospective coverage proof")
    cells = plan.get("cells")
    if not isinstance(cells, list):
        err("missing_cells", "coverage_plan.cells", "array required")
        cells = []
    seen = set()
    kiq_records = data.get("kiqs", [])
    if not isinstance(kiq_records, list):
        err("invalid_kiqs", "kiqs", "array required when provided")
        kiq_records = []
    kiqs = {x["kiq_id"] for x in kiq_records if isinstance(x, dict) and nonempty(x.get("kiq_id"))}
    for n, obj in enumerate(cells):
        path = f"coverage_plan.cells[{n}]"
        if not isinstance(obj, dict):
            err("invalid_cell", path, "object required")
            continue
        cell_id = obj.get("cell_id")
        if not nonempty(cell_id) or cell_id in seen:
            err("invalid_cell_id", path, "unique cell_id required")
        else:
            seen.add(cell_id)
        competitor(obj, path)
        linked = refs(obj, "source_ids", "sources", path)
        questions = obj.get("kiq_ids")
        if not isinstance(questions, list) or not questions or any(not nonempty(q) for q in questions):
            err("missing_kiq_refs", path, "nonempty kiq_ids array required")
        elif kiqs and any(q not in kiqs for q in questions):
            err("broken_kiq", path, "KIQ reference not present")
        requirement, status = obj.get("requirement"), obj.get("status")
        if not enum_value(requirement, {"required", "rotation", "exploration"}):
            err("invalid_requirement", path, "unsupported requirement")
        if not enum_value(status, COVERAGE):
            err("invalid_coverage_status", path, "unsupported status")
        metrics["states"][str(status)] = metrics["states"].get(str(status), 0) + 1
        if status == "completed":
            if not nonempty(obj.get("checked_scope")) or not any(indexed["sources"][s].get("access_status") == "read" for s in linked):
                err("unsupported_completion", path, "completed needs read source and actual checked_scope")
        if status == "not_applicable" and not nonempty(obj.get("reason")):
            err("unexplained_exclusion", path, "not_applicable needs reason")
        if obj.get("checked_at") is None and not enum_value(status, {"not_checked", "unknown"}):
            warn("check_time_unknown", path, "actual checked_at not recorded")
        else:
            dated(obj.get("checked_at"), path + ".checked_at")
        if requirement == "required" and status != "not_applicable":
            metrics["required_applicable"] += 1
            metrics["completed_required"] += status == "completed"
    if cells and not kiqs:
        warn("kiq_index_missing", "kiqs", "KIQ existence could not be checked")
    if metrics["required_applicable"]:
        metrics["completion_rate"] = round(metrics["completed_required"] / metrics["required_applicable"], 6)

    editorial = data.get("editorial")
    if not isinstance(editorial, dict):
        err("missing_editorial", "editorial", "object required")
        editorial = {}
    must = editorial.get("must_read")
    if not isinstance(must, list):
        err("missing_must_read", "editorial.must_read", "array required")
        must = []
    ranks, item_ids = [], set()
    for n, obj in enumerate(must):
        path = f"editorial.must_read[{n}]"
        if not isinstance(obj, dict):
            err("invalid_editorial_item", path, "object required")
            continue
        item = obj.get("item_id")
        if not nonempty(item) or item in item_ids:
            err("invalid_item_id", path, "unique item_id required")
        else:
            item_ids.add(item)
        rank = obj.get("rank")
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
            err("invalid_rank", path, "positive integer required")
        else:
            ranks.append(rank)
        for key in ["reason", "evidence_state"]:
            textfield(obj, key, path)
        if not enum_value(obj.get("impact_band"), {"critical", "important", "context"}):
            err("invalid_impact_band", path, "unsupported impact_band")
        if not nonempty(obj.get("review_origin")):
            warn("review_origin_missing", path, "record original review or retrospective explanation")
        events = refs(obj, "event_ids", "events", path)
        infs = refs(obj, "inference_ids", "inferences", path)
        if not events and not infs:
            err("unlinked_must_read", path, "event or inference link required")
        for eid in events:
            if not indexed["events"][eid].get("claim_ids"):
                err("selected_event_without_claim", path, "selected event needs linked claims")
            for clid in indexed["events"][eid].get("claim_ids", []) if isinstance(indexed["events"][eid].get("claim_ids"), list) else []:
                if not nonempty(clid) or clid not in indexed["claims"]:
                    continue
                ids = indexed["claims"][clid].get("source_ids")
                if not isinstance(ids, list) or not ids or not any(
                        nonempty(s) and s in indexed["sources"] and indexed["sources"][s].get("access_status") == "read" for s in ids):
                    err("selected_claim_without_read_source", path, "selected claim needs an actually read source; truth still requires human review")
        for iid in infs:
            obj2 = indexed["inferences"][iid]
            if not any(obj2.get(k) for k in ["claim_ids", "voice_ids", "research_ids"]):
                err("selected_inference_without_bridge", path, "selected inference needs linked evidence")
    if sorted(ranks) != list(range(1, len(must) + 1)):
        err("noncontinuous_ranks", "editorial.must_read", "ranks must be unique and continuous from 1")
    decisions = editorial.get("decisions", [])
    if not isinstance(decisions, list):
        err("invalid_decisions", "editorial.decisions", "array required")
    else:
        for n, obj in enumerate(decisions):
            if not isinstance(obj, dict):
                err("invalid_decision", f"editorial.decisions[{n}]", "object required")
                continue
            for key, group in [("event_ids", "events"), ("inference_ids", "inferences")]:
                if key in obj:
                    refs(obj, key, group, f"editorial.decisions[{n}]")
            if not nonempty(obj.get("reason")):
                warn("decision_reason_missing", f"editorial.decisions[{n}]", "keep actual editorial reason")
    return finish(metrics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        base = json.loads(args.base.read_text(encoding="utf-8-sig")) if args.base else None
        result = check(data, base)
    except (OSError, ValueError) as exc:
        parser.exit(2, "Unreadable input: " + str(exc) + "\n")
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
