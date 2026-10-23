#!/usr/bin/env python3
"""Recommend bounded melee loadout upgrades relative to currently owned gear."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from evaluate_combat_loadout import evaluate_loadout
from search_combat_studio_loadouts import search_loadouts

ROOT = Path(__file__).resolve().parents[1]
DIST, REPORTS = ROOT / "dist", ROOT / "reports"

def plan_upgrades(equipment, requirements, quest_unlocks, profiles, profile,
                  baseline_ids, costs, budget, inputs, attack_style="slash",
                  candidates_per_slot=8, node_limit=100000):
    if not isinstance(baseline_ids, list) or not baseline_ids:
        raise ValueError("baseline item IDs must be a non-empty array")
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in baseline_ids):
        raise ValueError("baseline item IDs must be non-negative integers")
    if len(baseline_ids) != len(set(baseline_ids)):
        raise ValueError("baseline item IDs contain duplicates")
    if not isinstance(costs, dict):
        raise ValueError("costs must be an object")
    # Current items are owned; don't mutate the caller's price map.
    effective_costs = dict(costs)
    for item_id in baseline_ids:
        effective_costs[str(item_id)] = 0
        effective_costs[item_id] = 0
    baseline = evaluate_loadout(profiles, baseline_ids, effective_costs, budget, inputs, attack_style)
    search = search_loadouts(equipment, requirements, quest_unlocks, profiles, profile,
                             effective_costs, budget, inputs, attack_style,
                             candidates_per_slot, node_limit)
    old_by_slot = {item["slot"]: item for item in baseline["selected_items"]}
    recommendations = []
    for row in search.get("top_loadouts", []):
        selected = row.get("selected_items", [])
        new_by_slot = {item["slot"]: item for item in selected}
        changes = []
        for slot in sorted(set(old_by_slot) | set(new_by_slot)):
            old, new = old_by_slot.get(slot), new_by_slot.get(slot)
            if old and new and old["item_id"] == new["item_id"]:
                continue
            changes.append({
                "slot": slot,
                "from_item_id": old["item_id"] if old else None,
                "from_item_name": old["item_name"] if old else None,
                "to_item_id": new["item_id"] if new else None,
                "to_item_name": new["item_name"] if new else None,
                "upgrade_cost_gp": new["cost_gp"] if new else 0,
                "attack_bonus_delta": (new["attack_bonus_contribution"] if new else 0) - (old["attack_bonus_contribution"] if old else 0),
                "melee_strength_delta": (new["melee_strength_contribution"] if new else 0) - (old["melee_strength_contribution"] if old else 0)
            })
        if not changes:
            continue
        candidate_dps = row.get("dps")
        cost = row.get("total_cost_gp")
        if isinstance(candidate_dps, bool) or not isinstance(candidate_dps, (int, float)):
            continue
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            continue
        baseline_dps = baseline["combat_result"]["dps"]
        gain = float(candidate_dps) - float(baseline_dps)
        recommendations.append({
            "rank": 0, "upgrade_cost_gp": cost, "remaining_budget_gp": budget - cost,
            "baseline_dps": baseline_dps, "candidate_dps": candidate_dps,
            "dps_gain": round(gain, 8),
            "dps_gain_percent": round(gain / baseline_dps * 100, 4) if baseline_dps else None,
            "dps_gain_per_million_gp": round(gain * 1000000 / cost, 8) if cost else None,
            "weapon": row.get("weapon"), "slot_changes": changes,
            "selected_items": selected, "warnings": row.get("warnings", [])
        })
    recommendations.sort(key=lambda x: (-x["dps_gain"], x["upgrade_cost_gp"],
                                        -(x["dps_gain_per_million_gp"] or 0)))
    for rank, row in enumerate(recommendations, 1):
        row["rank"] = rank
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": "upgrade_recommendations_with_limitations" if recommendations else "no_improving_upgrade_found",
        "attack_style": attack_style, "upgrade_budget_gp": budget,
        "baseline": {"item_ids": baseline_ids, "total_cost_gp": 0,
                     "dps": baseline["combat_result"]["dps"],
                     "hit_chance": baseline["combat_result"]["hit_chance"],
                     "max_hit": baseline["combat_result"]["max_hit"],
                     "weapon": baseline["weapon"]},
        "recommendations": recommendations,
        "search": search.get("search", {}),
        "candidate_counts": search.get("candidate_counts", {}),
        "eligibility_audit": search.get("eligibility_audit", []),
        "warnings": baseline.get("warnings", []),
        "guardrails": [
            "Baseline items are treated as owned at zero cost; budget applies to replacement items.",
            "Prices and effective combat/target inputs are caller-supplied, not live GE data.",
            "Uses scoped baseline melee arithmetic, not boss-verified DPS; prayers, potions, specials, phases, immunities, set effects, damage caps and supplies are not modelled.",
            "Unknown skill or quest requirements are withheld by the existing eligibility gate.",
            "Candidate and node limits can truncate search; inspect search.truncated.",
            "Compatibility beyond unique slots and one weapon is not fully proven."
        ]
    }

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equipment", default=str(DIST / "equipment-stats.json"))
    parser.add_argument("--requirements", default=str(DIST / "item-requirements.json"))
    parser.add_argument("--quest-unlocks", required=True)
    parser.add_argument("--profiles", default=str(DIST / "item-combat-profiles.json"))
    parser.add_argument("--profile", required=True)
    parser.add_argument("--baseline", required=True, help="JSON array of currently equipped item IDs")
    parser.add_argument("--costs", required=True)
    parser.add_argument("--combat-inputs", required=True)
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--style", choices=("stab", "slash", "crush"), default="slash")
    parser.add_argument("--candidates-per-slot", type=int, default=8)
    parser.add_argument("--node-limit", type=int, default=100000)
    parser.add_argument("--output", default=str(REPORTS / "combat-studio-upgrade-plan.json"))
    args = parser.parse_args()
    try:
        result = plan_upgrades(read_json(args.equipment), read_json(args.requirements),
            read_json(args.quest_unlocks), read_json(args.profiles), read_json(args.profile),
            read_json(args.baseline), read_json(args.costs), args.budget,
            read_json(args.combat_inputs), args.style, args.candidates_per_slot, args.node_limit)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "baseline", "recommendations", "search", "candidate_counts")}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
