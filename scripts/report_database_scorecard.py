#!/usr/bin/env python3
"""Create a repeatable scorecard for generated OSRS Hub database coverage.

Percentages describe the presence of explicitly selected fields only. They are not
an accuracy score, and the aggregate is a defined coverage index, not proof of
complete OSRS knowledge.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

# Each dataset has its own applicability denominator. Do not mix unrelated fields
# across every item/NPC record into a misleading single completeness percentage.
SPECS = {
    "items": ("items.json", ("id", "name", "members", "tradeable", "stackable")),
    "equipment": ("equipment-stats.json", ("id", "name", "slot", "bonuses", "requirements", "source_url")),
    "weapons": ("weapons.json", ("id", "name", "attack_speed", "weapon_type", "stances", "source_url")),
    "monsters_combat": ("monsters-combat.json", ("id", "name", "combat_level", "hitpoints", "attack_level", "strength_level", "defence_level", "source_url")),
    "item_requirements": ("item-requirements.json", ("id", "name", "requirements", "source_urls")),
    "quests": ("quests.json", ("id", "name", "source_urls")),
    "quest_relationships": ("quest-relationships.json", ("quest_id", "prerequisite_quest_ids", "source_urls")),
}
PROFILE_FIELDS = ("equipment_record_present", "weapon_record_present", "skill_requirement_record_present", "attack_speed", "source_urls")

def present(value):
    return value is not None and value != "" and value != [] and value != {}

def load_array(filename):
    path = DIST / filename
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read dist/{filename}: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"dist/{filename} must be an array of objects")
    return data

def coverage(rows, fields):
    total = len(rows)
    field_results = {}
    observed = 0
    opportunities = total * len(fields)
    for field in fields:
        count = sum(1 for row in rows if present(row.get(field)))
        observed += count
        field_results[field] = {"present_records": count, "missing_records": total - count,
                                "coverage_percent": round(100 * count / total, 2) if total else 0.0}
    return {"record_count": total, "field_count": len(fields),
            "field_presence_opportunities": opportunities, "field_presence_count": observed,
            "field_coverage_percent": round(100 * observed / opportunities, 2) if opportunities else 0.0,
            "fields": field_results}

def build_scorecard(loader=load_array):
    datasets, errors = {}, []
    for name, (filename, fields) in SPECS.items():
        try:
            datasets[name] = {"path": f"dist/{filename}", **coverage(loader(filename), fields)}
        except ValueError as exc:
            errors.append(str(exc))
    try:
        profiles = loader("item-combat-profiles.json")
        summary = coverage(profiles, PROFILE_FIELDS)
        summary["path"] = "dist/item-combat-profiles.json"
        summary["equipment_link_and_source_percent"] = round(100 * sum(
            bool(row.get("equipment_record_present")) and bool(row.get("source_urls")) for row in profiles
        ) / len(profiles), 2) if profiles else 0.0
        summary["weapon_link_and_speed_percent"] = round(100 * sum(
            bool(row.get("weapon_record_present")) and present(row.get("attack_speed")) for row in profiles
        ) / len(profiles), 2) if profiles else 0.0
        datasets["item_combat_profiles"] = summary
    except ValueError as exc:
        errors.append(str(exc))
    # Give each configured dataset equal weight, including empty datasets. This makes
    # a missing quest catalogue visible instead of letting it vanish from the denominator.
    dataset_coverages = [v["field_coverage_percent"] for v in datasets.values()]
    coverage_index = round(sum(dataset_coverages) / len(dataset_coverages), 2) if dataset_coverages else 0.0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "passed",
        "coverage_index_percent": coverage_index,
        "coverage_index_definition": "Arithmetic mean of each successfully loaded configured dataset field-coverage percentage. Empty datasets contribute 0%; this is a tracking index, not overall OSRS database completeness or factual accuracy.",
        "dataset_count": len(datasets),
        "total_records_across_datasets": sum(v["record_count"] for v in datasets.values()),
        "datasets": datasets,
        "errors": errors,
        "guardrails": [
            "A present field is not proof that its value is factually correct.",
            "Zero is present; null, empty strings, empty arrays and empty objects are treated as missing.",
            "Applicability differs by dataset; item-combat profiles have separate readiness indicators.",
            "An empty quest dataset scores zero field presence and is not treated as complete.",
            "Live Grand Exchange prices are outside this scorecard."
        ],
    }

def main():
    report = build_scorecard()
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "database-scorecard.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0

if __name__ == "__main__":
    raise SystemExit(main())
