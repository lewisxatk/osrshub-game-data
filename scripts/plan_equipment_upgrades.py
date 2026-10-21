#!/usr/bin/env python3
"""Create a conservative, price-input-driven equipment upgrade shortlist.

This is a slot-level candidate ranker, not a full DPS optimiser. Prices must be
provided by the caller because live GE pricing is intentionally out of scope.
Unknown quest/unlock restrictions remain visible and block a 'confirmed usable'
claim. No item is called best-in-slot from this report alone.
"""
from __future__ import annotations
import argparse, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
OBJECTIVES = {
    "attack_stab": "bonuses.attack_stab",
    "attack_slash": "bonuses.attack_slash",
    "attack_crush": "bonuses.attack_crush",
    "attack_magic": "bonuses.attack_magic",
    "attack_ranged": "bonuses.attack_ranged",
    "melee_strength": "bonuses.melee_strength",
    "ranged_strength": "bonuses.ranged_strength",
    "magic_damage": "bonuses.magic_damage",
    "defence_stab": "bonuses.defence_stab",
    "defence_slash": "bonuses.defence_slash",
    "defence_crush": "bonuses.defence_crush",
    "defence_magic": "bonuses.defence_magic",
    "defence_ranged": "bonuses.defence_ranged",
    "prayer": "bonuses.prayer",
}

def canonical(value: str) -> str:
    return " ".join(value.casefold().split())

def numeric_bonus(item: dict, objective: str) -> float | None:
    bonuses = item.get("bonuses")
    value = bonuses.get(objective) if isinstance(bonuses, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)

def evaluate_candidate(item: dict, requirements_by_id: dict, profile: dict, costs: dict, budget: int, objective: str) -> dict:
    item_id, name = item.get("id"), item.get("name", "")
    reasons = []
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
        return {"item_id": item_id, "item_name": name, "status": "unknown", "reasons": ["Invalid item ID"]}
    if not isinstance(name, str):
        name = ""
    excluded_ids = profile.get("excluded_item_ids", [])
    excluded_names = profile.get("excluded_item_names", [])
    excluded = (isinstance(excluded_ids, list) and item_id in excluded_ids) or (
        isinstance(excluded_names, list) and canonical(name) in {canonical(x) for x in excluded_names if isinstance(x, str)}
    )
    cost = costs.get(str(item_id), costs.get(item_id))
    if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
        return {"item_id": item_id, "item_name": name, "status": "unknown", "cost": None,
                "objective_value": numeric_bonus(item, objective), "reasons": ["No valid caller-supplied non-negative integer cost; affordability cannot be checked"]}
    value = numeric_bonus(item, objective)
    if value is None:
        return {"item_id": item_id, "item_name": name, "status": "unknown", "cost": cost,
                "objective_value": None, "reasons": [f"Missing or non-numeric {objective} bonus"]}
    if excluded:
        return {"item_id": item_id, "item_name": name, "status": "excluded", "cost": cost,
                "objective_value": value, "reasons": ["Manually excluded by player"]}
    if cost > budget:
        return {"item_id": item_id, "item_name": name, "status": "over_budget", "cost": cost,
                "objective_value": value, "reasons": [f"Cost exceeds available budget of {budget}"]}
    skills = profile.get("skills")
    if not isinstance(skills, dict):
        skills = {}
        reasons.append("Player skill profile missing or malformed")
    normalized_skills = {canonical(k): v for k, v in skills.items() if isinstance(k, str)}
    records = requirements_by_id.get(item_id, [])
    if not records:
        reasons.append("No normalized skill-requirement record exists")
    unmet = []
    missing = []
    for record in records:
        reqs = record.get("requirements")
        if not isinstance(reqs, list):
            reasons.append("Malformed skill requirement record")
            continue
        for req in reqs:
            if not isinstance(req, dict) or not isinstance(req.get("skill"), str) or isinstance(req.get("level"), bool) or not isinstance(req.get("level"), int):
                reasons.append("Malformed skill requirement entry")
                continue
            skill = canonical(req["skill"])
            level = normalized_skills.get(skill)
            if isinstance(level, bool) or not isinstance(level, int):
                missing.append(req["skill"])
            elif level < req["level"]:
                unmet.append({"skill": req["skill"], "required": req["level"], "player": level})
    if unmet:
        return {"item_id": item_id, "item_name": name, "status": "ineligible_by_known_skill_requirement",
                "cost": cost, "objective_value": value, "unmet_skills": unmet,
                "reasons": [f"Requires {x['skill']} {x['required']} (player has {x['player']})" for x in unmet]}
    if missing:
        reasons.append("Missing player levels for: " + ", ".join(sorted(set(missing), key=str.casefold)))
    reasons.append("Quest/unlock restrictions and completeness of upstream requirements are not verified")
    return {"item_id": item_id, "item_name": name, "status": "candidate_with_unknown_restrictions",
            "cost": cost, "objective_value": value, "reasons": reasons}

