#!/usr/bin/env python3
"""Report weapon-profile field coverage using only OSRS Hub's generated database."""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / "dist"
DEFAULT_OUTPUT = ROOT / "reports" / "weapon-profile-coverage.json"
DATASET = "item-combat-profiles.json"
BONUS_FIELDS = (
    "attack_stab", "attack_slash", "attack_crush", "attack_magic", "attack_ranged",
    "defence_stab", "defence_slash", "defence_crush", "defence_magic", "defence_ranged",
    "melee_strength", "ranged_strength", "magic_damage", "prayer",
)
PROFILE_FIELDS = ("name", "slot", "bonuses", "attack_speed", "weapon_type", "stances",
                  "skill_requirements", "source_urls", "sources")


def present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def finite_number(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, str) and value.strip():
        try:
            return math.isfinite(float(value.strip()))
        except ValueError:
            return False
    return False


def is_weapon(row: dict[str, Any]) -> bool:
    return row.get("slot") == "weapon" or row.get("weapon_record_present") is True


def summarize_profiles(rows: Any) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise ValueError("item-combat-profiles dataset must be a JSON array")
    errors: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append({"index": index, "issue": "record_not_object"})
            continue
        item_id = row.get("id")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            errors.append({"index": index, "issue": "invalid_item_id", "item_id": item_id})
            continue
        if item_id in seen_ids:
            errors.append({"index": index, "issue": "duplicate_item_id", "item_id": item_id})
            continue
        seen_ids.add(item_id)
        if is_weapon(row):
            profiles.append(row)

    field_coverage: dict[str, Any] = {}
    for field in PROFILE_FIELDS:
        ids = [row["id"] for row in profiles if present(row.get(field))]
        field_coverage[field] = {
            "present_count": len(ids),
            "missing_count": len(profiles) - len(ids),
            "coverage_percent": round(100 * len(ids) / len(profiles), 2) if profiles else 0.0,
            "sample_missing_ids": [row["id"] for row in profiles if not present(row.get(field))][:20],
        }

    bonus_coverage: dict[str, Any] = {}
    malformed_bonus_values = []
    for field in BONUS_FIELDS:
        present_ids = []
        for row in profiles:
            bonuses = row.get("bonuses")
            value = bonuses.get(field) if isinstance(bonuses, dict) else None
            if finite_number(value):
                present_ids.append(row["id"])
            elif present(value):
                malformed_bonus_values.append({"item_id": row["id"], "field": field, "value": value})
        bonus_coverage[field] = {
            "numeric_count": len(present_ids),
            "unknown_or_non_numeric_count": len(profiles) - len(present_ids),
            "coverage_percent": round(100 * len(present_ids) / len(profiles), 2) if profiles else 0.0,
            "sample_missing_ids": [
                row["id"] for row in profiles
                if not isinstance(row.get("bonuses"), dict) or not finite_number(row["bonuses"].get(field))
            ][:20],
        }

    invalid_speed = [
        {"item_id": row["id"], "value": row.get("attack_speed")}
        for row in profiles
        if isinstance(row.get("attack_speed"), bool)
        or not isinstance(row.get("attack_speed"), int)
        or row.get("attack_speed", 0) <= 0
    ]
    missing_requirement_record = [
        row["id"] for row in profiles if row.get("skill_requirement_record_present") is not True
    ]
    missing_source_urls = [
        row["id"] for row in profiles
        if not isinstance(row.get("source_urls"), list) or not row.get("source_urls")
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed",
        "dataset": DATASET,
        "meaning": "Coverage measures fields present in the generated database, not factual accuracy or full OSRS eligibility.",
        "counts": {
            "profile_records_total": len(rows),
            "valid_unique_profile_ids": len(seen_ids),
            "weapon_profiles": len(profiles),
            "record_errors": len(errors),
            "malformed_bonus_values": len(malformed_bonus_values),
            "invalid_attack_speed_count": len(invalid_speed),
            "missing_requirement_record_count": len(missing_requirement_record),
            "missing_source_url_count": len(missing_source_urls),
        },
        "field_coverage": field_coverage,
        "bonus_coverage": bonus_coverage,
        "quality_samples": {
            "record_errors": errors[:100],
            "malformed_bonus_values": malformed_bonus_values[:100],
            "invalid_attack_speed": invalid_speed[:100],
            "missing_requirement_record_ids": missing_requirement_record[:50],
            "missing_source_url_ids": missing_source_urls[:50],
        },
        "guardrails": [
            "All inspected values come from dist/item-combat-profiles.json.",
            "This report performs no network requests and does not alter source or generated records.",
            "A missing field is unknown; it is not replaced with zero or treated as a non-existent game mechanic.",
            "Coverage and shape checks do not independently verify OSRS factual accuracy.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path = args.dist_dir / DATASET
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        report = summarize_profiles(rows)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
