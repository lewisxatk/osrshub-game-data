#!/usr/bin/env python3
"""Evaluate item restrictions conservatively for a player profile.

This is a decision-support report, not a complete equipment eligibility oracle.
It fails closed: missing skill data, unknown quest requirements, or incomplete
profile data never become an "eligible" result.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def canonical(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def normalize_skill_map(value):
    if not isinstance(value, dict):
        return {}, ["Player skill levels are missing or malformed"]
    levels = {}
    warnings = []
    for skill, level in value.items():
        key = canonical(skill)
        if not key:
            warnings.append("Ignored a blank skill name")
            continue
        if isinstance(level, bool) or not isinstance(level, int) or level < 1:
            warnings.append(f"Invalid level for skill {skill!r}")
            continue
        levels[key] = level
    return levels, warnings


def evaluate_items(items, requirements, profile):
    if not isinstance(items, list):
        raise ValueError("items must be a JSON array")
    if not isinstance(requirements, list):
        raise ValueError("item requirements must be a JSON array")
    if not isinstance(profile, dict):
        raise ValueError("profile must be a JSON object")

    skill_levels, profile_warnings = normalize_skill_map(profile.get("skills"))
    excluded_ids = set()
    raw_excluded_ids = profile.get("excluded_item_ids", [])
    if not isinstance(raw_excluded_ids, list):
        profile_warnings.append("excluded_item_ids must be an array; ignored")
        raw_excluded_ids = []
    for value in raw_excluded_ids:
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            excluded_ids.add(value)
        else:
            profile_warnings.append(f"Ignored invalid excluded item ID: {value!r}")
    raw_excluded_names = profile.get("excluded_item_names", [])
    if not isinstance(raw_excluded_names, list):
        profile_warnings.append("excluded_item_names must be an array; ignored")
        raw_excluded_names = []
    excluded_names = set()
    for value in raw_excluded_names:
        if isinstance(value, str) and canonical(value):
            excluded_names.add(canonical(value))
        else:
            profile_warnings.append(f"Ignored invalid excluded item name: {value!r}")
    raw_completed_quests = profile.get("completed_quests", [])
    if not isinstance(raw_completed_quests, list):
        profile_warnings.append("completed_quests must be an array; ignored")
        raw_completed_quests = []
    completed_quests = set()
    for value in raw_completed_quests:
        if isinstance(value, str) and canonical(value):
            completed_quests.add(canonical(value))
        else:
            profile_warnings.append(f"Ignored invalid completed quest entry: {value!r}")
    requirement_by_id = {}
    for row in requirements:
        if not isinstance(row, dict):
            continue
        item_id = row.get("item_id")
        if isinstance(item_id, int) and not isinstance(item_id, bool):
            requirement_by_id.setdefault(item_id, []).append(row)

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id, name = item.get("id"), item.get("name", "")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0 or not isinstance(name, str):
            continue
        reasons = []
        skill_status = "unknown"
        matched = requirement_by_id.get(item_id, [])
        if item_id in excluded_ids or canonical(name) in excluded_names:
            overall = "excluded"
            reasons.append("Manually excluded by the player")
        else:
            missing_levels = []
            unmet = []
            invalid_requirements = []
            normalized = []
            for source_row in matched:
                raw_reqs = source_row.get("requirements")
                if not isinstance(raw_reqs, list):
                    invalid_requirements.append("Requirement record is malformed")
                    continue
                for req in raw_reqs:
                    if not isinstance(req, dict) or not isinstance(req.get("skill"), str):
                        invalid_requirements.append("Requirement entry is malformed")
                        continue
                    level = req.get("level")
                    if isinstance(level, bool) or not isinstance(level, int) or level < 0:
                        invalid_requirements.append(f"Invalid requirement level for {req.get('skill')}")
                        continue
                    normalized.append((canonical(req["skill"]), req["skill"], level))
            if invalid_requirements:
                skill_status = "unknown"
                reasons.extend(invalid_requirements)
            elif not matched:
                reasons.append("No normalized skill requirement record exists for this item")
            else:
                for key, label, level in normalized:
                    if key not in skill_levels:
                        missing_levels.append(label)
                    elif skill_levels[key] < level:
                        unmet.append({"skill": label, "required": level, "player": skill_levels[key]})
                if unmet:
                    skill_status = "ineligible"
                    reasons.extend([f"Requires {x['skill']} {x['required']} (player has {x['player']})" for x in unmet])
                elif missing_levels:
                    skill_status = "unknown"
                    reasons.append("Player profile is missing skill levels: " + ", ".join(sorted(set(missing_levels), key=str.casefold)))
                else:
                    skill_status = "meets_known_skill_requirements"
                    reasons.append("Player meets every skill requirement present in the normalized source")

            if skill_status == "ineligible":
                overall = "ineligible_by_known_skill_requirement"
            else:
                overall = "unknown"
                reasons.append("Quest, unlock, item-variant, and requirement-completeness checks are not fully verified")
        results.append({
            "item_id": item_id,
            "item_name": name,
            "skill_status": skill_status,
            "overall_status": overall,
            "matched_requirement_record_count": len(matched),
            "requirement_sources": sorted({
                source
                for row in matched
                for source in (row.get("sources", []) if isinstance(row.get("sources"), list) else [])
                if isinstance(source, str) and source.strip()
            }, key=str.casefold),
            "requirement_source_urls": sorted({
                row["source_url"] for row in matched
                if isinstance(row.get("source_url"), str) and row["source_url"].startswith("https://")
            }),
            "reasons": reasons,
            "manual_exclusion": item_id in excluded_ids or canonical(name) in excluded_names,
        })
    results.sort(key=lambda row: (row["overall_status"] != "excluded", row["overall_status"] != "ineligible_by_known_skill_requirement", row["item_name"].casefold(), row["item_id"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_warnings",
        "profile_label": profile.get("label") if isinstance(profile.get("label"), str) else None,
        "item_count_evaluated": len(results),
        "counts": {
            status: sum(row["overall_status"] == status for row in results)
            for status in ("excluded", "ineligible_by_known_skill_requirement", "unknown")
        },
        "profile_warnings": profile_warnings,
        "completed_quest_names_received": len(completed_quests),
        "completed_quests_used_for_unlock_decisions": False,
        "results": results,
        "safety_note": "No item is marked fully eligible by this report. Known skill failures and manual exclusions are actionable, but absent requirement records and unmodelled quest/unlock restrictions remain unknown.",
    }


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="JSON file containing skills and optional manual exclusions")
    parser.add_argument("--items", default=str(DIST / "equipment-stats.json"))
    parser.add_argument("--requirements", default=str(DIST / "item-requirements.json"))
    parser.add_argument("--output", default=str(REPORTS / "item-eligibility.json"))
    args = parser.parse_args()
    try:
        items = read_json(args.items)
        requirements = read_json(args.requirements)
        profile = read_json(args.profile)
        result = evaluate_items(items, requirements, profile)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, indent=2))
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "results"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
