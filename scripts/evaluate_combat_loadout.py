#!/usr/bin/env python3
"""Evaluate a user-selected melee loadout with explicit, scoped baseline DPS math."""
from __future__ import annotations
import argparse, json, math
from datetime import datetime, timezone
from pathlib import Path
from combat_math import calculate_core

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
ATTACK_FIELDS = {"stab": "attack_stab", "slash": "attack_slash", "crush": "attack_crush"}

def evaluate_loadout(profiles, selected_ids, costs, budget, inputs, attack_style):
    if not isinstance(profiles, list) or any(not isinstance(row, dict) for row in profiles):
        raise ValueError("profiles must be an array of objects")
    if not isinstance(selected_ids, list) or not selected_ids:
        raise ValueError("selected_item_ids must be a non-empty array")
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in selected_ids):
        raise ValueError("selected_item_ids must contain non-negative integer IDs")
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("selected_item_ids contains duplicate IDs")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError("budget_gp must be a non-negative integer")
    if not isinstance(costs, dict) or not isinstance(inputs, dict):
        raise ValueError("costs and combat inputs must be objects")
    if attack_style not in ATTACK_FIELDS:
        raise ValueError("attack_style must be stab, slash or crush")
    by_id = {}
    for row in profiles:
        rid = row.get("id")
        if isinstance(rid, int) and not isinstance(rid, bool):
            if rid in by_id:
                raise ValueError(f"duplicate profile ID {rid}")
            by_id[rid] = row
    missing = [rid for rid in selected_ids if rid not in by_id]
    if missing:
        raise ValueError("selected items missing from combat profiles: " + ", ".join(map(str, missing)))
    required = ("effective_attack", "effective_strength", "effective_defence", "defence_bonus")
    absent = [key for key in required if key not in inputs]
    if absent:
        raise ValueError("missing combat inputs: " + ", ".join(absent))
    total_cost = 0
    total_attack = 0
    total_strength = 0
    selected = []
    warnings = []
    slots = set()
    weapon_rows = []
    for rid in selected_ids:
        row = by_id[rid]
        slot = row.get("slot")
        if not isinstance(slot, str) or not slot.strip():
            warnings.append(f"{row.get('name', rid)} has no known equipment slot")
        elif slot in slots:
            raise ValueError(f"multiple selected items occupy slot {slot!r}")
        else:
            slots.add(slot)
        cost = costs.get(str(rid), costs.get(rid))
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            raise ValueError(f"item {rid} has no valid caller-supplied non-negative integer GP cost")
        total_cost += cost
        bonuses = row.get("bonuses")
        if not isinstance(bonuses, dict):
            raise ValueError(f"item {rid} has no usable bonuses object")
        attack_field = ATTACK_FIELDS[attack_style]
        attack_bonus = bonuses.get(attack_field)
        strength_bonus = bonuses.get("melee_strength")
        for label, value in ((attack_field, attack_bonus), ("melee_strength", strength_bonus)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"item {rid} has unknown or non-integer {label}; refusing to treat it as zero")
        total_attack += attack_bonus
        total_strength += strength_bonus
        if slot == "weapon":
            weapon_rows.append(row)
        reqs = row.get("skill_requirements")
        if reqs is None:
            warnings.append(f"{row.get('name', rid)} has no normalized skill-requirement record")
        if row.get("data_status") != "joined_fields_present":
            warnings.append(f"{row.get('name', rid)} has partial joined combat data")
        selected.append({
            "item_id": rid, "item_name": row.get("name", ""),
            "slot": slot, "cost_gp": cost,
            "attack_bonus_contribution": attack_bonus,
            "melee_strength_contribution": strength_bonus,
            "skill_requirements": reqs,
            "source_urls": row.get("source_urls", []),
            "data_status": row.get("data_status", "partial")
        })
    if total_cost > budget:
        raise ValueError(f"selected loadout costs {total_cost} GP, exceeding budget {budget} GP")
    if len(weapon_rows) != 1:
        raise ValueError(f"select exactly one item in the weapon slot; found {len(weapon_rows)}")
    speed = weapon_rows[0].get("attack_speed")
    if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
        raise ValueError("selected weapon has no valid attack speed")
    combat_inputs = {
        "effective_attack": inputs["effective_attack"],
        "attack_bonus": total_attack,
        "effective_defence": inputs["effective_defence"],
        "defence_bonus": inputs["defence_bonus"],
        "effective_strength": inputs["effective_strength"],
        "strength_bonus": total_strength,
        "attack_speed_ticks": speed
    }
    result = calculate_core(combat_inputs)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "baseline_loadout_estimate_with_limitations",
        "attack_style": attack_style,
        "budget_gp": budget, "total_cost_gp": total_cost, "remaining_budget_gp": budget-total_cost,
        "selected_item_count": len(selected), "selected_items": selected,
        "aggregated_bonuses": {"attack_style_bonus": total_attack, "melee_strength": total_strength},
        "weapon": {"item_id": weapon_rows[0]["id"], "item_name": weapon_rows[0].get("name", ""), "attack_speed_ticks": speed},
        "combat_result": result,
        "warnings": sorted(set(warnings)),
        "guardrails": [
            "This evaluates the supplied loadout; it does not search all possible loadouts.",
            "Only melee stab, slash or crush baseline arithmetic is supported by this evaluator.",
            "Effective levels and target defence inputs are caller-supplied and must be verified separately.",
            "No prayers, potions, special attacks, style-specific max-hit effects, monster phases, immunities, damage caps or supply costs are modelled.",
            "Skill requirements are shown for review but quest/unlock completeness is not verified.",
            "Costs are caller-supplied GP values, not live Grand Exchange prices.",
            "The result is a baseline estimate, not a verified boss-specific DPS result."
        ]
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", required=True, help="JSON array of selected item IDs")
    parser.add_argument("--costs", required=True, help="JSON object mapping item IDs to GP costs")
    parser.add_argument("--inputs", required=True, help="JSON object with precomputed effective levels and target defence")
    parser.add_argument("--budget", required=True, type=int)
    parser.add_argument("--style", choices=sorted(ATTACK_FIELDS), required=True)
    parser.add_argument("--profiles", default=str(DIST / "item-combat-profiles.json"))
    parser.add_argument("--output", default=str(REPORTS / "combat-loadout-evaluation.json"))
    args = parser.parse_args()
    try:
        load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
        result = evaluate_loadout(load(args.profiles), load(args.selected), load(args.costs), args.budget, load(args.inputs), args.style)
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
