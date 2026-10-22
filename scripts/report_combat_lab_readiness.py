#!/usr/bin/env python3
"""Audit cross-domain readiness for the OSRS Hub Combat Lab.

This report measures available facts, joins, provenance, and known uncertainty.
It does not claim that field presence proves game-mechanics accuracy.
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

DATASETS = {
    "items": ("items.json", ("id", "name")),
    "equipment": ("equipment-stats.json", ("id", "name", "slot", "bonuses", "requirements")),
    "weapons": ("weapons.json", ("id", "name", "attack_speed", "weapon_type", "stances")),
    "item_combat_profiles": ("item-combat-profiles.json", ("id", "name", "slot", "bonuses", "source_urls")),
    "item_requirements": ("item-requirements.json", ("item_id", "requirements", "source_url")),
    "monsters_combat": ("monsters-combat.json", ("id", "name", "combat_level", "hitpoints", "defence_level")),
    "quests": ("quests.json", ("id", "name", "field_status")),
    "quest_relationships": ("quest-relationships.json", ("quest_id", "prerequisite_quest_ids")),
}

def present(value):
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

def coverage(rows, fields):
    total = len(rows)
    by_field = {}
    for field in fields:
        count = sum(present(row.get(field)) for row in rows)
        by_field[field] = {
            "present": count,
            "missing": total - count,
            "coverage_percent": round(count * 100 / total, 2) if total else 0.0,
        }
    return {"record_count": total, "fields": by_field}

def build_report(loader=load_array):
    data, errors = {}, []
    for key, (filename, fields) in DATASETS.items():
        try:
            rows = loader(filename)
            data[key] = rows
        except ValueError as exc:
            errors.append(str(exc))
    summaries = {}
    for key, (_, fields) in DATASETS.items():
        if key in data:
            summaries[key] = coverage(data[key], fields)
    items = data.get("items", [])
    equipment = data.get("equipment", [])
    weapons = data.get("weapons", [])
    profiles = data.get("item_combat_profiles", [])
    requirements = data.get("item_requirements", [])
    monsters = data.get("monsters_combat", [])
    quests = data.get("quests", [])
    relationships = data.get("quest_relationships", [])
    equip_ids = {r.get("id") for r in equipment if isinstance(r.get("id"), int)}
    weapon_ids = {r.get("id") for r in weapons if isinstance(r.get("id"), int)}
    profile_ids = {r.get("id") for r in profiles if isinstance(r.get("id"), int)}
    req_ids = {r.get("item_id") for r in requirements if isinstance(r.get("item_id"), int)}
    quest_ids = {r.get("id") for r in quests if isinstance(r.get("id"), int)}
    relation_quest_ids = {r.get("quest_id") for r in relationships if isinstance(r.get("quest_id"), int)}
    equipment_missing_profile = [r.get("id") for r in equipment if isinstance(r.get("id"), int) and r.get("id") not in profile_ids]
    equipment_missing_requirements = [r.get("id") for r in equipment if isinstance(r.get("id"), int) and r.get("id") not in req_ids]
    weapons_missing_profiles = [r.get("id") for r in weapons if isinstance(r.get("id"), int) and r.get("id") not in profile_ids]
    quest_missing_relationships = [r.get("id") for r in quests if isinstance(r.get("id"), int) and r.get("id") not in relation_quest_ids]
    profiles_partial = [r.get("id") for r in profiles if r.get("data_status") != "joined_fields_present"]
    profiles_without_sources = [r.get("id") for r in profiles if not present(r.get("source_urls"))]
    unknown_quest_facts = [r.get("key", r.get("id")) for r in quests if isinstance(r, dict) and (
        not isinstance(r.get("field_status"), dict)
        or any(r.get("field_status", {}).get(field) != "known" for field in ("requirements", "skill_requirements"))
    )]
    weapon_missing_mechanics = [r.get("id") for r in weapons if not present(r.get("attack_speed")) or not present(r.get("weapon_type")) or not present(r.get("stances"))]
    monster_missing_core = [r.get("id") for r in monsters if any(not present(r.get(field)) for field in ("combat_level", "hitpoints", "defence_level"))]
    findings = [
        {"severity":"high","area":"equipment-to-combat-profile joins","count":len(equipment_missing_profile),"examples":equipment_missing_profile[:20],"meaning":"Equipment records with no joined item combat profile."},
        {"severity":"high","area":"equipment requirement coverage","count":len(equipment_missing_requirements),"examples":equipment_missing_requirements[:20],"meaning":"Equipment records without a normalized skill-requirement record; this does not mean no requirements exist."},
        {"severity":"high","area":"weapon mechanics","count":len(weapon_missing_mechanics),"examples":weapon_missing_mechanics[:20],"meaning":"Weapon records missing attack speed, type or stance data."},
        {"severity":"high","area":"quest facts","count":len(unknown_quest_facts),"examples":unknown_quest_facts[:20],"meaning":"Quests where prerequisite or skill requirement facts are not explicitly known."},
        {"severity":"medium","area":"quest relationship coverage","count":len(quest_missing_relationships),"examples":quest_missing_relationships[:20],"meaning":"Quest records without a relationship record."},
        {"severity":"medium","area":"monster core combat data","count":len(monster_missing_core),"examples":monster_missing_core[:20],"meaning":"Monster records missing at least one selected core combat field."},
        {"severity":"medium","area":"combat profile source provenance","count":len(profiles_without_sources),"examples":profiles_without_sources[:20],"meaning":"Joined combat profiles with no source URL list."},
        {"severity":"medium","area":"partial item combat profiles","count":len(profiles_partial),"examples":profiles_partial[:20],"meaning":"Joined profiles not marked as having all expected joined fields."},
        {"severity":"low","area":"weapon-to-profile joins","count":len(weapons_missing_profiles),"examples":weapons_missing_profiles[:20],"meaning":"Weapon records without a joined item combat profile."},
    ]
    priorities = sorted(findings, key=lambda x: ({"high":0,"medium":1,"low":2}[x["severity"]], -x["count"], x["area"]))
    recommendations = [
        {"priority":1,"task":"Close equipment profile and requirement joins","reason":"Eligibility and equipment search cannot be reliable where candidate items lack profiles or requirement records."},
        {"priority":2,"task":"Verify weapon mechanics and item effects","reason":"DPS ranking depends on correct speed, attack style, damage style and special effects, not just bonuses."},
        {"priority":3,"task":"Expand source-backed quest and unlock facts","reason":"Unknown restrictions must not silently become eligible equipment."},
        {"priority":4,"task":"Expand monster-specific combat facts and rules","reason":"Accurate boss calculations require target defence, immunities, caps and phase-specific mechanics."},
        {"priority":5,"task":"Build complete-loadout DPS optimisation and upgrade deltas","reason":"Compare legal combinations under a budget using the same verified formula engine and disclose assumptions."},
    ]
    counts = {level: sum(x["severity"] == level and x["count"] > 0 for x in findings) for level in ("high","medium","low")}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "review_required" if any(x["count"] for x in findings) else "passed",
        "purpose":"Cross-domain data readiness audit for future account-aware, boss-aware Combat Lab search and upgrade recommendations.",
        "source_dataset_summaries": summaries,
        "cross_domain_joins": {
            "equipment_record_count":len(equipment),
            "equipment_with_combat_profile_count":sum(r.get("id") in profile_ids for r in equipment),
            "equipment_missing_combat_profile_ids":equipment_missing_profile,
            "equipment_missing_requirement_record_ids":equipment_missing_requirements,
            "weapon_record_count":len(weapons),
            "weapons_missing_combat_profile_ids":weapons_missing_profiles,
            "quest_record_count":len(quests),
            "quests_missing_relationship_record_ids":quest_missing_relationships,
            "quests_with_unknown_requirement_facts":len(unknown_quest_facts),
            "monster_record_count":len(monsters),
            "item_record_count":len(items),
            "item_combat_profile_count":len(profiles),
        },
        "findings": findings,
        "finding_groups_with_open_gaps":counts,
        "recommended_next_steps":recommendations,
        "errors":errors,
        "guardrails":[
            "Field presence and join coverage do not prove factual accuracy.",
            "Unknown requirement or unlock data must not be treated as no requirement.",
            "This audit does not calculate DPS, certify any loadout, or claim all OSRS items are covered.",
            "A complete Combat Lab requires verified formula rules, target-specific mechanics, eligibility checks and current prices.",
        ]
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default=str(REPORTS/"combat-lab-readiness.json"))
    args=parser.parse_args()
    result=build_report()
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result["status"]=="failed" else 0

if __name__=="__main__":
    raise SystemExit(main())
