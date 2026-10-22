#!/usr/bin/env python3
"""Audit the normalized Combat Studio join contract without inventing missing facts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

DATASETS = {
    "items": ("items.json", "id"),
    "equipment": ("equipment-stats.json", "id"),
    "weapons": ("weapons.json", "id"),
    "requirements": ("item-requirements.json", "item_id"),
    "profiles": ("item-combat-profiles.json", "id"),
    "monsters": ("monsters-combat.json", "id"),
}
BONUS_FIELDS = (
    "attack_stab", "attack_slash", "attack_crush", "attack_magic", "attack_ranged",
    "defence_stab", "defence_slash", "defence_crush", "defence_magic", "defence_ranged",
    "melee_strength", "ranged_strength", "magic_damage", "prayer",
)
MONSTER_FIELDS = (
    "combat_level", "hitpoints", "attack_level", "strength_level", "defence_level",
    "magic_level", "ranged_level", "attack_speed", "max_hit", "slayer_level", "size",
)


def load_rows(directory: Path, filename: str):
    try:
        rows = json.loads((directory / filename).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {filename}: {exc}") from exc
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{filename} must be a JSON array of objects")
    return rows


def index_rows(rows, filename, id_field, errors):
    indexed = {}
    for index, row in enumerate(rows):
        rid = row.get(id_field)
        if isinstance(rid, bool) or not isinstance(rid, int) or rid < 0:
            errors.append({"dataset": filename, "index": index, "issue": "invalid_id", "value": rid})
            continue
        if rid in indexed:
            errors.append({"dataset": filename, "index": index, "issue": "duplicate_id", "value": rid})
            continue
        indexed[rid] = row
    return indexed


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def audit_datasets(datasets):
    """Return structural errors separately from honest-but-incomplete source coverage."""
    errors, warnings = [], []
    missing = [filename for filename, _ in DATASETS.values() if filename not in datasets]
    if missing:
        return {
            "status": "failed",
            "errors": [{"issue": "missing_dataset", "dataset": name} for name in missing],
            "warnings": [],
            "summary": {},
        }

    indexed = {}
    for key, (filename, id_field) in DATASETS.items():
        indexed[key] = index_rows(datasets[filename], filename, id_field, errors)

    item_ids = set(indexed["items"])
    equipment_ids = set(indexed["equipment"])
    weapon_ids = set(indexed["weapons"])
    requirement_ids = set(indexed["requirements"])
    profile_ids = set(indexed["profiles"])
    monster_ids = set(indexed["monsters"])

    for key, target_ids in (("equipment", item_ids), ("weapons", item_ids), ("requirements", item_ids), ("profiles", item_ids)):
        for rid in sorted(set(indexed[key]) - target_ids)[:100]:
            errors.append({"dataset": DATASETS[key][0], "issue": "orphan_item_reference", "item_id": rid})

    profile_flag_mismatches = 0
    for rid, row in indexed["profiles"].items():
        expected = {
            "equipment_record_present": rid in equipment_ids,
            "weapon_record_present": rid in weapon_ids,
            "skill_requirement_record_present": rid in requirement_ids,
        }
        for field, expected_value in expected.items():
            if row.get(field) is not expected_value:
                profile_flag_mismatches += 1
                errors.append({"dataset": "item-combat-profiles.json", "item_id": rid,
                               "issue": "join_flag_mismatch", "field": field,
                               "expected": expected_value, "actual": row.get(field)})

        bonuses = row.get("bonuses")
        if not isinstance(bonuses, dict):
            errors.append({"dataset": "item-combat-profiles.json", "item_id": rid, "issue": "bonuses_not_object"})
        else:
            for field, value in bonuses.items():
                if value is not None and not is_number(value):
                    errors.append({"dataset": "item-combat-profiles.json", "item_id": rid,
                                   "issue": "non_numeric_bonus", "field": field, "value": value})
        if not isinstance(row.get("source_urls"), list):
            errors.append({"dataset": "item-combat-profiles.json", "item_id": rid, "issue": "source_urls_not_array"})

    malformed_stances = []
    for rid, row in indexed["weapons"].items():
        speed = row.get("attack_speed")
        if speed is not None and (isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0):
            errors.append({"dataset": "weapons.json", "item_id": rid, "issue": "invalid_attack_speed", "value": speed})
        stances = row.get("stances")
        if not isinstance(stances, list):
            errors.append({"dataset": "weapons.json", "item_id": rid, "issue": "stances_not_array"})
        else:
            for stance_index, stance in enumerate(stances):
                if not isinstance(stance, dict) or not isinstance(stance.get("name"), str) or not stance["name"].strip():
                    malformed_stances.append({"item_id": rid, "stance_index": stance_index})
    if malformed_stances:
        errors.append({"dataset": "weapons.json", "issue": "stance_name_missing",
                       "count": len(malformed_stances), "examples": malformed_stances[:20]})

    invalid_monster_values = []
    for rid, row in indexed["monsters"].items():
        for field in MONSTER_FIELDS:
            value = row.get(field)
            if value is not None and (not is_number(value) or value < 0):
                invalid_monster_values.append({"monster_id": rid, "field": field, "value": value})
    if invalid_monster_values:
        errors.append({"dataset": "monsters-combat.json", "issue": "invalid_combat_value",
                       "count": len(invalid_monster_values), "examples": invalid_monster_values[:30]})

    # Coverage gaps are actionable warnings, never interpreted as zero/no requirement.
    gaps = {
        "items_without_combat_profile": sorted(item_ids - profile_ids),
        "equipment_without_requirement_record": sorted(equipment_ids - requirement_ids),
        "weapons_without_source_url": sorted(rid for rid, row in indexed["weapons"].items()
                                             if not isinstance(row.get("source_url"), str) or not row["source_url"]),
        "weapons_without_attack_speed": sorted(rid for rid, row in indexed["weapons"].items()
                                               if row.get("attack_speed") is None),
        "weapons_without_stances": sorted(rid for rid, row in indexed["weapons"].items()
                                          if not row.get("stances")),
        "monsters_without_core_combat_fields": sorted(
            rid for rid, row in indexed["monsters"].items()
            if any(row.get(field) is None for field in ("combat_level", "hitpoints", "defence_level"))
        ),
    }
    for name, ids in gaps.items():
        if ids:
            warnings.append({"issue": "coverage_gap", "area": name, "count": len(ids), "sample_ids": ids[:25],
                             "meaning": "Missing data is unknown; it does not imply zero or no requirement."})

    summary = {
        "item_count": len(item_ids),
        "equipment_count": len(equipment_ids),
        "weapon_count": len(weapon_ids),
        "requirement_count": len(requirement_ids),
        "combat_profile_count": len(profile_ids),
        "monster_count": len(monster_ids),
        "profile_join_flag_mismatches": profile_flag_mismatches,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }
    return {
        "status": "failed" if errors else "passed_with_gaps" if warnings else "passed",
        "summary": summary,
        "coverage_gaps": gaps,
        "errors": errors[:250],
        "warnings": warnings,
        "guardrails": [
            "Join keys are exact numeric IDs; names are never used as fallback join keys.",
            "Null and absent values remain unknown and are not coerced to zero.",
            "A present field or passing structural audit is not proof of factual accuracy.",
            "This report validates data structure and joins, not DPS formulas or loadout legality.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(REPORTS / "combat-join-contract.json"))
    args = parser.parse_args()
    try:
        datasets = {filename: load_rows(DIST, filename) for filename, _ in DATASETS.values()}
        report = audit_datasets(datasets)
    except ValueError as exc:
        report = {"status": "failed", "summary": {}, "coverage_gaps": {},
                  "errors": [{"issue": "input_error", "message": str(exc)}], "warnings": []}
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