def build_plan(equipment: Any, requirements: Any, profile: Any, costs: Any, budget: int, objective: str, top_n: int = 5) -> dict:
    if not isinstance(equipment, list) or any(not isinstance(x, dict) for x in equipment):
        raise ValueError("equipment must be an array of objects")
    if not isinstance(requirements, list) or any(not isinstance(x, dict) for x in requirements):
        raise ValueError("requirements must be an array of objects")
    if not isinstance(profile, dict):
        raise ValueError("profile must be an object")
    if not isinstance(costs, dict):
        raise ValueError("costs must be an object mapping item IDs to integer costs")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError("budget must be a non-negative integer")
    if objective not in OBJECTIVES:
        raise ValueError(f"unsupported objective; choose one of: {', '.join(sorted(OBJECTIVES))}")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 50:
        raise ValueError("top_n must be between 1 and 50")
    requirements_by_id = {}
    for row in requirements:
        rid = row.get("item_id")
        if isinstance(rid, int) and not isinstance(rid, bool):
            requirements_by_id.setdefault(rid, []).append(row)
    slots = {}
    for item in equipment:
        slot = item.get("slot")
        if not isinstance(slot, str) or not slot.strip():
            continue
        candidate = evaluate_candidate(item, requirements_by_id, profile, costs, budget, objective)
        candidate["slot"] = slot
        slots.setdefault(canonical(slot), []).append(candidate)
    ranked = {}
    for slot, rows in sorted(slots.items()):
        rows.sort(key=lambda row: (
            row["status"] != "candidate_with_unknown_restrictions",
            -(row["objective_value"] if isinstance(row.get("objective_value"), (int, float)) else float("-inf")),
            row.get("cost") if isinstance(row.get("cost"), int) else float("inf"),
            row.get("item_name", "").casefold(),
        ))
        ranked[slot] = rows[:top_n]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "candidate_shortlist_only",
        "budget": budget,
        "objective": objective,
        "objective_field": OBJECTIVES[objective],
        "slots_with_candidates": len(ranked),
        "results_by_slot": ranked,
        "guardrails": [
            "Costs are supplied by the caller; no live GE price is fetched.",
            "This ranks one item at a time within each slot and does not optimise complete multi-slot combinations.",
            "Quest, unlock, item-variant and full requirement coverage remain unverified; no candidate is confirmed usable.",
            "A larger single bonus is not equivalent to higher DPS, kill speed or best-in-slot performance."
        ]
    }

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--costs", required=True, help="JSON object mapping item IDs to integer costs in GP")
    parser.add_argument("--budget", required=True, type=int, help="Available GP budget")
    parser.add_argument("--objective", required=True, choices=sorted(OBJECTIVES))
    parser.add_argument("--equipment", default=str(DIST / "equipment-stats.json"))
    parser.add_argument("--requirements", default=str(DIST / "item-requirements.json"))
    parser.add_argument("--output", default=str(REPORTS / "equipment-shortlist.json"))
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    try:
        result = build_plan(read_json(args.equipment), read_json(args.requirements), read_json(args.profile),
                            read_json(args.costs), args.budget, args.objective, args.top)
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
