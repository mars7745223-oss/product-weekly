"""Calculate evidence-backed CPS/TOS arithmetic; never choose products or tiers."""
import argparse
import json
import math
from pathlib import Path

MODELS = {
    "CPS": {
        "customer_overlap": .25, "competitive_threat": .25,
        "growth_momentum": .15, "capability_advantage": .15,
        "scope_relevance": .10, "learning_value": .10,
    },
    "TOS": {
        "business_impact": .30, "capability_fit": .20,
        "technical_feasibility": .15, "application_readiness": .10,
        "economic_feasibility": .10, "transferability": .10,
        "differentiation_potential": .05,
    },
}


def calculate(data):
    if not isinstance(data, dict):
        raise ValueError("input must be an object")
    model = data.get("model")
    if model not in MODELS:
        raise ValueError("model must be CPS or TOS")
    scope = data.get("scope")
    if not isinstance(scope, str) or not scope.strip():
        raise ValueError("scope is required")
    default = MODELS[model]
    weights = data.get("weights", default)
    if not isinstance(weights, dict) or set(weights) != set(default):
        raise ValueError("weights must include exactly the model dimensions")
    for key, weight in weights.items():
        if (isinstance(weight, bool) or not isinstance(weight, (int, float))
                or not math.isfinite(weight) or not 0 < weight <= 1):
            raise ValueError("weights must be finite positive fractions: " + key)
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("weights must sum to 1; do not use 25 instead of .25")
    if "weights" in data and not data.get("weight_version"):
        raise ValueError("custom weights require weight_version")
    ratings = data.get("ratings")
    if not isinstance(ratings, dict) or set(ratings) != set(default):
        raise ValueError("ratings must contain every model dimension; use null for unknown")
    known, unknown = [], []
    contribution = coverage = 0.0
    for key, weight in weights.items():
        rating = ratings[key]
        if not isinstance(rating, dict):
            raise ValueError("rating must be an object: " + key)
        score = rating.get("score")
        if score is None:
            unknown.append(key)
            continue
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
            raise ValueError("score must be an integer 1..5 or null: " + key)
        reason = rating.get("reason")
        refs = rating.get("evidence_refs")
        if (not isinstance(reason, str) or not reason.strip()
                or not isinstance(refs, list) or not refs
                or any(not isinstance(ref, str) or not ref.strip() for ref in refs)):
            raise ValueError("known scores require reason and evidence_refs: " + key)
        coverage += weight
        contribution += weight * score
        known.append(key)
    complete = not unknown
    coverage = 1.0 if complete else coverage
    score = round(20 * contribution, 4) if complete else None
    bounds = None
    if known:
        bounds = [round(20 * (contribution + 1 - coverage), 4),
                  round(20 * (contribution + 5 * (1 - coverage)), 4)]
    result = {
        "schema_version": "product-weekly-priority/1", "model": model,
        "weight_version": data.get("weight_version", model + "-1"),
        "scope": scope, "weights": dict(weights),
        "status": "complete" if complete else "partial" if known else "unassessed",
        "weighted_coverage": round(coverage, 8), "score": score,
        "score_bounds": bounds, "unknown_dimensions": unknown,
        "scale": [20, 100], "calculation_only": True,
        "interpretation": "Ordinal research model; not a probability or an adoption decision.",
    }
    if model == "CPS":
        result["threat_score"] = (20 * ratings["competitive_threat"]["score"]
                                  if ratings["competitive_threat"].get("score") is not None else None)
        result["learning_score"] = (20 * ratings["learning_value"]["score"]
                                    if ratings["learning_value"].get("score") is not None else None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sensitivity", type=Path,
                        help="JSON scenarios with complete weights, versions and reasons; arithmetic only")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        result = calculate(data)
        if args.sensitivity:
            scenarios = json.loads(args.sensitivity.read_text(encoding="utf-8-sig"))
            result = compare_scenarios(data, scenarios)
    except (ValueError, OSError) as error:
        parser.exit(2, "Invalid scoring input: " + str(error) + "\n")
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def compare_scenarios(data, scenarios):
    """Recalculate declared weight scenarios; do not infer tiers or objective rank."""
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("sensitivity must be a nonempty scenario array")
    baseline = calculate(data)
    outputs, names = [], set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("scenario must be an object")
        name, reason = scenario.get("weight_version"), scenario.get("reason")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError("scenarios require unique nonempty weight_version")
        if not isinstance(reason, str) or not reason.strip() or "weights" not in scenario:
            raise ValueError("scenario requires reason and complete weights")
        names.add(name)
        candidate = dict(data, weights=scenario["weights"], weight_version=name)
        evaluated = calculate(candidate)
        outputs.append({"reason": reason, "result": evaluated,
                        "score_change": (round(evaluated["score"] - baseline["score"], 4)
                                         if evaluated["score"] is not None and baseline["score"] is not None else None)})
    return {"schema_version": "product-weekly-sensitivity/1", "baseline": baseline,
            "scenarios": outputs, "calculation_only": True, "ranking_decision": None,
            "interpretation": "Declared weight preferences; not confidence intervals or validated importance."}


if __name__ == "__main__":
    main()
