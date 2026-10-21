#!/usr/bin/env python3
"""Compare database weapons with scoped baseline DPS arithmetic.

Requires caller-supplied effective combat levels, target defence roll inputs,
and GP costs. Uses normalized weapon speed and equipment bonuses when present.
This is a baseline comparison only: it does not model weapon-specific special
effects, prayers, potions, target mechanics, or full eligibility.
"""
from __future__ import annotations
import argparse, json, math
from datetime import datetime, timezone
from pathlib import Path
from combat_math import calculate_core

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
ATTACK_FIELDS = {"stab": "attack_stab", "slash": "attack_slash", "crush": "attack_crush"}

def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None

def compare_weapons(weapons, equipment, requirements, profile, costs, inputs, budget, attack_style):
    for name, value in (("weapons", weapons), ("equipment", equipment), ("requirements", requirements)):
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            raise ValueError(f"{name} must be an array of objects")
    if not isinstance(profile, dict) or not isinstance(costs, dict) or not isinstance(inputs, dict):
        raise ValueError("profile, costs and combat inputs must be JSON objects")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError("budget must be a non-negative integer")
    if attack_style not in ATTACK_FIELDS:
        raise ValueError("attack_style must be stab, slash or crush")
    required_inputs = ("effective_attack", "effective_strength", "effective_defence", "defence_bonus")
    missing = [key for key in required_inputs if key not in inputs]
    if missing:
        raise ValueError("missing baseline combat inputs: " + ", ".join(missing))
    equipment_by_id = {row.get("id"): row for row in equipment if isinstance(row.get("id"), int) and not isinstance(row.get("id"), bool)}
    requirements_by_id = {}
    for row in requirements:
        rid = row.get("item_id")
        if isinstance(rid, int) and not isinstance(rid, bool):
            requirements_by_id.setdefault(rid, []).append(row)
    skills = profile.get("skills") if isinstance(profile.get("skills"), dict) else {}
    skills = {" ".join(k.casefold().split()): v for k, v in skills.items() if isinstance(k, str)}
    excluded_ids = profile.get("excluded_item_ids", [])
    excluded_ids = set(x for x in excluded_ids if isinstance(x, int) and not isinstance(x, bool)) if isinstance(excluded_ids, list) else set()
    excluded_names = profile.get("excluded_item_names", [])
    excluded_names = {" ".join(x.casefold().split()) for x in excluded_names if isinstance(x, str)} if isinstance(excluded_names, list) else set()
    results = []
    for weapon in weapons:
        wid, name = weapon.get("id"), weapon.get("name", "")
        if isinstance(wid, bool) or not isinstance(wid, int) or wid < 0:
            continue
        gear = equipment_by_id.get(wid)
        if not isinstance(gear, dict):
            results.append({"item_id": wid, "item_name": name, "status": "unknown", "reasons": ["No matching normalized equipment-stat record"]})
            continue
        speed = weapon.get("attack_speed")
        bonuses = gear.get("bonuses") if isinstance(gear.get("bonuses"), dict) else {}
        attack_bonus = _number(bonuses.get(ATTACK_FIELDS[attack_style]))
        strength_bonus = _number(bonuses.get("melee_strength"))
        cost = costs.get(str(wid), costs.get(wid))
        reasons = []
        if wid in excluded_ids or (isinstance(name, str) and " ".join(name.casefold().split()) in excluded_names):
            results.append({"item_id": wid, "item_name": name, "status": "excluded", "cost": cost, "reasons": ["Manually excluded by player"]})
            continue
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            results.append({"item_id": wid, "item_name": name, "status": "unknown", "cost": None, "reasons": ["No valid caller-supplied GP cost"]})
            continue
        if cost > budget:
            results.append({"item_id": wid, "item_name": name, "status": "over_budget", "cost": cost, "reasons": [f"Cost exceeds budget of {budget} GP"]})
            continue
        if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0 or attack_bonus is None or strength_bonus is None:
            results.append({"item_id": wid, "item_name": name, "status": "unknown", "cost": cost, "reasons": ["Missing valid attack speed or required attack/strength bonus"]})
            continue
        unmet, missing_levels, malformed = [], [], []
        req_records = requirements_by_id.get(wid, [])
        if not req_records:
            reasons.append("No normalized skill requirement record exists")
        for req_record in req_records:
            reqs = req_record.get("requirements")
            if not isinstance(reqs, list):
                malformed.append("Malformed requirement record")
                continue
            for req in reqs:
                if not isinstance(req, dict) or not isinstance(req.get("skill"), str) or isinstance(req.get("level"), bool) or not isinstance(req.get("level"), int):
                    malformed.append("Malformed requirement entry")
                    continue
                key = " ".join(req["skill"].casefold().split())
                level = skills.get(key)
                if isinstance(level, bool) or not isinstance(level, int):
                    missing_levels.append(req["skill"])
                elif level < req["level"]:
                    unmet.append({"skill": req["skill"], "required": req["level"], "player": level})
        if unmet:
            results.append({"item_id": wid, "item_name": name, "status": "ineligible_by_known_skill_requirement", "cost": cost, "unmet_skills": unmet, "reasons": [f"Requires {x['skill']} {x['required']} (player has {x['player']})" for x in unmet]})
            continue
        if malformed:
            results.append({"item_id": wid, "item_name": name, "status": "unknown", "cost": cost, "reasons": malformed})
            continue
        combat_inputs = {
            "effective_attack": inputs["effective_attack"],
            "attack_bonus": int(attack_bonus),
            "effective_defence": inputs["effective_defence"],
            "defence_bonus": inputs["defence_bonus"],
            "effective_strength": inputs["effective_strength"],
            "strength_bonus": int(strength_bonus),
            "attack_speed_ticks": speed,
        }
        try:
            calc = calculate_core(combat_inputs)
        except (ValueError, TypeError) as exc:
            results.append({"item_id": wid, "item_name": name, "status": "unknown", "cost": cost, "reasons": [f"Invalid baseline input: {exc}"]})
            continue
        if missing_levels:
            reasons.append("Player skill levels missing for: " + ", ".join(sorted(set(missing_levels), key=str.casefold)))
        reasons.append("Quest/unlock restrictions and special weapon mechanics are not modelled")
        results.append({
            "item_id": wid, "item_name": name,
            "status": "baseline_comparable_with_unknown_restrictions",
            "cost": cost, "attack_speed_ticks": speed,
            "attack_bonus_used": ATTACK_FIELDS[attack_style], "attack_bonus": int(attack_bonus),
            "melee_strength_bonus": int(strength_bonus),
            "attack_roll": calc["attack_roll"], "defence_roll": calc["defence_roll"],
            "hit_chance": calc["hit_chance"], "max_hit": calc["max_hit"],
            "expected_damage_per_attack": calc["expected_damage_per_attack"], "dps": calc["dps"],
            "source_url": weapon.get("source_url") or gear.get("source_url"),
            "reasons": reasons,
        })
    results.sort(key=lambda row: (
        row.get("status") != "baseline_comparable_with_unknown_restrictions",
        -(row.get("dps") if isinstance(row.get("dps"), (int,float)) else -1),
        row.get("cost") if isinstance(row.get("cost"), int) else float("inf"),
        str(row.get("item_name", "")).casefold(),
    ))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "baseline_comparison_only",
        "budget_gp": budget, "attack_style": attack_style,
        "combat_inputs": inputs, "candidate_count": len(results),
        "results": results,
        "guardrails": [
            "DPS is a simplified baseline using caller-supplied effective levels and source-recorded attack speed/bonuses.",
            "Prices are caller supplied; no live Grand Exchange data is fetched.",
            "Quest/unlock requirements, boosts, prayers, special attacks, damage distribution exceptions, boss phases and immunities are not modelled.",
            "Do not use this report as a boss-specific best-in-slot answer without adding and verifying the relevant mechanics."
        ]
    }

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--costs", required=True)
    parser.add_argument("--inputs", required=True, help="JSON: effective_attack, effective_strength, effective_defence, defence_bonus")
    parser.add_argument("--budget", required=True, type=int)
    parser.add_argument("--style", required=True, choices=sorted(ATTACK_FIELDS))
    parser.add_argument("--weapons", default=str(DIST / "weapons.json"))
    parser.add_argument("--equipment", default=str(DIST / "equipment-stats.json"))
    parser.add_argument("--requirements", default=str(DIST / "item-requirements.json"))
    parser.add_argument("--output", default=str(REPORTS / "weapon-baseline-comparison.json"))
    args = parser.parse_args()
    try:
        result = compare_weapons(read_json(args.weapons), read_json(args.equipment), read_json(args.requirements),
            read_json(args.profile), read_json(args.costs), read_json(args.inputs), args.budget, args.style)
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
