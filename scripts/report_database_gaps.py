#!/usr/bin/env python3
"""Build an actionable data-gap queue from generated OSRS Hub datasets."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

def load_array(filename):
    try:
        data = json.loads((DIST / filename).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read dist/{filename}: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"dist/{filename} must be an array of objects")
    return data

def build_gap_report(loader=load_array):
    items, equipment, weapons = loader("items.json"), loader("equipment-stats.json"), loader("weapons.json")
    requirements, profiles = loader("item-requirements.json"), loader("item-combat-profiles.json")
    monsters, quests = loader("monsters-combat.json"), loader("quests.json")
    quest_links, relationships = loader("quest-relationships.json"), loader("item-relationships.json")
    equipment_ids = {r.get("id") for r in equipment}
    weapon_ids = {r.get("id") for r in weapons}
    requirement_ids = {r.get("item_id") for r in requirements}
    profile_by_id = {r.get("id"): r for r in profiles}
    relationship_ids = {r.get("item_id") for r in relationships}
    gaps = []
    def add(key, priority, area, count, denominator, impact, action, examples=None):
        gaps.append({"key":key,"priority":priority,"area":area,"affected_records":count,
          "denominator":denominator,"coverage_percent":round(100*(denominator-count)/denominator,2) if denominator else 0.0,
          "impact":impact,"recommended_action":action,"sample_ids":(examples or [])[:20]})
    missing_req=sorted(equipment_ids-requirement_ids)
    add("equipment_requirement_record_missing","high","item_requirements",len(missing_req),len(equipment_ids),
      "A missing normalized requirement record is unknown; it must not be treated as no requirements.",
      "Compare source equipment metadata and add only source-backed requirement records.",missing_req)
    missing_rel=sorted((equipment_ids|weapon_ids)-relationship_ids)
    add("equipment_or_weapon_relationship_missing","high","item_relationships",len(missing_rel),len(equipment_ids|weapon_ids),
      "Equipment or weapons may be absent from the relationship index used by downstream queries.",
      "Rebuild item relationships and investigate any equipment/weapon IDs still missing.",missing_rel)
    missing_profile=sorted(i for i in equipment_ids if not profile_by_id.get(i,{}).get("equipment_record_present",False))
    add("equipment_profile_link_missing","high","item_combat_profiles",len(missing_profile),len(equipment_ids),
      "Equipment may not be discoverable through the joined combat-profile view.",
      "Check the source IDs and join builder before changing any game stats.",missing_profile)
    bad_speed=sorted(r.get("id") for r in weapons if isinstance(r.get("attack_speed"),bool) or not isinstance(r.get("attack_speed"),int) or r.get("attack_speed")<=0)
    add("weapon_attack_speed_invalid_or_missing","high","weapons",len(bad_speed),len(weapons),
      "Combat timing needs a valid attack-speed tick value.",
      "Verify each affected weapon against its retained source; never guess a speed.",bad_speed)
    missing_source=sorted(r.get("id") for r in profiles if not isinstance(r.get("source_urls"),list) or not r.get("source_urls"))
    add("combat_profile_source_url_missing","medium","item_combat_profiles",len(missing_source),len(profiles),
      "Records without retained URLs are harder to independently verify.",
      "Carry forward the source URL from the matching upstream record.",missing_source)
    missing_monster=sorted(r.get("id") for r in monsters if any(r.get(f) is None for f in ("combat_level","hitpoints","attack_level","strength_level","defence_level")))
    add("monster_core_combat_fields_missing","high","monsters_combat",len(missing_monster),len(monsters),
      "Combat and readiness features may lack required inputs for affected monsters.",
      "Populate only verified values and preserve unknowns as null.",missing_monster)
    add("quest_catalogue_empty","critical","quests",int(not quests),1,
      "Quest unlock and readiness checks cannot work from an empty quest catalogue.",
      "Implement a maintained, versioned source adapter for verified quest IDs, names and provenance.")
    add("quest_relationships_empty","high","quest_relationships",int(not quest_links),1,
      "Quest dependency planning cannot work without prerequisite relationships.",
      "Import verified prerequisite edges and source URLs; do not infer an empty list from missing data.")
    priority={"critical":0,"high":1,"medium":2,"low":3}
    gaps.sort(key=lambda g:(priority[g["priority"]],-g["affected_records"],g["key"]))
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"passed",
      "meaning":"Actionable diagnostics based on generated dataset coverage. A gap means data is absent or unverified in this build, not that the fact is absent from OSRS.",
      "dataset_counts":{"items":len(items),"equipment":len(equipment),"weapons":len(weapons),"item_requirements":len(requirements),
        "item_combat_profiles":len(profiles),"monsters_combat":len(monsters),"quests":len(quests),"quest_relationships":len(quest_links)},
      "gap_count":len(gaps),"gaps":gaps,"guardrails":[
        "Missing requirements are not interpreted as zero requirements.",
        "Unknown quest relationships are not interpreted as no prerequisites.",
        "The report prioritizes gaps and does not mutate source data.",
        "Live Grand Exchange prices are not read or inferred."]}

def main():
    try: report=build_gap_report()
    except ValueError as exc:
        print(json.dumps({"status":"failed","error":str(exc)},indent=2)); return 1
    REPORTS.mkdir(parents=True,exist_ok=True)
    (REPORTS/"database-gap-queue.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
