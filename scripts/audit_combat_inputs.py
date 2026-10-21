#!/usr/bin/env python3
"""Validate a player profile, item cost map, and scoped combat inputs before comparisons."""
from __future__ import annotations
import json, math
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/"reports"
REQUIRED_COMBAT=("effective_attack","effective_strength","effective_defence","defence_bonus")
SKILLS=("attack","strength","defence","ranged","magic","hitpoints","prayer")
def audit_inputs(profile,costs,combat,budget):
    errors=[]; warnings=[]
    if not isinstance(profile,dict): errors.append("profile must be a JSON object"); profile={}
    if not isinstance(costs,dict): errors.append("costs must be a JSON object"); costs={}
    if not isinstance(combat,dict): errors.append("combat inputs must be a JSON object"); combat={}
    if isinstance(budget,bool) or not isinstance(budget,int) or budget<0: errors.append("budget must be a non-negative integer")
    skills=profile.get("skills")
    if not isinstance(skills,dict):
        errors.append("profile.skills must be an object")
        skills={}
    normalized={}
    for name,value in skills.items():
        if not isinstance(name,str) or not name.strip():
            errors.append("skill names must be non-empty strings"); continue
        if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=99:
            errors.append(f"skill {name!r} must be an integer from 1 to 99"); continue
        key=" ".join(name.casefold().split())
        if key in normalized: errors.append(f"duplicate skill after case/space normalization: {name}")
        normalized[key]=value
    missing_skills=[skill for skill in SKILLS if skill not in normalized]
    if missing_skills: warnings.append("Profile omits skill levels: "+", ".join(missing_skills))
    for key in REQUIRED_COMBAT:
        value=combat.get(key)
        if isinstance(value,bool) or not isinstance(value,int) or value<0:
            errors.append(f"combat input {key!r} must be a non-negative integer")
    if isinstance(combat.get("effective_attack"),int) and not isinstance(combat.get("effective_attack"),bool) and isinstance(combat.get("effective_strength"),int) and not isinstance(combat.get("effective_strength"),bool):
        if combat["effective_attack"]>255 or combat["effective_strength"]>255:
            warnings.append("Effective combat level exceeds 255; confirm the upstream boost calculation and intended mechanics")
    invalid_costs=[]
    for item_id,cost in costs.items():
        if not (isinstance(item_id,str) and item_id.isdigit()) and not (isinstance(item_id,int) and not isinstance(item_id,bool) and item_id>=0):
            invalid_costs.append(str(item_id)); continue
        if isinstance(cost,bool) or not isinstance(cost,int) or cost<0: invalid_costs.append(str(item_id))
    if invalid_costs: errors.append("Invalid item cost entries (IDs must be non-negative integers and costs non-negative integer GP): "+", ".join(invalid_costs[:20]))
    exclusions=profile.get("excluded_item_ids",[])
    if not isinstance(exclusions,list) or any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in exclusions):
        errors.append("profile.excluded_item_ids must be an array of non-negative integer IDs")
    excluded_names=profile.get("excluded_item_names",[])
    if not isinstance(excluded_names,list) or any(not isinstance(x,str) or not x.strip() for x in excluded_names):
        errors.append("profile.excluded_item_names must be an array of non-empty strings")
    if not profile.get("source_url"): warnings.append("Profile has no source URL or import provenance")
    if not combat.get("source_url"): warnings.append("Combat input has no source URL/provenance; formula outputs remain baseline-only")
    if not combat.get("checked_on"): warnings.append("Combat inputs have no checked_on date")
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"failed" if errors else "passed_with_warnings" if warnings else "passed","budget_gp":budget if isinstance(budget,int) and not isinstance(budget,bool) and budget>=0 else None,"profile_skill_count":len(normalized),"cost_entry_count":len(costs),"combat_input_fields_present":sorted(k for k in REQUIRED_COMBAT if k in combat),"errors":errors,"warnings":warnings,"guardrails":["Validation checks shape and plausible ranges, not whether OSRS facts are correct.","Effective levels must be calculated from verified boosts, styles, prayers and other applicable mechanics upstream.","Item costs are user supplied and are not live Grand Exchange prices."]}
def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",required=True); p.add_argument("--costs",required=True); p.add_argument("--inputs",required=True); p.add_argument("--budget",required=True,type=int); p.add_argument("--output",default=str(REPORTS/"combat-input-audit.json"))
    a=p.parse_args()
    try:
        load=lambda path:json.loads(Path(path).read_text(encoding="utf-8"))
        result=audit_inputs(load(a.profile),load(a.costs),load(a.inputs),a.budget)
    except (OSError,json.JSONDecodeError) as exc:
        result={"status":"failed","errors":[str(exc)],"warnings":[]}
    REPORTS.mkdir(parents=True,exist_ok=True); Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 1 if result["status"]=="failed" else 0
if __name__=="__main__":raise SystemExit(main())
