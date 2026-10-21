#!/usr/bin/env python3
"""Summarize normalized equipment slots and weapon types to expose category gaps."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def summarize(rows, field):
    if not isinstance(rows, list):
        raise ValueError(f"{field} dataset must be a JSON array")
    counts = Counter()
    missing = 0
    invalid = 0
    seen = set()
    duplicate_ids = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            invalid += 1
            continue
        rid = row.get("id")
        if isinstance(rid, bool) or not isinstance(rid, int) or rid < 0:
            invalid += 1
        elif rid in seen:
            duplicate_ids.append(rid)
        else:
            seen.add(rid)
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            missing += 1
        else:
            counts[" ".join(value.split()).casefold()] += 1
    return {
        "record_count": len(rows),
        "category_counts": dict(sorted(counts.items())),
        "missing_category_count": missing,
        "invalid_record_count": invalid,
        "duplicate_ids": sorted(set(duplicate_ids)),
    }


def main():
    try:
        equipment = json.loads((DIST / "equipment-stats.json").read_text(encoding="utf-8"))
        weapons = json.loads((DIST / "weapons.json").read_text(encoding="utf-8"))
        eq = summarize(equipment, "slot")
        wp = summarize(weapons, "weapon_type")
        errors = []
        for label, result in (("equipment", eq), ("weapons", wp)):
            if result["invalid_record_count"] or result["duplicate_ids"]:
                errors.append(f"{label} contains invalid records or duplicate IDs")
        status = "failed" if errors else "passed"
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        eq, wp, errors, status = {}, {}, [str(exc)], "failed"
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "equipment_slots": eq,
        "weapon_types": wp,
        "errors": errors,
        "note": "Counts show observed source coverage only; missing categories are not inferred and category counts do not prove mechanic accuracy.",
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "combat-category-coverage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
