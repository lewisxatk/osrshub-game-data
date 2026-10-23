#!/usr/bin/env python3
"""Create a unified, source-conscious readiness matrix for OSRS Hub datasets.

This is a structural readiness report, not a claim that present fields are correct.
Missing facts remain gaps; they are never converted to zero or interpreted as false.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

# Keep this matrix deliberately small and actionable. Each field is a named
# opportunity, not a claim that these fields are sufficient for the whole game.
CONTRACTS = {
    "items": {"file": "items.json", "id": "id", "fields": ["id", "name", "wiki_url"]},
    "equipment": {"file": "equipment-stats.json", "id": "id", "fields": ["id", "name", "slot", "bonuses"]},
    "weapons": {"file": "weapons.json", "id": "id", "fields": ["id", "name", "attack_speed", "weapon_type", "stances"]},
    "item_requirements": {"file": "item-requirements.json", "id": "item_id", "fields": ["item_id", "requirements", "requirements_status", "source_url"]},
    "item_combat_profiles": {"file": "item-combat-profiles.json", "id": "id", "fields": ["id", "name", "bonuses", "source_urls"]},
    "monsters_combat": {"file": "monsters-combat.json", "id": "id", "fields": ["id", "name", "combat_level", "hitpoints", "defence_level"]},
    "quests": {"file": "quests.json", "id": "id", "fields": ["id", "name", "field_status"]},
    "quest_relationships": {"file": "quest-relationships.json", "id": "quest_id", "fields": ["quest_id", "prerequisite_quest_ids"]},
    "item_relationships": {"file": "item-relationships.json", "id": "item_id", "fields": ["item_id", "relationships"]},
}

def is_present(value):
    return value is not None and value != "" and value != [] and value != {}

def load_array(filename):
    path = DIST / filename
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read dist/{filename}: {exc}") from exc
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"dist/{filename} must be an array of objects")
    return value

def _coverage(rows, fields):
    fields_out = {}
    for field in fields:
        present = sum(is_present(row.get(field)) for row in rows)
        total = len(rows)
        fields_out[field] = {
            "present_count": present,
            "missing_count": total - present,
            "coverage_percent": round(present * 100 / total, 2) if total else 0.0,
        }
    return fields_out

def build_readiness_report(loader=load_array):
    datasets, errors = {}, []
    for key, contract in CONTRACTS.items():
        try:
            rows = loader(contract["file"])
            datasets[key] = rows
        except ValueError as exc:
            errors.append(str(exc))

    summaries = {}
    for key, rows in datasets.items():
        contract = CONTRACTS[key]
        ids = [row.get(contract["id"]) for row in rows]
        valid_ids = [value for value in ids if isinstance(value, int) and not isinstance(value, bool) and value >= 0]
        duplicates = sorted(value for value, count in Counter(valid_ids).items() if count > 1)
        summaries[key] = {
            "file": contract["file"],
            "record_count": len(rows),
            "valid_id_count": len(valid_ids),
            "invalid_id_count": len(rows) - len(valid_ids),
            "duplicate_ids": duplicates[:20],
            "duplicate_id_count": len(duplicates),
            "fields": _coverage(rows, contract["fields"]),
        }

    def ids(dataset, key):
        return {row.get(key) for row in datasets.get(dataset, [])
                if isinstance(row.get(key), int) and not isinstance(row.get(key), bool)}
    equipment_ids = ids("equipment", "id")
    weapon_ids = ids("weapons", "id")
    profile_ids = ids("item_combat_profiles", "id")
    requirement_ids = ids("item_requirements", "item_id")
    item_ids = ids("items", "id")
    quest_ids = ids("quests", "id")
    quest_link_ids = ids("quest_relationships", "quest_id")
    relationship_ids = ids("item_relationships", "item_id")

    # Missing child records and orphan child records are different failures.
    joins = {
        "equipment_missing_profile_ids": sorted(equipment_ids - profile_ids)[:100],
        "equipment_missing_requirement_ids": sorted(equipment_ids - requirement_ids)[:100],
        "weapon_missing_profile_ids": sorted(weapon_ids - profile_ids)[:100],
        "item_missing_relationship_ids": sorted(item_ids - relationship_ids)[:100],
        "quest_missing_relationship_ids": sorted(quest_ids - quest_link_ids)[:100],
        "equipment_orphan_item_ids": sorted(equipment_ids - item_ids)[:100],
        "weapon_orphan_equipment_ids": sorted(weapon_ids - equipment_ids)[:100],
        "profile_orphan_item_ids": sorted(profile_ids - item_ids)[:100],
        "requirement_orphan_item_ids": sorted(requirement_ids - item_ids)[:100],
        "item_relationship_orphan_item_ids": sorted(relationship_ids - item_ids)[:100],
        "quest_relationship_orphan_quest_ids": sorted(quest_link_ids - quest_ids)[:100],
        "equipment_count": len(equipment_ids),
        "weapon_count": len(weapon_ids),
        "item_count": len(item_ids),
        "quest_count": len(quest_ids),
    }

    unknown_quest_facts = sum(
        not isinstance(row.get("field_status"), dict)
        or any(row.get("field_status", {}).get(field) != "known"
               for field in ("requirements", "skill_requirements"))
        for row in datasets.get("quests", [])
    )
    unknown_requirements = sum(
        row.get("requirements_status") in (None, "unknown", "partial")
        for row in datasets.get("item_requirements", [])
    )
    missing_weapon_mechanics = sum(
        not is_present(row.get("attack_speed"))
        or not is_present(row.get("weapon_type"))
        or not is_present(row.get("stances"))
        for row in datasets.get("weapons", [])
    )
    missing_monster_core = sum(
        any(not is_present(row.get(field)) for field in ("combat_level", "hitpoints", "defence_level"))
        for row in datasets.get("monsters_combat", [])
    )

    gaps = []
    def add_gap(key, severity, domain, count, denominator, impact, action):
        gaps.append({
            "key": key, "severity": severity, "domain": domain,
            "affected_records": int(count), "denominator": int(denominator),
            "coverage_percent": round(100 * (denominator - count) / denominator, 2) if denominator else 0.0,
            "impact": impact, "recommended_action": action,
        })

    add_gap("equipment_profile_join", "high", "equipment", len(equipment_ids - profile_ids), len(equipment_ids),
            "Equipment may be absent from the joined profile used by downstream tools.",
            "Investigate ID joins and rebuild profiles; do not change game facts to force a match.")
    add_gap("equipment_requirements", "high", "item_requirements", len(equipment_ids - requirement_ids), len(equipment_ids),
            "Eligibility is uncertain where no normalized requirement record exists.",
            "Add only source-backed requirements; missing records are not proof of no requirements.")
    add_gap("weapon_mechanics", "high", "weapons", missing_weapon_mechanics, len(datasets.get("weapons", [])),
            "Attack timing or style-aware combat features may lack required inputs.",
            "Verify missing mechanics against retained sources; never guess attack speed or stances.")
    add_gap("quest_requirement_facts", "high", "quests", unknown_quest_facts, len(datasets.get("quests", [])),
            "Quest planning cannot safely treat unknown requirements as no requirements.",
            "Import sourced prerequisite and skill facts and keep field-level known/unknown status.")
    add_gap("monster_core_combat", "medium", "monsters_combat", missing_monster_core, len(datasets.get("monsters_combat", [])),
            "Monster readiness and scoped combat calculations may lack key inputs.",
            "Verify core combat fields and retain nulls for unresolved values.")
    add_gap("item_relationship_index", "medium", "item_relationships", len(item_ids - relationship_ids), len(item_ids),
            "Items may be absent from the relationship explorer.",
            "Rebuild the index and inspect remaining IDs before adding relationships.")
    add_gap("quest_relationship_index", "medium", "quest_relationships", len(quest_ids - quest_link_ids), len(quest_ids),
            "Quest dependency coverage may be incomplete.",
            "Separate known-empty prerequisites from unavailable prerequisite facts.")
    add_gap("requirement_record_uncertainty", "medium", "item_requirements", unknown_requirements, len(datasets.get("item_requirements", [])),
            "Requirement records may be unknown or partially parsed.",
            "Resolve source evidence and validation warnings rather than assuming completeness.")

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda gap: (severity_order[gap["severity"]], -gap["affected_records"], gap["key"]))
    integrity_issues = sum(s["invalid_id_count"] + s["duplicate_id_count"] for s in summaries.values())
    status = "failed" if errors else "review_required" if integrity_issues or any(g["affected_records"] for g in gaps) else "passed"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "purpose": "Unified structural readiness and data-gap report for OSRS Hub. Field presence is not proof of factual accuracy.",
        "dataset_summaries": summaries,
        "cross_domain_joins": joins,
        "integrity_issue_count": integrity_issues,
        "gap_count": len(gaps),
        "gaps": gaps,
        "errors": errors,
        "guardrails": [
            "Missing values are unknown, not zero.",
            "A missing requirement or relationship record is not proof that none exists.",
            "Known-empty is distinct from unknown and partial.",
            "This report does not mutate source datasets or invent OSRS facts.",
            "Coverage percentages measure structural presence only, not correctness.",
            "Live Grand Exchange prices are outside this report.",
        ],
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(REPORTS / "hub-readiness-matrix.json"))
    args = parser.parse_args()
    try:
        report = build_readiness_report()
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, indent=2))
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0

if __name__ == "__main__":
    raise SystemExit(main())
