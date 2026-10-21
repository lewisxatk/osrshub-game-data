#!/usr/bin/env python3
"""Audit equipment and weapon metadata gaps to guide source-adapter work."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "dist" / "items.json"
EQUIPMENT = ROOT / "dist" / "equipment.json"
REPORTS = ROOT / "reports"
BONUS_FIELDS = (
    "attack_stab", "attack_slash", "attack_crush", "attack_magic", "attack_ranged",
    "defence_stab", "defence_slash", "defence_crush", "defence_magic", "defence_ranged",
    "melee_strength", "ranged_strength", "magic_damage", "prayer",
)
MAX_EXAMPLES = 30


def nonempty(value):
    return value is not None and value != "" and value != [] and value != {}


def sample(row, reason):
    return {"id": row.get("id"), "name": row.get("name", ""), "reason": reason,
            "sources": row.get("sources", [])}


def main():
    errors = []
    try:
        items = json.loads(ITEMS.read_text(encoding="utf-8"))
        equipment = json.loads(EQUIPMENT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Unable to read generated item/equipment JSON: {exc}")
        items, equipment = [], []
    if not isinstance(items, list):
        errors.append("dist/items.json must be an array")
        items = []
    if not isinstance(equipment, list):
        errors.append("dist/equipment.json must be an array")
        equipment = []

    counts = Counter()
    examples = {
        "equipment_missing_bonus_object": [],
        "equipment_bonus_object_missing_fields": [],
        "weapon_missing_metadata": [],
        "weapon_missing_attack_speed": [],
    }
    equipment_bonus_fields = Counter()
    weapon_types = Counter()
    weapon_stances = Counter()

    for row in equipment:
        if not isinstance(row, dict):
            continue
        counts["equipment_records"] += 1
        bonus = row.get("equipment")
        if not isinstance(bonus, dict) or not bonus:
            counts["equipment_missing_bonus_object"] += 1
            if len(examples["equipment_missing_bonus_object"]) < MAX_EXAMPLES:
                examples["equipment_missing_bonus_object"].append(sample(row, "No non-empty equipment bonus object"))
            continue
        missing_fields = [field for field in BONUS_FIELDS if field not in bonus or bonus[field] is None]
        for field in BONUS_FIELDS:
            if field in bonus and bonus[field] is not None:
                equipment_bonus_fields[field] += 1
        if missing_fields:
            counts["equipment_bonus_object_missing_one_or_more_bonus_fields"] += 1
            if len(examples["equipment_bonus_object_missing_fields"]) < MAX_EXAMPLES:
                examples["equipment_bonus_object_missing_fields"].append(
                    sample(row, "Missing bonus keys: " + ", ".join(missing_fields))
                )

    for row in items:
        if not isinstance(row, dict):
            continue
        weapon = row.get("weapon")
        # Only classify as a weapon when a weapon object exists or item has an explicit
        # weapon type; do not infer weaponhood from an item name.
        explicit_weapon = isinstance(weapon, dict) or nonempty(row.get("weapon_type"))
        if not explicit_weapon:
            continue
        counts["records_with_weapon_metadata"] += 1
        if not isinstance(weapon, dict) or not weapon:
            counts["weapon_metadata_missing_or_not_object"] += 1
            if len(examples["weapon_missing_metadata"]) < MAX_EXAMPLES:
                examples["weapon_missing_metadata"].append(sample(row, "Explicit weapon marker but no weapon object"))
            continue
        if not nonempty(weapon.get("attack_speed")):
            counts["weapon_missing_attack_speed"] += 1
            if len(examples["weapon_missing_attack_speed"]) < MAX_EXAMPLES:
                examples["weapon_missing_attack_speed"].append(sample(row, "Weapon object has no attack_speed"))
        if nonempty(weapon.get("weapon_type")):
            weapon_types[str(weapon["weapon_type"])] += 1
        stances = weapon.get("stances")
        if isinstance(stances, list) and stances:
            counts["weapons_with_stances"] += 1
            for stance in stances:
                if isinstance(stance, dict) and nonempty(stance.get("attack_type")):
                    weapon_stances[str(stance["attack_type"])] += 1
        else:
            counts["weapons_without_stances"] += 1

    counts["item_records"] = len(items)
    counts["equipment_bonus_field_presence"] = dict(sorted(equipment_bonus_fields.items()))
    counts["weapon_types"] = dict(weapon_types.most_common())
    counts["stance_attack_types"] = dict(weapon_stances.most_common())
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed",
        "meaning": (
            "This report measures field presence in imported records. It does not assert that values "
            "are accurate, that every item should be equipable, or that missing fields can safely be inferred."
        ),
        "counts": dict(counts),
        "examples_capped_at": MAX_EXAMPLES,
        "examples": examples,
        "errors": errors,
        "next_actions": [
            "Review missing equipment bonus objects against an authoritative source before filling values.",
            "Prioritize weapon records missing attack speed or stances for source mapping.",
            "Keep unknown values explicitly unknown; do not infer combat stats from item names.",
        ],
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "equipment-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
