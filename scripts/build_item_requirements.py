#!/usr/bin/env python3
"""Normalize item skill requirements while distinguishing empty from unknown source fields."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def normalize_requirements(items):
    if not isinstance(items, list):
        raise ValueError("items dataset must be a JSON array")
    records = []
    warnings = []
    seen_ids = set()
    skills = Counter()
    equipment_count = 0
    unknown_count = 0
    known_empty_count = 0
    partial_count = 0

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            warnings.append({"index": index, "reason": "record_not_object"})
            continue
        item_id = item.get("id")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
            warnings.append({"index": index, "reason": "invalid_item_id", "id": item_id})
            continue
        if item_id in seen_ids:
            raise ValueError(f"duplicate item ID {item_id}")
        seen_ids.add(item_id)

        equipment = item.get("equipment")
        if not isinstance(equipment, dict) or not equipment:
            continue
        equipment_count += 1

        # Missing/malformed requirements are unknown. An explicit empty object is
        # meaningful source evidence and must not disappear from the dataset.
        if "requirements" not in equipment or not isinstance(equipment["requirements"], dict):
            unknown_count += 1
            continue

        raw = equipment["requirements"]
        normalized = []
        invalid_entries = []
        normalized_pairs = sorted(
            raw.items(),
            key=lambda pair: " ".join(pair[0].split()).casefold() if isinstance(pair[0], str) else str(pair[0]).casefold(),
        )
        for skill, level in normalized_pairs:
            if not isinstance(skill, str) or not skill.strip():
                invalid_entries.append({"skill": skill, "value": level, "reason": "invalid_skill_name"})
                continue
            if isinstance(level, bool) or not isinstance(level, (int, float)) or int(level) != level or level < 0:
                invalid_entries.append({"skill": skill, "value": level, "reason": "invalid_skill_level"})
                continue
            normalized.append({"skill": " ".join(skill.split()), "level": int(level)})
            skills[skill.casefold()] += 1

        if invalid_entries:
            warnings.extend({"item_id": item_id, **entry} for entry in invalid_entries)
            status = "partial"
            partial_count += 1
        elif not normalized:
            status = "known_empty"
            known_empty_count += 1
        else:
            status = "known"

        records.append({
            "item_id": item_id,
            "item_name": item.get("name") if isinstance(item.get("name"), str) else "",
            "requirements": normalized,
            "requirements_status": status,
            "sources": sorted({x for x in item.get("sources", []) if isinstance(x, str)}) if isinstance(item.get("sources"), list) else [],
            "source_url": item.get("wiki_url") if isinstance(item.get("wiki_url"), str) else None,
        })

    records.sort(key=lambda row: row["item_id"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_warnings" if warnings else "passed",
        "source_item_count": len(items),
        "equipment_item_count": equipment_count,
        "items_with_requirement_field": len(records),
        "items_with_nonempty_skill_requirements": sum(row["requirements_status"] == "known" for row in records),
        "items_with_skill_requirements": sum(row["requirements_status"] == "known" for row in records),
        "items_with_explicit_empty_requirements": known_empty_count,
        "items_with_partially_invalid_requirements": partial_count,
        "items_with_unknown_requirements": unknown_count,
        "requirement_field_coverage_percent": round(100.0 * len(records) / equipment_count, 2) if equipment_count else 0.0,
        "requirement_entry_count": sum(len(row["requirements"]) for row in records),
        "skill_counts": dict(sorted(skills.items())),
        "warning_count": len(warnings),
        "warnings": warnings[:100],
        "note": "Known-empty means the source explicitly supplied an empty requirements object. Missing or malformed source fields remain unknown; structural coverage does not independently verify factual accuracy.",
    }
    return records, report


def main():
    try:
        items = json.loads((DIST / "items.json").read_text(encoding="utf-8"))
        records, report = normalize_requirements(items)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        records = []
        report = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "failed", "errors": [str(exc)]}
    DIST.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (DIST / "item-requirements.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (REPORTS / "item-requirements-coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
