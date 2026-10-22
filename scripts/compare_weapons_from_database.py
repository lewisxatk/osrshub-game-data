#!/usr/bin/env python3
"""Compare two weapon profiles from the generated OSRS Hub database only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / "dist"
DATASET = "item-combat-profiles.json"
BONUS_FIELDS = (
    "attack_stab", "attack_slash", "attack_crush", "attack_magic", "attack_ranged",
    "defence_stab", "defence_slash", "defence_crush", "defence_magic", "defence_ranged",
    "melee_strength", "ranged_strength", "magic_damage", "prayer",
)


def numeric(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    if isinstance(value, str) and value.strip():
        try:
            result = float(value.strip())
            return result if math.isfinite(result) else None
        except ValueError:
            return None
    return None


def lookup_profile(rows: Any, item_id: int) -> dict[str, Any]:
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{DATASET} must be an array of objects")
    matches = [
        row for row in rows
        if not isinstance(row.get("id"), bool) and row.get("id") == item_id
    ]
    if len(matches) > 1:
        raise ValueError(f"duplicate item ID {item_id} in {DATASET}")
    if not matches:
        raise LookupError(f"item ID {item_id} not found in {DATASET}")
    row = matches[0]
    if row.get("slot") != "weapon" and row.get("weapon_record_present") is not True:
        raise ValueError(f"item ID {item_id} is not marked as a weapon in {DATASET}")
    return row


def compare_profiles(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    bonus_differences = {}
    left_bonuses = left.get("bonuses") if isinstance(left.get("bonuses"), dict) else {}
    right_bonuses = right.get("bonuses") if isinstance(right.get("bonuses"), dict) else {}
    for field in BONUS_FIELDS:
        left_value = numeric(left_bonuses.get(field))
        right_value = numeric(right_bonuses.get(field))
        bonus_differences[field] = {
            "left_value": left_bonuses.get(field),
            "right_value": right_bonuses.get(field),
            "delta_right_minus_left": right_value - left_value
            if left_value is not None and right_value is not None else None,
            "delta_status": "calculated" if left_value is not None and right_value is not None else "unknown_input",
        }
    left_speed, right_speed = numeric(left.get("attack_speed")), numeric(right.get("attack_speed"))
    return {
        "left": {
            "id": left.get("id"), "name": left.get("name"), "slot": left.get("slot"),
            "weapon_type": left.get("weapon_type"), "attack_speed": left.get("attack_speed"),
            "skill_requirements": left.get("skill_requirements"),
            "weapon_record_present": left.get("weapon_record_present"),
            "data_status": left.get("data_status"),
        },
        "right": {
            "id": right.get("id"), "name": right.get("name"), "slot": right.get("slot"),
            "weapon_type": right.get("weapon_type"), "attack_speed": right.get("attack_speed"),
            "skill_requirements": right.get("skill_requirements"),
            "weapon_record_present": right.get("weapon_record_present"),
            "data_status": right.get("data_status"),
        },
        "bonus_differences": bonus_differences,
        "attack_speed_delta_right_minus_left": (
            right_speed - left_speed if left_speed is not None and right_speed is not None else None
        ),
        "attack_speed_delta_status": (
            "calculated" if left_speed is not None and right_speed is not None else "unknown_input"
        ),
        "interpretation": "Differences describe stored database fields only; they are not a DPS, accuracy, eligibility, or upgrade recommendation.",
        "guardrails": [
            "Both weapon records are read only from the generated item-combat-profiles dataset.",
            "No network requests are made; source URLs are not fetched.",
            "A numeric delta is emitted only when both corresponding inputs are finite numbers.",
            "Missing values remain unknown; no bonuses, requirements, prices, or combat effects are inferred.",
        ],
    }


def compare_from_database(left_id: int, right_id: int, dist_dir: Path = DEFAULT_DIST) -> dict[str, Any]:
    for item_id in (left_id, right_id):
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            raise ValueError("weapon IDs must be non-negative integers")
    path = dist_dir / DATASET
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    left = lookup_profile(rows, left_id)
    right = lookup_profile(rows, right_id)
    return {
        "status": "compared",
        "dataset": DATASET,
        "left_item_id": left_id,
        "right_item_id": right_id,
        "comparison": compare_profiles(left, right),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", type=int, required=True, help="Left weapon item ID in the generated database")
    parser.add_argument("--right", type=int, required=True, help="Right weapon item ID in the generated database")
    parser.add_argument("--dist-dir", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    try:
        result = compare_from_database(args.left, args.right, args.dist_dir)
    except (ValueError, LookupError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
