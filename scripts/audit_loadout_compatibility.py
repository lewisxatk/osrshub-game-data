#!/usr/bin/env python3
"""Audit a caller-selected loadout against OSRS Hub's generated item database only.

This is a conservative compatibility audit, not a DPS calculator or a complete
quest/unlock oracle. It never makes network requests and never promotes unknown
facts to confirmed eligibility.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / "dist"
DEFAULT_REPORTS = ROOT / "reports"
DATASET = "item-combat-profiles.json"


def canonical(value: Any) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def index_profiles(rows: Any) -> dict[int, dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError(f"{DATASET} must be a JSON array")
    indexed: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{DATASET}[{index}] must be an object")
        item_id = row.get("id")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            raise ValueError(f"{DATASET}[{index}] has an invalid item ID")
        if item_id in indexed:
            raise ValueError(f"{DATASET} contains duplicate item ID {item_id}")
        indexed[item_id] = row
    return indexed


def normalize_skills(profile: Any) -> tuple[dict[str, int], list[str]]:
    if not isinstance(profile, dict):
        raise ValueError("player profile must be a JSON object")
    raw = profile.get("skills")
    if not isinstance(raw, dict):
        return {}, ["Player skill map is missing or malformed"]
    levels: dict[str, int] = {}
    warnings: list[str] = []
    for name, value in raw.items():
        key = canonical(name)
        if not key:
            warnings.append("Blank skill name ignored")
            continue
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 99:
            warnings.append(f"Invalid player level for {name!r}; expected integer 1–99")
            continue
        if key in levels:
            warnings.append(f"Duplicate normalized player skill: {name!r}")
            continue
        levels[key] = value
    return levels, warnings


def evaluate_loadout(selected: Any, profiles: dict[int, dict[str, Any]], profile: Any,
                     costs: Any = None, budget: int | None = None) -> dict[str, Any]:
    if isinstance(selected, list):
        raw_items = selected
    elif isinstance(selected, dict):
        raw_items = selected.get("items", selected.get("selected_items"))
    else:
        raw_items = None
    if not isinstance(raw_items, list):
        raise ValueError("selection must be an array or an object containing items array")
    if budget is not None and (isinstance(budget, bool) or not isinstance(budget, int) or budget < 0):
        raise ValueError("budget must be a non-negative integer")
    if costs is not None and not isinstance(costs, dict):
        raise ValueError("costs must be a JSON object keyed by item ID")

    skills, profile_warnings = normalize_skills(profile)
    excluded_ids = set()
    excluded_names = set()
    completed_quests = set()
    if isinstance(profile, dict):
        for value in profile.get("excluded_item_ids", []) if isinstance(profile.get("excluded_item_ids", []), list) else []:
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                excluded_ids.add(value)
        for value in profile.get("excluded_item_names", []) if isinstance(profile.get("excluded_item_names", []), list) else []:
            if isinstance(value, str) and canonical(value):
                excluded_names.add(canonical(value))
        for value in profile.get("completed_quests", []) if isinstance(profile.get("completed_quests", []), list) else []:
            if isinstance(value, str) and canonical(value):
                completed_quests.add(canonical(value))

    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    seen_slots: set[str] = set()
    total_cost = 0
    known_cost_count = 0

    for index, entry in enumerate(raw_items):
        if isinstance(entry, int) and not isinstance(entry, bool):
            item_id, requested_slot = entry, None
        elif isinstance(entry, dict):
            item_id = entry.get("item_id", entry.get("id"))
            requested_slot = entry.get("slot")
        else:
            errors.append({"code": "invalid_selection_entry", "index": index,
                           "message": "Each selection must be an item ID or object"})
            continue

        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            errors.append({"code": "invalid_item_id", "index": index,
                           "message": "Selected item ID must be a non-negative integer"})
            continue
        if item_id in seen_ids:
            errors.append({"code": "duplicate_item_id", "index": index, "item_id": item_id,
                           "message": "The same item ID is selected more than once"})
        seen_ids.add(item_id)

        row = profiles.get(item_id)
        if row is None:
            errors.append({"code": "item_not_found", "index": index, "item_id": item_id,
                           "message": "Item ID is absent from the generated combat-profile dataset"})
            results.append({"item_id": item_id, "name": None, "status": "unknown",
                            "reasons": ["No generated item-combat-profile record exists"]})
            continue

        name = row.get("name") if isinstance(row.get("name"), str) else ""
        db_slot = row.get("slot") if isinstance(row.get("slot"), str) else None
        reasons: list[str] = []
        item_warnings: list[str] = []
        item_status = "meets_known_checks"

        if requested_slot is not None:
            if not isinstance(requested_slot, str) or not canonical(requested_slot):
                errors.append({"code": "invalid_requested_slot", "index": index, "item_id": item_id,
                               "message": "Requested slot must be a non-empty string"})
                item_status = "review_required"
                reasons.append("Requested equipment slot is malformed")
            else:
                slot_key = canonical(requested_slot)
                if slot_key in seen_slots:
                    errors.append({"code": "duplicate_slot", "index": index, "item_id": item_id,
                                   "slot": requested_slot, "message": "More than one selected item uses the same slot"})
                seen_slots.add(slot_key)
                if db_slot is None:
                    item_status = "review_required"
                    reasons.append("Database has no equipment slot for this item")
                elif canonical(db_slot) != slot_key:
                    errors.append({"code": "slot_mismatch", "index": index, "item_id": item_id,
                                   "requested_slot": requested_slot, "database_slot": db_slot,
                                   "message": "Requested slot conflicts with the generated database slot"})
                    item_status = "incompatible"
                    reasons.append(f"Requested slot {requested_slot!r} conflicts with database slot {db_slot!r}")

        if item_id in excluded_ids or canonical(name) in excluded_names:
            item_status = "excluded"
            reasons.append("Item is manually excluded by the player profile")

        if row.get("equipment_record_present") is not True:
            if item_status not in ("excluded", "incompatible"):
                item_status = "review_required"
            item_warnings.append("Equipment-stat record is missing")

        if row.get("skill_requirement_record_present") is not True or not isinstance(row.get("skill_requirements"), list):
            if item_status not in ("excluded", "incompatible"):
                item_status = "review_required"
            item_warnings.append("Skill requirements are unknown because no valid requirement record is present")
        else:
            unmet = []
            missing_skills = []
            invalid_requirements = []
            for req in row["skill_requirements"]:
                if not isinstance(req, dict) or not isinstance(req.get("skill"), str):
                    invalid_requirements.append("Malformed skill requirement entry")
                    continue
                level = req.get("level")
                if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 99:
                    invalid_requirements.append(f"Invalid requirement level for {req['skill']!r}")
                    continue
                skill = canonical(req["skill"])
                if skill not in skills:
                    missing_skills.append(req["skill"])
                elif skills[skill] < level:
                    unmet.append({"skill": req["skill"], "required": level, "player": skills[skill]})
            if invalid_requirements:
                if item_status not in ("excluded", "incompatible"):
                    item_status = "review_required"
                item_warnings.extend(invalid_requirements)
            elif unmet:
                item_status = "ineligible_by_known_skill_requirement"
                reasons.extend([f"Requires {r['skill']} {r['required']} (profile has {r['player']})" for r in unmet])
            elif missing_skills:
                if item_status not in ("excluded", "incompatible"):
                    item_status = "review_required"
                item_warnings.append("Player skill levels missing: " + ", ".join(sorted(set(missing_skills), key=str.casefold)))
            else:
                reasons.append("Meets all skill requirements recorded in the generated database")

        if not row.get("source_urls"):
            item_warnings.append("No source URL retained on the joined database record")
        if row.get("weapon_record_present") is True and db_slot not in (None, "weapon"):
            item_warnings.append("Weapon record is present but the database slot is not 'weapon'; review source mapping")

        cost_value = None
        if costs is not None:
            raw_cost = costs.get(str(item_id), costs.get(item_id))
            if isinstance(raw_cost, int) and not isinstance(raw_cost, bool) and raw_cost >= 0:
                cost_value = raw_cost
                total_cost += raw_cost
                known_cost_count += 1
            else:
                item_warnings.append("Cost is unknown; no live price lookup is performed")
        results.append({
            "item_id": item_id, "name": name, "requested_slot": requested_slot,
            "database_slot": db_slot, "status": item_status, "cost_gp": cost_value,
            "skill_requirements": row.get("skill_requirements"),
            "source_urls": row.get("source_urls") if isinstance(row.get("source_urls"), list) else [],
            "reasons": reasons, "warnings": item_warnings,
        })
        for warning in item_warnings:
            warnings.append({"item_id": item_id, "message": warning})

    if budget is not None and costs is not None:
        if known_cost_count != len(results):
            warnings.append({"code": "budget_incomplete", "message": "Budget cannot be confirmed because one or more selected item costs are unknown"})
        elif total_cost > budget:
            errors.append({"code": "budget_overrun", "total_cost_gp": total_cost, "budget_gp": budget,
                           "message": "Selected item costs exceed the supplied budget"})

    fatal_codes = {"invalid_selection_entry", "invalid_item_id", "duplicate_item_id", "duplicate_slot",
                   "item_not_found", "invalid_requested_slot", "slot_mismatch", "budget_overrun"}
    failed = any(error.get("code") in fatal_codes for error in errors)
    has_unknown = bool(warnings) or any(row.get("status") == "review_required" for row in results)
    has_ineligible = any(row.get("status") in ("excluded", "incompatible", "ineligible_by_known_skill_requirement") for row in results)
    status = "failed" if failed else ("review_required" if has_unknown or has_ineligible else "passed_known_checks")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "dataset": DATASET,
        "selection_count": len(raw_items),
        "results": results,
        "summary": {
            "passed_known_checks": sum(r.get("status") == "meets_known_checks" for r in results),
            "review_required": sum(r.get("status") == "review_required" for r in results),
            "ineligible_or_excluded": sum(r.get("status") in ("excluded", "incompatible", "ineligible_by_known_skill_requirement") for r in results),
            "known_cost_count": known_cost_count,
            "total_cost_gp": total_cost if costs is not None else None,
            "budget_gp": budget,
            "error_count": len(errors),
            "warning_count": len(warnings) + len(profile_warnings),
        },
        "errors": errors,
        "warnings": warnings,
        "profile_warnings": profile_warnings,
        "guardrails": [
            "All item facts are read from the generated item-combat-profiles dataset; this tool makes no network requests.",
            "Missing requirements, sources, slots, costs, and skill levels remain unknown rather than being inferred.",
            "Passing means only the selected structural and known skill checks passed; quest, unlock, variant and special restrictions may remain unknown.",
            "Cost data is caller-supplied; no live Grand Exchange prices are fetched.",
            "This report is not a DPS calculation or a claim of complete equipment eligibility.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, required=True, help="JSON selection array or object with an items array")
    parser.add_argument("--profile", type=Path, required=True, help="Player profile JSON")
    parser.add_argument("--dist-dir", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--costs", type=Path, help="Optional caller-supplied JSON item-ID-to-GP map")
    parser.add_argument("--budget", type=int, help="Optional budget in GP; requires --costs to confirm")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORTS / "loadout-compatibility.json")
    args = parser.parse_args()
    try:
        profiles = index_profiles(read_json(args.dist_dir / DATASET))
        selected = read_json(args.selected)
        profile = read_json(args.profile)
        costs = read_json(args.costs) if args.costs else None
        report = evaluate_loadout(selected, profiles, profile, costs, args.budget)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
