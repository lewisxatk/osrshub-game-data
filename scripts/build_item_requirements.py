#!/usr/bin/env python3
"""Normalize item skill requirements into explicit, auditable item records."""
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
        raw = equipment.get("requirements") if isinstance(equipment, dict) else None
        if not isinstance(raw, dict) or not raw:
            continue
        normalized = []
        for skill, level in sorted(raw.items(), key=lambda pair: str(pair[0]).casefold()):
            if not isinstance(skill, str) or not skill.strip():
                warnings.append({"item_id": item_id, "reason": "invalid_skill_name"})
                continue
            if isinstance(level, bool) or not isinstance(level, (int, float)) or int(level) != level or level < 0:
                warnings.append({"item_id": item_id, "skill": skill, "reason": "invalid_skill_level", "value": level})
                continue
            normalized.append({"skill": " ".join(skill.split()), "level": int(level)})
            skills[skill.casefold()] += 1
        if normalized:
            records.append({
                "item_id": item_id,
                "item_name": item.get("name") if isinstance(item.get("name"), str) else "",
                "requirements": normalized,
                "sources": sorted({x for x in item.get("sources", []) if isinstance(x, str)}) if isinstance(item.get("sources"), list) else [],
                "source_url": item.get("wiki_url") if isinstance(item.get("wiki_url"), str) else None,
            })
    records.sort(key=lambda row: row["item_id"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_warnings" if warnings else "passed",
        "source_item_count": len(items),
        "items_with_skill_requirements": len(records),
        "requirement_entry_count": sum(len(row["requirements"]) for row in records),
        "skill_counts": dict(sorted(skills.items())),
        "warning_count": len(warnings),
        "warnings": warnings[:100],
        "note": "Requirements are copied from source equipment metadata; this output does not infer quest unlocks or claim every item requirement is present.",
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
