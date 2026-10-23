#!/usr/bin/env python3
"""Build a conservative account-aware Combat Studio gear plan.

Ranks complete slot combinations by a selected equipment bonus, subject to an
upgrade budget. This is an actionable planner foundation, NOT a DPS optimiser.
Unknown requirements never become confirmed eligible. Costs are caller supplied.
"""
from __future__ import annotations
import argparse, json, math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
OBJECTIVES = {
    "attack_stab": "attack_stab", "attack_slash": "attack_slash",
    "attack_crush": "attack_crush", "attack_magic": "attack_magic",
    "attack_ranged": "attack_ranged", "melee_strength": "melee_strength",
    "ranged_strength": "ranged_strength", "magic_damage": "magic_damage",
    "defence_stab": "defence_stab", "defence_slash": "defence_slash",
    "defence_crush": "defence_crush", "defence_magic": "defence_magic",
    "defence_ranged": "defence_ranged", "prayer": "prayer",
}

def canonical(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""

def index_by_id(rows, key):
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            result.setdefault(value, []).append(row)
    return result

def valid_cost(cost):
    return isinstance(cost, int) and not isinstance(cost, bool) and cost >= 0

def build_plan(equipment, requirements, quest_unlocks, profile, costs, budget,
               objective="melee_strength", top_per_slot=12, node_limit=150000):
    if not isinstance(equipment, list) or any(not isinstance(x, dict) for x in equipment):
        raise ValueError("equipment must be an array of objects")
    if not isinstance(requirements, list) or not isinstance(quest_unlocks, list):
        raise ValueError("requirements and quest_unlocks must be arrays")
    if not isinstance(profile, dict) or not isinstance(costs, dict):
        raise ValueError("profile and costs must be objects")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise ValueError("budget must be a non-negative integer")
    if objective not in OBJECTIVES:
        raise ValueError("unsupported objective: " + str(objective))
    if isinstance(top_per_slot, bool) or not isinstance(top_per_slot, int) or not 1 <= top_per_slot <= 50:
        raise ValueError("top_per_slot must be between 1 and 50")
    if isinstance(node_limit, bool) or not isinstance(node_limit, int) or node_limit < 1:
        raise ValueError("node_limit must be positive")

    skill_rows = index_by_id(requirements, "item_id")
    quest_rows = index_by_id(quest_unlocks, "item_id")
    skills = {canonical(k): v for k, v in profile.get("skills", {}).items() if isinstance(k, str)} if isinstance(profile.get("skills"), dict) else {}
    completed_raw = profile.get("completed_quests", [])
    completed = {canonical(x) for x in completed_raw if isinstance(x, str)} if isinstance(completed_raw, list) else set()
    excluded_ids = {x for x in profile.get("excluded_item_ids", []) if isinstance(x, int) and not isinstance(x, bool)} if isinstance(profile.get("excluded_item_ids", []), list) else set()
    excluded_names = {canonical(x) for x in profile.get("excluded_item_names", []) if isinstance(x, str)} if isinstance(profile.get("excluded_item_names", []), list) else set()
    # Added items are candidate requests only. They do not bypass actual restrictions.
    added_ids = {x for x in profile.get("added_item_ids", []) if isinstance(x, int) and not isinstance(x, bool)} if isinstance(profile.get("added_item_ids", []), list) else set()
    current = profile.get("current_equipment", {})
    if not isinstance(current, dict):
        current = {}
    current_ids = {x for x in current.values() if isinstance(x, int) and not isinstance(x, bool)}
    candidates_by_slot = {}
    audit = []
    seen_ids = set()

    for item in equipment:
        item_id, name, slot = item.get("id"), item.get("name", ""), item.get("slot")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0 or item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        if not isinstance(name, str) or not isinstance(slot, str) or not slot.strip():
            continue
        bonuses = item.get("bonuses")
        value = bonuses.get(OBJECTIVES[objective]) if isinstance(bonuses, dict) else None
        reasons = []
        status = "eligible"
        if item_id in excluded_ids or canonical(name) in excluded_names:
            status = "excluded"
            reasons.append("Manually excluded by player")
        else:
            req_records = skill_rows.get(item_id, [])
            if not req_records or any(r.get("requirements_status") not in ("known", "known_empty") for r in req_records):
                status = "unknown"
                reasons.append("Skill-requirement data is missing or incomplete")
            else:
                unmet = []
                missing = []
                for record in req_records:
                    reqs = record.get("requirements")
                    if not isinstance(reqs, list):
                        status = "unknown"; reasons.append("Malformed skill requirement record"); continue
                    for req in reqs:
                        if not isinstance(req, dict) or not isinstance(req.get("skill"), str) or isinstance(req.get("level"), bool) or not isinstance(req.get("level"), int):
                            status = "unknown"; reasons.append("Malformed skill requirement entry"); continue
                        level = skills.get(canonical(req["skill"]))
                        if isinstance(level, bool) or not isinstance(level, int):
                            missing.append(req["skill"])
                        elif level < req["level"]:
                            unmet.append((req["skill"], req["level"], level))
                if unmet:
                    status = "ineligible"
                    reasons.extend(f"Requires {skill} {need}; account has {have}" for skill, need, have in unmet)
                elif missing and status != "unknown":
                    status = "unknown"
                    reasons.append("Account is missing levels for: " + ", ".join(sorted(set(missing), key=str.casefold)))

            qrecords = quest_rows.get(item_id, [])
            if not qrecords or any(r.get("requirements_status") not in ("known", "known_empty") for r in qrecords):
                if status == "eligible": status = "unknown"
                reasons.append("Quest/unlock requirement data is missing or incomplete")
            else:
                unmet_quests = []
                for record in qrecords:
                    req_quests = record.get("required_quests")
                    if not isinstance(req_quests, list):
                        if status == "eligible": status = "unknown"
                        reasons.append("Malformed quest/unlock requirement record")
                        continue
                    for quest in req_quests:
                        if not isinstance(quest, str) or not canonical(quest):
                            if status == "eligible": status = "unknown"
                            reasons.append("Malformed quest name in unlock data")
                        elif canonical(quest) not in completed:
                            unmet_quests.append(quest)
                if unmet_quests:
                    status = "ineligible"
                    reasons.extend("Requires completed quest: " + q for q in sorted(set(unmet_quests), key=str.casefold))

        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            if status == "eligible": status = "unknown"
            reasons.append("Objective bonus is missing or invalid")
        raw_cost = costs.get(str(item_id), costs.get(item_id))
        owned = item_id in current_ids
        cost = 0 if owned else raw_cost
        if not valid_cost(cost):
            if status == "eligible": status = "unknown"
            reasons.append("No valid caller-supplied cost; affordability cannot be checked")
        elif cost > budget:
            if status == "eligible": status = "over_budget"
            reasons.append("Upgrade cost exceeds available budget")
        row = {
            "item_id": item_id, "item_name": name, "slot": slot, "status": status,
            "objective_value": float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None,
            "market_cost_gp": raw_cost if valid_cost(raw_cost) else None,
            "upgrade_cost_gp": cost if valid_cost(cost) else None,
            "already_owned": owned, "user_added_candidate": item_id in added_ids,
            "reasons": sorted(set(reasons), key=str.casefold),
            "source_urls": item.get("source_urls", []),
        }
        audit.append(row)
        if status == "eligible" and valid_cost(cost) and cost <= budget and row["objective_value"] is not None:
            candidates_by_slot.setdefault(canonical(slot), []).append(row)

    # Bounded branch-and-bound search. Each slot may be left unchanged/empty.
    slots = []
    for slot, rows in sorted(candidates_by_slot.items()):
        rows.sort(key=lambda r: (-r["objective_value"], r["upgrade_cost_gp"], r["item_name"].casefold(), r["item_id"]))
        slots.append((slot, rows[:top_per_slot]))
    suffix = [0.0] * (len(slots) + 1)
    for i in range(len(slots) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + max([0.0] + [r["objective_value"] for r in slots[i][1]])
    best = {"value": 0.0, "cost": 0, "items": []}
    nodes, truncated = 0, False
    def visit(index, cost, value, chosen, chosen_ids):
        nonlocal nodes, truncated, best
        nodes += 1
        if nodes > node_limit:
            truncated = True
            return
        if value + suffix[index] < best["value"]:
            return
        if index == len(slots):
            if value > best["value"] or (value == best["value"] and cost < best["cost"]):
                best = {"value": value, "cost": cost, "items": list(chosen)}
            return
        visit(index + 1, cost, value, chosen, chosen_ids)
        if truncated: return
        for row in slots[index][1]:
            if row["item_id"] in chosen_ids: continue
            new_cost = cost + row["upgrade_cost_gp"]
            if new_cost <= budget:
                visit(index + 1, new_cost, value + row["objective_value"], chosen + [row], chosen_ids | {row["item_id"]})
                if truncated: return
    visit(0, 0, 0.0, [], set())
    selected_by_slot = {canonical(r["slot"]): r for r in best["items"]}
    upgrade_path = []
    for slot, current_id in sorted(current.items(), key=lambda x: canonical(x[0])):
        if isinstance(current_id, bool) or not isinstance(current_id, int): continue
        target = selected_by_slot.get(canonical(slot))
        if target and target["item_id"] != current_id:
            current_item = next((x for x in equipment if x.get("id") == current_id), None)
            current_bonus = current_item.get("bonuses", {}).get(OBJECTIVES[objective]) if isinstance(current_item, dict) and isinstance(current_item.get("bonuses"), dict) else None
            delta = target["objective_value"] - current_bonus if isinstance(current_bonus, (int, float)) and not isinstance(current_bonus, bool) else None
            upgrade_path.append({
                "slot": slot, "from_item_id": current_id,
                "from_item_name": current_item.get("name") if isinstance(current_item, dict) else None,
                "to_item_id": target["item_id"], "to_item_name": target["item_name"],
                "upgrade_cost_gp": target["upgrade_cost_gp"], "objective_delta": delta,
                "note": "Stat-objective delta only; this is not a DPS improvement estimate."
            })
    unknown = sum(r["status"] == "unknown" for r in audit)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "search_truncated" if truncated else "account_aware_stat_plan",
        "objective": objective, "objective_field": "bonuses." + OBJECTIVES[objective],
        "budget_gp": budget, "upgrade_cost_gp": best["cost"], "remaining_budget_gp": budget - best["cost"],
        "objective_total": round(best["value"], 6),
        "selected_items": [{k: r[k] for k in ("item_id","item_name","slot","objective_value","market_cost_gp","upgrade_cost_gp","already_owned","user_added_candidate","source_urls")} for r in best["items"]],
        "upgrade_path": upgrade_path,
        "candidate_counts": {
            "total_items_audited": len(audit), "eligible_candidates": sum(r["status"] == "eligible" for r in audit),
            "unknown_restrictions": unknown, "ineligible": sum(r["status"] == "ineligible" for r in audit),
            "manually_excluded": sum(r["status"] == "excluded" for r in audit),
            "over_budget": sum(r["status"] == "over_budget" for r in audit),
        },
        "audit": audit,
        "search": {"slots_considered": len(slots), "nodes_visited": min(nodes, node_limit), "node_limit": node_limit, "truncated": truncated},
        "guardrails": [
            "This is a budgeted sum-of-one-bonus-per-slot planner, not a DPS optimiser or best-in-slot claim.",
            "Quest eligibility is only as reliable as explicit item quest-unlock records and completed quest names supplied.",
            "Missing/incomplete skill or quest requirement data is not treated as eligible.",
            "Manually excluded items are never selected; added_item_ids only flags requested candidates and cannot bypass restrictions.",
            "Already-owned items have zero upgrade cost when listed in current_equipment.",
            "Prices are caller-supplied; no live Grand Exchange prices are fetched.",
            "Unknown combat mechanics, set effects, item variants and boss-specific restrictions are not inferred."
        ]
    }

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--costs", required=True)
    parser.add_argument("--budget", required=True, type=int)
    parser.add_argument("--objective", choices=sorted(OBJECTIVES), default="melee_strength")
    parser.add_argument("--equipment", default=str(DIST / "equipment-stats.json"))
    parser.add_argument("--requirements", default=str(DIST / "item-requirements.json"))
    parser.add_argument("--quest-unlocks", required=True, help="Explicit item_id, required_quests, requirements_status records")
    parser.add_argument("--output", default=str(REPORTS / "combat-studio-plan.json"))
    parser.add_argument("--top-per-slot", type=int, default=12)
    parser.add_argument("--node-limit", type=int, default=150000)
    args = parser.parse_args()
    try:
        result = build_plan(read_json(args.equipment), read_json(args.requirements), read_json(args.quest_unlocks),
                            read_json(args.profile), read_json(args.costs), args.budget,
                            args.objective, args.top_per_slot, args.node_limit)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status":"failed","error":str(exc)}, indent=2)); return 1
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "audit"}, ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
