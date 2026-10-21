#!/usr/bin/env python3
"""Structural and coverage checks for generated OSRS Hub datasets."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST, REPORTS = ROOT / "dist", ROOT / "reports"
EXPECTED_ITEMS = ("Fighter torso", "Helm of Neitiznot", "Slayer helmet (i)")
IMPORTANT_ITEM_FIELDS = ("equipment", "equipable", "equipable_by_player")
IMPORTANT_MONSTER_FIELDS = ("combat_level", "hitpoints", "max_hit", "attack_speed")


def read_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_records(filename, data, errors, warnings, counts):
    if not isinstance(data, list):
        errors.append(f"{filename} must contain a JSON array")
        return
    counts[filename] = len(data)
    seen = set()
    missing_name = 0
    missing_id = 0
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            errors.append(f"{filename}[{index}] is not an object")
            continue
        record_id = row.get("id")
        if isinstance(record_id, bool) or not isinstance(record_id, int):
            missing_id += 1
            errors.append(f"{filename}[{index}] has no integer id")
        elif record_id in seen:
            errors.append(f"{filename} has duplicate id {record_id}")
        else:
            seen.add(record_id)
        if not isinstance(row.get("name"), str) or not row["name"].strip():
            missing_name += 1
            warnings.append(f"{filename}[{index}] id={record_id} has no name")
        if not isinstance(row.get("sources"), list) or not row["sources"]:
            warnings.append(f"{filename}[{index}] id={record_id} has no source attribution")

    counts[f"{filename}_missing_id_count"] = missing_id
    counts[f"{filename}_missing_name_count"] = missing_name
    if filename == "items.json":
        names = {row.get("name", "").casefold() for row in data if isinstance(row, dict)}
        for name in EXPECTED_ITEMS:
            if name.casefold() not in names:
                warnings.append(f"Expected item not found by exact name: {name}")
        counts["items_with_equipment_metadata"] = sum(
            any(field in row for field in IMPORTANT_ITEM_FIELDS)
            for row in data if isinstance(row, dict)
        )
    elif filename == "monsters.json":
        counts["monsters_with_combat_metadata"] = sum(
            any(row.get(field) is not None for field in IMPORTANT_MONSTER_FIELDS)
            for row in data if isinstance(row, dict)
        )


def main():
    errors, warnings, counts = [], [], {}
    loaded = {}
    for filename in ("items.json", "equipment.json", "monsters.json", "manifest.json"):
        path = DIST / filename
        if not path.exists():
            errors.append(f"Missing generated file: dist/{filename}")
            continue
        try:
            loaded[filename] = read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid JSON in {filename}: {exc}")

    for filename in ("items.json", "equipment.json", "monsters.json"):
        if filename in loaded:
            validate_records(filename, loaded[filename], errors, warnings, counts)

    manifest = loaded.get("manifest.json")
    if manifest is not None:
        if not isinstance(manifest, dict):
            errors.append("manifest.json must contain a JSON object")
        else:
            source_hashes = manifest.get("inputs_sha256")
            if not isinstance(source_hashes, dict) or not source_hashes:
                warnings.append("Manifest has no input source hashes")
            for label in ("items", "monsters"):
                expected = manifest.get("counts", {}).get(label)
                actual = counts.get(f"{label}.json")
                if expected is not None and actual is not None and expected != actual:
                    errors.append(f"Manifest count mismatch for {label}: expected {expected}, found {actual}")

    conflict_path = REPORTS / "source-conflicts.json"
    if conflict_path.exists():
        try:
            conflict_report = read_json(conflict_path)
            if isinstance(conflict_report, dict) and isinstance(conflict_report.get("summary"), dict):
                counts["meaningful_conflicts"] = conflict_report["summary"].get("meaningful_conflict_count", 0)
                counts["ignored_volatile_conflicts"] = conflict_report["summary"].get("ignored_volatile_conflict_count", 0)
                counts["records_missing_source_ids"] = conflict_report["summary"].get("records_missing_ids", 0)
                if counts["records_missing_source_ids"]:
                    warnings.append(f"{counts['records_missing_source_ids']} source records were skipped because IDs were missing or invalid")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid JSON in source-conflicts.json: {exc}")

    result = {
        "status": "failed" if errors else "passed_with_warnings" if warnings else "passed",
        "counts": counts,
        "errors": errors,
        "warnings": warnings,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
