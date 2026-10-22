#!/usr/bin/env python3
"""Compare two supplied OSRS melee loadouts under identical scoped baseline inputs.

This is an upgrade-delta tool, not a loadout searcher or boss-accurate simulator.
It deliberately evaluates both loadouts with the same caller-supplied levels,
target defence, style, prices, and profile dataset, then reports changed slots,
cost delta, bonus deltas and estimated DPS delta. Unknown restrictions remain
warnings; they are never silently treated as satisfied.
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from evaluate_combat_loadout import evaluate_loadout

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

def _loadout_by_slot(result):
    return {item["slot"]: item for item in result["selected_items"]}

def compare_loadouts(profiles, baseline_ids, candidate_ids, costs, budget, inputs, attack_style):
    baseline = evaluate_loadout(profiles, baseline_ids, costs, budget, inputs, attack_style)
    candidate = evaluate_loadout(profiles, candidate_ids, costs, budget, inputs, attack_style)
    before, after = _loadout_by_slot(baseline), _loadout_by_slot(candidate)
    changes = []
    for slot in sorted(set(before) | set(after)):
        old, new = before.get(slot), after.get(slot)
        if old and new and old["item_id"] == new["item_id"]:
            continue
        changes.append({
            "slot": slot,
            "baseline_item_id": old["item_id"] if old else None,
            "baseline_item_name": old["item_name"] if old else None,
            "candidate_item_id": new["item_id"] if new else None,
            "candidate_item_name": new["item_name"] if new else None,
            "baseline_cost_gp": old["cost_gp"] if old else 0,
            "candidate_cost_gp": new["cost_gp"] if new else 0,
            "cost_delta_gp": (new["cost_gp"] if new else 0) - (old["cost_gp"] if old else 0),
            "attack_bonus_delta": (new["attack_bonus_contribution"] if new else 0) - (old["attack_bonus_contribution"] if old else 0),
            "melee_strength_delta": (new["melee_strength_contribution"] if new else 0) - (old["melee_strength_contribution"] if old else 0),
        })
    bcombat, ccombat = baseline["combat_result"], candidate["combat_result"]
    # combat_math.calculate_core returns DPS at combat_result.dps; guard against schema drift.
    bdps, cdps = bcombat.get("dps"), ccombat.get("dps")
    if isinstance(bdps, bool) or not isinstance(bdps, (int, float)) or isinstance(cdps, bool) or not isinstance(cdps, (int, float)):
        raise ValueError("combat evaluator did not return numeric DPS; refusing to create an upgrade delta")
    bcost, ccost = baseline["total_cost_gp"], candidate["total_cost_gp"]
    warnings = sorted(set(baseline["warnings"] + candidate["warnings"]))
    if not changes:
        warnings.append("Baseline and candidate loadouts are identical; no slot upgrades were evaluated")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "baseline_upgrade_delta_with_limitations",
        "attack_style": attack_style,
        "budget_gp": budget,
        "baseline": {"total_cost_gp": bcost, "remaining_budget_gp": budget-bcost, "dps": round(float(bdps), 8),
                     "attack_bonus": baseline["aggregated_bonuses"]["attack_style_bonus"],
                     "melee_strength": baseline["aggregated_bonuses"]["melee_strength"],
                     "weapon": baseline["weapon"]},
        "candidate": {"total_cost_gp": ccost, "remaining_budget_gp": budget-ccost, "dps": round(float(cdps), 8),
                      "attack_bonus": candidate["aggregated_bonuses"]["attack_style_bonus"],
                      "melee_strength": candidate["aggregated_bonuses"]["melee_strength"],
                      "weapon": candidate["weapon"]},
        "delta": {"cost_gp": ccost-bcost, "dps": round(float(cdps)-float(bdps), 8),
                  "dps_percent": round(((float(cdps)-float(bdps))/float(bdps))*100, 4) if float(bdps) else None,
                  "attack_bonus": candidate["aggregated_bonuses"]["attack_style_bonus"]-baseline["aggregated_bonuses"]["attack_style_bonus"],
                  "melee_strength": candidate["aggregated_bonuses"]["melee_strength"]-baseline["aggregated_bonuses"]["melee_strength"]},
        "slot_changes": changes,
        "warnings": sorted(set(warnings)),
        "guardrails": [
            "Both loadouts use identical caller-supplied effective levels and target-defence inputs.",
            "DPS is the repository's scoped baseline estimate, not boss-specific verified DPS.",
            "No prayers, potions, special attacks, monster phases, immunities, damage caps or supplies are modelled.",
            "Item costs are caller-supplied and are not live Grand Exchange prices.",
            "Skill, quest and unlock restrictions are not fully verified; warnings must be reviewed.",
            "A positive DPS delta is conditional on the supplied inputs and mechanics being appropriate."
        ]
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="JSON array of baseline selected item IDs")
    parser.add_argument("--candidate", required=True, help="JSON array of candidate selected item IDs")
    parser.add_argument("--costs", required=True, help="JSON object mapping item IDs to GP costs")
    parser.add_argument("--inputs", required=True, help="JSON object with shared precomputed combat inputs")
    parser.add_argument("--budget", required=True, type=int)
    parser.add_argument("--style", choices=("stab", "slash", "crush"), required=True)
    parser.add_argument("--profiles", default=str(DIST / "item-combat-profiles.json"))
    parser.add_argument("--output", default=str(REPORTS / "loadout-upgrade-delta.json"))
    args = parser.parse_args()
    try:
        load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
        result = compare_loadouts(load(args.profiles), load(args.baseline), load(args.candidate),
                                  load(args.costs), args.budget, load(args.inputs), args.style)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
