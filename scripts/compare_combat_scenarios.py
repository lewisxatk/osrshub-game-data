#!/usr/bin/env python3
"""Compare bounded Combat Studio loadout candidates across sourced scenarios.

This reuses the current scoped baseline melee evaluator. It is a scenario
comparison layer, not a verified boss-DPS model or a guarantee of global
optimality: each scenario contributes candidates from its own bounded search,
and the union of those top candidates is then evaluated across every scenario.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from evaluate_combat_loadout import evaluate_loadout
from search_combat_studio_loadouts import search_loadouts

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
REQUIRED_INPUTS = ("effective_attack", "effective_strength", "effective_defence", "defence_bonus")


def _validate_scenarios(scenarios):
    if not isinstance(scenarios, list) or not 2 <= len(scenarios) <= 10:
        raise ValueError("scenarios must contain between 2 and 10 scenario objects")
    seen = set()
    normalized = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError(f"scenario {index} must be an object")
        sid = scenario.get("scenario_id")
        name = scenario.get("name")
        inputs = scenario.get("combat_inputs")
        source_url = scenario.get("source_url")
        weight = scenario.get("weight", 1.0)
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError(f"scenario {index} requires a non-empty scenario_id")
        if sid in seen:
            raise ValueError(f"duplicate scenario_id {sid!r}")
        seen.add(sid)
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"scenario {sid} requires a non-empty name")
        if not isinstance(inputs, dict):
            raise ValueError(f"scenario {sid} requires a combat_inputs object")
        missing = [key for key in REQUIRED_INPUTS if key not in inputs]
        if missing:
            raise ValueError(f"scenario {sid} missing combat inputs: {', '.join(missing)}")
        for key in REQUIRED_INPUTS:
            value = inputs[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"scenario {sid} {key} must be a non-negative integer")
        if not isinstance(source_url, str) or not source_url.startswith("https://oldschool.runescape.wiki/"):
            raise ValueError(f"scenario {sid} requires an HTTPS OSRS Wiki source_url")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight <= 0:
            raise ValueError(f"scenario {sid} weight must be a finite positive number")
        normalized.append({
            "scenario_id": sid,
            "name": name.strip(),
            "combat_inputs": {key: inputs[key] for key in REQUIRED_INPUTS},
            "source_url": source_url,
            "weight": float(weight),
        })
    total_weight = sum(row["weight"] for row in normalized)
    for row in normalized:
        row["normalized_weight"] = row["weight"] / total_weight
    return normalized


def compare_scenarios(equipment, requirements, quest_unlocks, profiles, profile, costs,
                      budget, scenarios, attack_style="slash", candidates_per_slot=8,
                      node_limit=100000, top_n=20):
    if attack_style not in ("stab", "slash", "crush"):
        raise ValueError("attack_style must be stab, slash or crush")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError("budget_gp must be a non-negative integer")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 50:
        raise ValueError("top_n must be between 1 and 50")
    scenarios = _validate_scenarios(scenarios)

    scenario_searches = []
    candidate_ids = {}
    for scenario in scenarios:
        result = search_loadouts(
            equipment, requirements, quest_unlocks, profiles, profile, costs, budget,
            scenario["combat_inputs"], attack_style, candidates_per_slot, node_limit,
        )
        scenario_searches.append({
            "scenario_id": scenario["scenario_id"],
            "name": scenario["name"],
            "status": result["status"],
            "search": result["search"],
            "candidate_counts": result["candidate_counts"],
        })
        for candidate in result.get("top_loadouts", []):
            selected = candidate.get("selected_items", [])
            ids = tuple(sorted(item["item_id"] for item in selected if isinstance(item, dict) and isinstance(item.get("item_id"), int) and not isinstance(item.get("item_id"), bool)))
            if ids and len(ids) == len(selected):
                candidate_ids[ids] = True

    scenario_results = []
    for ids in sorted(candidate_ids):
        per_scenario = []
        valid = True
        total_cost = None
        selected_names = None
        for scenario in scenarios:
            try:
                evaluated = evaluate_loadout(
                    profiles, list(ids), costs, budget, scenario["combat_inputs"], attack_style
                )
            except ValueError:
                valid = False
                break
            if total_cost is None:
                total_cost = evaluated["total_cost_gp"]
                selected_names = [
                    {"item_id": item["item_id"], "item_name": item["item_name"], "slot": item["slot"]}
                    for item in evaluated["selected_items"]
                ]
            elif total_cost != evaluated["total_cost_gp"]:
                valid = False
                break
            per_scenario.append({
                "scenario_id": scenario["scenario_id"],
                "name": scenario["name"],
                "weight": scenario["normalized_weight"],
                "source_url": scenario["source_url"],
                "dps": evaluated["combat_result"]["dps"],
                "hit_chance": evaluated["combat_result"]["hit_chance"],
                "max_hit": evaluated["combat_result"]["max_hit"],
                "attack_roll": evaluated["combat_result"]["attack_roll"],
                "defence_roll": evaluated["combat_result"]["defence_roll"],
            })
        if not valid or len(per_scenario) != len(scenarios):
            continue
        dps_values = [row["dps"] for row in per_scenario]
        weighted_mean = sum(row["dps"] * row["weight"] for row in per_scenario)
        scenario_results.append({
            "selected_items": selected_names,
            "selected_item_ids": list(ids),
            "total_cost_gp": total_cost,
            "remaining_budget_gp": budget - total_cost,
            "weighted_average_dps": round(weighted_mean, 8),
            "worst_case_dps": round(min(dps_values), 8),
            "best_case_dps": round(max(dps_values), 8),
            "dps_spread": round(max(dps_values) - min(dps_values), 8),
            "scenario_results": per_scenario,
        })

    scenario_results.sort(key=lambda row: (
        -row["weighted_average_dps"], -row["worst_case_dps"],
        row["total_cost_gp"], tuple(row["selected_item_ids"]),
    ))
    truncated = any(row["search"].get("truncated", False) for row in scenario_searches)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": "search_truncated" if truncated else ("scenario_ranked_candidates" if scenario_results else "no_valid_candidates"),
        "attack_style": attack_style,
        "budget_gp": budget,
        "scenario_count": len(scenarios),
        "candidate_union_count": len(candidate_ids),
        "evaluated_candidate_count": len(scenario_results),
        "scenarios": [{
            "scenario_id": row["scenario_id"], "name": row["name"],
            "weight": row["weight"], "normalized_weight": row["normalized_weight"],
            "source_url": row["source_url"],
        } for row in scenarios],
        "scenario_searches": scenario_searches,
        "ranked_candidates": scenario_results[:top_n],
        "ranking_method": {
            "primary": "weighted_average_dps_descending",
            "tie_breakers": ["worst_case_dps_descending", "total_cost_gp_ascending", "item_ids_ascending"],
            "weighting": "Positive user-supplied scenario weights are normalized to sum to one.",
        },
        "guardrails": [
            "Uses the scoped baseline melee evaluator and caller-supplied effective levels; it is not verified boss-specific DPS.",
            "Each scenario source URL is a provenance pointer, not proof that its numeric inputs were independently verified.",
            "Candidate discovery is bounded per scenario; the union of per-scenario top candidates is not a global exhaustive optimum.",
            "Prayer, potion, special attack, phase, immunity, set-effect, damage-cap and supply-cost mechanics are not modelled.",
            "Unknown or incomplete item eligibility remains subject to the existing fail-closed eligibility gate.",
            "Costs are caller-supplied GP values, not live Grand Exchange prices.",
            "Weighted average is the ranking objective; worst-case DPS and spread are exposed to show trade-offs, not to imply a universally best setup.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equipment", default=str(DIST / "equipment-stats.json"))
    parser.add_argument("--requirements", default=str(DIST / "item-requirements.json"))
    parser.add_argument("--quest-unlocks", required=True)
    parser.add_argument("--profiles", default=str(DIST / "item-combat-profiles.json"))
    parser.add_argument("--profile", required=True)
    parser.add_argument("--costs", required=True)
    parser.add_argument("--scenarios", required=True, help="JSON array of 2-10 sourced scenario objects")
    parser.add_argument("--budget", required=True, type=int)
    parser.add_argument("--style", choices=("stab", "slash", "crush"), default="slash")
    parser.add_argument("--candidates-per-slot", type=int, default=8)
    parser.add_argument("--node-limit", type=int, default=100000)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--output", default=str(REPORTS / "combat-studio-scenario-comparison.json"))
    args = parser.parse_args()
    try:
        load = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
        scenario_document = load(args.scenarios)
        scenarios = scenario_document.get("scenarios") if isinstance(scenario_document, dict) else scenario_document
        result = compare_scenarios(
            load(args.equipment), load(args.requirements), load(args.quest_unlocks),
            load(args.profiles), load(args.profile), load(args.costs), args.budget,
            scenarios, args.style, args.candidates_per_slot, args.node_limit, args.top_n,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
