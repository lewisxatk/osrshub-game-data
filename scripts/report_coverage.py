#!/usr/bin/env python3
"""Produce field-presence coverage reports without assuming source fields are universal."""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "items": ("dist/items.json", ("members", "tradeable", "stackable", "equipable", "equipment", "weapon", "ge", "examine")),
    "equipment": ("dist/equipment.json", ("equipment", "weapon", "equipable", "equipable_by_player", "attack_speed")),
    "monsters": ("dist/monsters.json", ("combat_level", "hitpoints", "attack_level", "strength_level", "defence_level", "magic_level", "ranged_level", "max_hit", "attack_speed", "drops", "slayer_level")),
}
def main():
    reports = ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "meaning": "Field presence is descriptive coverage, not a correctness or completeness guarantee.",
              "datasets": {}, "errors": []}
    for dataset, (relative_path, fields) in DATASETS.items():
        path = ROOT / relative_path
        if not path.exists():
            report["errors"].append(f"Missing {relative_path}")
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report["errors"].append(f"Cannot read {relative_path}: {exc}")
            continue
        if not isinstance(rows, list):
            report["errors"].append(f"{relative_path} must be an array")
            continue
        field_counts = Counter()
        for row in rows:
            if not isinstance(row, dict):
                continue
            for field in fields:
                value = row.get(field)
                if value is not None and value != "" and value != [] and value != {}:
                    field_counts[field] += 1
        total = len(rows)
        report["datasets"][dataset] = {
            "record_count": total,
            "fields": {field: {"records_with_value": field_counts[field],
                               "coverage_percent": round(field_counts[field] * 100 / total, 2) if total else 0.0}
                       for field in fields}
        }
    report["status"] = "failed" if report["errors"] else "passed"
    (reports / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0
if __name__ == "__main__":
    raise SystemExit(main())
