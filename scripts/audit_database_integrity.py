#!/usr/bin/env python3
"""Audit cross-dataset IDs and joins without inventing missing OSRS facts."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

def load_array(name):
    try:
        rows = json.loads((DIST / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read dist/{name}: {exc}") from exc
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"dist/{name} must be an array of objects")
    return rows

def ids(rows, field, label, errors):
    result = set()
    duplicates = set()
    for index, row in enumerate(rows):
        value = row.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append({"dataset": label, "index": index, "issue": "invalid_id", "value": value})
            continue
        if value in result:
            duplicates.add(value)
            errors.append({"dataset": label, "index": index, "issue": "duplicate_id", "value": value})
        result.add(value)
    return result

def audit_datasets(datasets):
    errors, warnings = [], []
    required = ("items.json", "equipment-stats.json", "weapons.json", "item-requirements.json",
                "item-relationships.json", "item-combat-profiles.json", "monsters-combat.json",
                "quests.json", "quest-relationships.json")
    missing = [name for name in required if name not in datasets]
    if missing:
        raise ValueError("Missing input datasets: " + ", ".join(missing))
    item_ids = ids(datasets["items.json"], "id", "items.json", errors)
    equipment_ids = ids(datasets["equipment-stats.json"], "id", "equipment-stats.json", errors)
    weapon_ids = ids(datasets["weapons.json"], "id", "weapons.json", errors)
    requirement_ids = ids(datasets["item-requirements.json"], "item_id", "item-requirements.json", errors)
    profile_ids = ids(datasets["item-combat-profiles.json"], "id", "item-combat-profiles.json", errors)
    monster_ids = ids(datasets["monsters-combat.json"], "id", "monsters-combat.json", errors)
    quest_ids = ids(datasets["quests.json"], "id", "quests.json", errors)
    relationship_item_ids = set()
    broken_relationships = 0
    for index, row in enumerate(datasets["item-relationships.json"]):
        iid = row.get("item_id")
        if isinstance(iid, bool) or not isinstance(iid, int):
            errors.append({"dataset":"item-relationships.json","index":index,"issue":"invalid_item_id","value":iid})
            continue
        relationship_item_ids.add(iid)
        if iid not in item_ids:
            broken_relationships += 1
            errors.append({"dataset":"item-relationships.json","index":index,"issue":"orphan_item_relationship","item_id":iid})
        rels = row.get("relationships")
        if not isinstance(rels, list):
            errors.append({"dataset":"item-relationships.json","index":index,"issue":"relationships_not_array"})
            continue
        for rel in rels:
            if not isinstance(rel, dict):
                errors.append({"dataset":"item-relationships.json","index":index,"issue":"relationship_not_object"})
                continue
            rid, kind = rel.get("record_id"), rel.get("type")
            targets = {
                "has_equipment_stats": equipment_ids,
                "has_weapon_data": weapon_ids,
                "has_skill_requirements": requirement_ids,
                "has_combat_profile": profile_ids,
            }
            target = targets.get(kind)
            if kind not in targets:
                errors.append({"dataset":"item-relationships.json","index":index,"issue":"unknown_relationship_type","relationship_type":kind})
            elif rid not in target:
                errors.append({"dataset":"item-relationships.json","index":index,"issue":"orphan_join_target","relationship_type":kind,"record_id":rid})
    orphan_requirements = sorted(requirement_ids - item_ids)
    for iid in orphan_requirements:
        errors.append({"dataset":"item-requirements.json","issue":"orphan_item_requirement","item_id":iid})
    orphan_profiles = sorted(profile_ids - item_ids)
    for iid in orphan_profiles:
        errors.append({"dataset":"item-combat-profiles.json","issue":"orphan_item_profile","item_id":iid})
    missing_profiles = sorted(item_ids - profile_ids)
    if missing_profiles:
        warnings.append({"dataset":"item-combat-profiles.json","issue":"items_without_profile","count":len(missing_profiles),"sample_ids":missing_profiles[:20]})
    # Relationship rows are intentionally emitted only for items with equipment/weapon
    # records. Restrict the gap check to items marked player-equipable in the source data.
    equipable_ids = {
        row["id"] for row in datasets["items.json"]
        if isinstance(row.get("id"), int) and not isinstance(row.get("id"), bool)
        and (row.get("equipable_by_player") is True or row.get("equipable_weapon") is True)
    }
    missing_relationships = sorted(equipable_ids - relationship_item_ids)
    if missing_relationships:
        warnings.append({"dataset":"item-relationships.json","issue":"equipable_items_without_relationship_record","count":len(missing_relationships),"sample_ids":missing_relationships[:20]})
    for index, row in enumerate(datasets["item-combat-profiles.json"]):
        iid = row.get("id")
        for flag, target, field in (
            ("equipment_record_present", equipment_ids, "equipment"),
            ("weapon_record_present", weapon_ids, "weapon"),
            ("skill_requirement_record_present", requirement_ids, "requirements"),
        ):
            value = row.get(flag)
            if not isinstance(value, bool):
                errors.append({"dataset":"item-combat-profiles.json","index":index,"issue":"presence_flag_not_boolean","field":flag})
            elif value != (iid in target):
                errors.append({"dataset":"item-combat-profiles.json","index":index,"issue":"presence_flag_join_mismatch","field":flag,"item_id":iid})
    if not quest_ids:
        warnings.append({"dataset":"quests.json","issue":"empty_quest_catalogue","message":"Quest prerequisite coverage cannot be assessed until verified quest facts are imported."})
    if not datasets["quest-relationships.json"]:
        warnings.append({"dataset":"quest-relationships.json","issue":"empty_quest_relationships","message":"No quest prerequisite relationships are currently available; this is not evidence that quests have no prerequisites."})
    bad_quest_refs = 0
    for index, row in enumerate(datasets["quest-relationships.json"]):
        qid = row.get("quest_id")
        if qid not in quest_ids:
            bad_quest_refs += 1
            errors.append({"dataset":"quest-relationships.json","index":index,"issue":"orphan_quest_relationship","quest_id":qid})
        prereqs = row.get("prerequisite_quest_ids", [])
        if not isinstance(prereqs, list):
            errors.append({"dataset":"quest-relationships.json","index":index,"issue":"prerequisite_ids_not_array","quest_id":qid})
            continue
        for prereq in prereqs:
            if prereq not in quest_ids:
                errors.append({"dataset":"quest-relationships.json","index":index,"issue":"unknown_prerequisite_quest_id","quest_id":qid,"prerequisite_quest_id":prereq})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else ("review_required" if warnings else "passed"),
        "counts": {
            "items":len(item_ids), "equipment_records":len(equipment_ids), "weapon_records":len(weapon_ids),
            "item_requirement_records":len(requirement_ids), "item_combat_profiles":len(profile_ids),
            "monster_combat_records":len(monster_ids), "quest_records":len(quest_ids),
            "item_relationship_records":len(datasets["item-relationships.json"]),
            "orphan_requirement_count":len(orphan_requirements), "orphan_profile_count":len(orphan_profiles),
            "orphan_relationship_count":broken_relationships, "orphan_quest_relationship_count":bad_quest_refs,
        },
        "error_count":len(errors), "warning_count":len(warnings),
        "errors":errors[:300], "warnings":warnings[:200],
        "guardrails":[
            "This audit checks cross-dataset integrity, not whether upstream OSRS facts are correct.",
            "Missing records and unknown quest prerequisites remain unknown; they are never inferred to be absent.",
            "Item IDs and quest IDs are separate namespaces and are checked only against their matching datasets.",
            "An empty quest dataset raises a coverage warning rather than proving there are no quest requirements."
        ]
    }

def main():
    try:
        names = ("items.json", "equipment-stats.json", "weapons.json", "item-requirements.json",
                 "item-relationships.json", "item-combat-profiles.json", "monsters-combat.json",
                 "quests.json", "quest-relationships.json")
        data = {name: load_array(name) for name in names}
        report = audit_datasets(data)
    except ValueError as exc:
        print(json.dumps({"status":"failed","error":str(exc)},indent=2))
        return 1
    REPORTS.mkdir(parents=True,exist_ok=True)
    (REPORTS/"database-integrity.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if report["status"] == "failed" else 0

if __name__ == "__main__":
    raise SystemExit(main())
