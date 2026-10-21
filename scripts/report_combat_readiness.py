#!/usr/bin/env python3
"""Summarize readiness of generated data for downstream combat features."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

EQUIPMENT_FIELDS = ("slot", "bonuses", "requirements", "source_url")
WEAPON_FIELDS = ("attack_speed", "weapon_type", "stances", "source_url")
MONSTER_FIELDS = (
    "combat_level", "hitpoints", "attack_level", "strength_level",
    "defence_level", "magic_level", "ranged_level", "attack_speed", "max_hit",
)

def present(value):
    return value is not None and value != "" and value != [] and value != {}

def field_summary(rows, fields):
    total = len(rows)
    summary = {}
    for field in fields:
        count = sum(1 for row in rows if isinstance(row, dict) and present(row.get(field)))
        summary[field] = {
            "present": count,
            "missing": total - count,
            "coverage_percent": round(100 * count / total, 2) if total else 0.0,
        }
    return summary

def load_array(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON array")
    if any(not isinstance(row, dict) for row in data):
        raise ValueError(f"{path.relative_to(ROOT)} contains non-object records")
    return data

def main():
    errors = []
    datasets = {}
    specs = {
        "equipment_stats": ("equipment-stats.json", EQUIPMENT_FIELDS),
        "weapons": ("weapons.json", WEAPON_FIELDS),
        "monsters_combat": ("monsters-combat.json", MONSTER_FIELDS),
    }
    for name, (filename, fields) in specs.items():
        try:
            rows = load_array(DIST / filename)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        datasets[name] = {
            "record_count": len(rows),
            "fields": field_summary(rows, fields),
        }
        if name == "equipment_stats":
            datasets[name]["records_with_core_fields"] = sum(
                all(present(row.get(field)) for field in ("slot", "bonuses", "requirements"))
                for row in rows
            )
        elif name == "weapons":
            datasets[name]["records_with_core_fields"] = sum(
                all(present(row.get(field)) for field in ("attack_speed", "weapon_type", "stances"))
                for row in rows
            )
        else:
            core = ("combat_level", "hitpoints", "attack_level", "strength_level", "defence_level")
            datasets[name]["records_with_core_fields"] = sum(
                all(present(row.get(field)) for field in core)
                for row in rows
            )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed",
        "purpose": "Readiness indicators for downstream feature planning; not a factual accuracy score.",
        "datasets": datasets,
        "errors": errors,
        "guardrails": [
            "Missing values remain unknown and are not inferred.",
            "Coverage measures field presence only; values still require source verification.",
            "A record with core fields is not automatically combat-ready or mechanically verified.",
        ],
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "combat-readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    raise SystemExit(main())
