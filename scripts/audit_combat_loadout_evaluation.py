#!/usr/bin/env python3
"""Audit arithmetic and consistency of a generated baseline loadout evaluation."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/"reports"

def audit_report(report):
    if not isinstance(report,dict):
        raise ValueError("evaluation report must be a JSON object")
    errors=[]; warnings=[]
    selected=report.get("selected_items")
    if not isinstance(selected,list) or not selected:
        errors.append("selected_items must be a non-empty array")
        selected=[]
    seen_ids=set(); seen_slots=set(); calculated_cost=0
    for index,item in enumerate(selected):
        if not isinstance(item,dict):
            errors.append(f"selected_items[{index}] must be an object"); continue
        rid=item.get("item_id")
        if isinstance(rid,bool) or not isinstance(rid,int) or rid<0:
            errors.append(f"selected_items[{index}] has invalid item_id")
        elif rid in seen_ids:
            errors.append(f"duplicate selected item ID {rid}")
        seen_ids.add(rid)
        slot=item.get("slot")
        if isinstance(slot,str) and slot:
            if slot in seen_slots: errors.append(f"multiple selected items in slot {slot!r}")
            seen_slots.add(slot)
        cost=item.get("cost_gp")
        if isinstance(cost,bool) or not isinstance(cost,int) or cost<0:
            errors.append(f"selected item {rid} has invalid cost_gp")
        else: calculated_cost+=cost
        for key in ("attack_bonus_contribution","melee_strength_contribution"):
            value=item.get(key)
            if isinstance(value,bool) or not isinstance(value,int):
                errors.append(f"selected item {rid} has invalid {key}")
    budget=report.get("budget_gp"); total=report.get("total_cost_gp"); remaining=report.get("remaining_budget_gp")
    for name,value in (("budget_gp",budget),("total_cost_gp",total),("remaining_budget_gp",remaining)):
        if isinstance(value,bool) or not isinstance(value,int) or value<0: errors.append(f"{name} must be a non-negative integer")
    if all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in (budget,total,remaining)):
        if total!=calculated_cost: errors.append("total_cost_gp does not match sum of selected item costs")
        if total+remaining!=budget: errors.append("total_cost_gp plus remaining_budget_gp must equal budget_gp")
        if total>budget: errors.append("loadout exceeds budget")
    agg=report.get("aggregated_bonuses")
    if not isinstance(agg,dict): errors.append("aggregated_bonuses must be an object")
    else:
        for field,contrib_field in (("attack_style_bonus","attack_bonus_contribution"),("melee_strength","melee_strength_contribution")):
            value=agg.get(field)
            if isinstance(value,bool) or not isinstance(value,int): errors.append(f"aggregated {field} must be an integer")
            elif value!=sum(item.get(contrib_field,0) for item in selected if isinstance(item,dict) and isinstance(item.get(contrib_field),int) and not isinstance(item.get(contrib_field),bool)):
                errors.append(f"aggregated {field} does not match selected item contributions")
    weapon=report.get("weapon")
    if not isinstance(weapon,dict) or isinstance(weapon.get("attack_speed_ticks"),bool) or not isinstance(weapon.get("attack_speed_ticks"),int) or weapon.get("attack_speed_ticks",0)<=0:
        errors.append("weapon must provide a positive integer attack_speed_ticks")
    result=report.get("combat_result")
    if not isinstance(result,dict) or result.get("status")!="baseline_only" or not isinstance(result.get("dps"),(int,float)) or isinstance(result.get("dps"),bool) or result.get("dps",0)<0:
        errors.append("combat_result is missing valid baseline_only DPS output")
    guardrails=report.get("guardrails")
    if not isinstance(guardrails,list) or not guardrails:
        warnings.append("report has no guardrail explanations")
    if report.get("status")!="baseline_loadout_estimate_with_limitations":
        errors.append("unexpected evaluation status")
    return {
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "status":"failed" if errors else "review_required" if warnings else "passed",
      "error_count":len(errors),"warning_count":len(warnings),"errors":errors,"warnings":warnings,
      "calculated_item_cost_gp":calculated_cost,
      "guardrails":["Consistency checks do not verify upstream OSRS facts or effective-level calculations.","A structurally valid baseline DPS report is not proof of boss-specific accuracy."]
    }

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",default=str(REPORTS/"combat-loadout-evaluation.json"))
    parser.add_argument("--output",default=str(REPORTS/"combat-loadout-evaluation-audit.json"))
    args=parser.parse_args()
    try:
        report=json.loads(Path(args.input).read_text(encoding="utf-8"))
        result=audit_report(report)
    except (OSError,json.JSONDecodeError,ValueError) as exc:
        result={"status":"failed","error_count":1,"warning_count":0,"errors":[str(exc)],"warnings":[]}
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result["status"]=="failed" else 0
if __name__=="__main__": raise SystemExit(main())
