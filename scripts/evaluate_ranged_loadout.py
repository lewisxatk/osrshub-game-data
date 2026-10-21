#!/usr/bin/env python3
"""Evaluate a selected ranged loadout with explicitly limited baseline combat math."""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from combat_math import calculate_core
ROOT=Path(__file__).resolve().parents[1]; DIST=ROOT/"dist"; REPORTS=ROOT/"reports"
def evaluate_ranged_loadout(profiles,selected_ids,costs,budget,inputs):
 if not isinstance(profiles,list) or any(not isinstance(x,dict) for x in profiles): raise ValueError("profiles must be an array of objects")
 if not isinstance(selected_ids,list) or not selected_ids: raise ValueError("selected IDs must be a non-empty array")
 if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in selected_ids) or len(selected_ids)!=len(set(selected_ids)): raise ValueError("selected IDs must be unique non-negative integers")
 if isinstance(budget,bool) or not isinstance(budget,int) or budget<0: raise ValueError("budget must be a non-negative integer")
 if not isinstance(costs,dict) or not isinstance(inputs,dict): raise ValueError("costs and inputs must be objects")
 for key in ("effective_ranged","effective_defence","defence_bonus"):
  if isinstance(inputs.get(key),bool) or not isinstance(inputs.get(key),int) or inputs[key]<0: raise ValueError(f"{key} must be a non-negative integer")
 by_id={}
 for row in profiles:
  rid=row.get("id")
  if isinstance(rid,int) and not isinstance(rid,bool):
   if rid in by_id: raise ValueError(f"duplicate profile ID {rid}")
   by_id[rid]=row
 if any(x not in by_id for x in selected_ids): raise ValueError("one or more selected IDs are missing from combat profiles")
 cost_sum=0; attack=0; strength=0; slots=set(); weapons=[]; chosen=[]; warnings=[]
 for rid in selected_ids:
  row=by_id[rid]; slot=row.get("slot")
  if not isinstance(slot,str) or not slot: warnings.append(f"Item {rid} has unknown slot")
  elif slot in slots: raise ValueError(f"multiple selected items occupy slot {slot!r}")
  else: slots.add(slot)
  cost=costs.get(str(rid),costs.get(rid))
  if isinstance(cost,bool) or not isinstance(cost,int) or cost<0: raise ValueError(f"item {rid} has no valid supplied GP cost")
  cost_sum+=cost; bonuses=row.get("bonuses")
  if not isinstance(bonuses,dict): raise ValueError(f"item {rid} has no bonuses object")
  a=bonuses.get("attack_ranged"); s=bonuses.get("ranged_strength")
  if isinstance(a,bool) or not isinstance(a,int): raise ValueError(f"item {rid} has unknown ranged attack bonus")
  if isinstance(s,bool) or not isinstance(s,int): raise ValueError(f"item {rid} has unknown ranged strength bonus")
  attack+=a; strength+=s
  if slot=="weapon": weapons.append(row)
  if row.get("skill_requirements") is None: warnings.append(f"{row.get('name',rid)} has no normalized skill requirement record")
  if row.get("data_status")!="joined_fields_present": warnings.append(f"{row.get('name',rid)} has partial combat data")
  chosen.append({"item_id":rid,"item_name":row.get("name",""),"slot":slot,"cost_gp":cost,"ranged_attack_contribution":a,"ranged_strength_contribution":s,"skill_requirements":row.get("skill_requirements"),"source_urls":row.get("source_urls",[])})
 if cost_sum>budget: raise ValueError(f"loadout costs {cost_sum} GP, exceeding budget {budget} GP")
 if len(weapons)!=1: raise ValueError(f"select exactly one weapon; found {len(weapons)}")
 speed=weapons[0].get("attack_speed")
 if isinstance(speed,bool) or not isinstance(speed,int) or speed<=0: raise ValueError("weapon has no valid attack speed")
 result=calculate_core({"effective_attack":inputs["effective_ranged"],"attack_bonus":attack,"effective_defence":inputs["effective_defence"],"defence_bonus":inputs["defence_bonus"],"effective_strength":inputs["effective_ranged"],"strength_bonus":strength,"attack_speed_ticks":speed})
 return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"baseline_ranged_loadout_estimate_with_limitations","budget_gp":budget,"total_cost_gp":cost_sum,"remaining_budget_gp":budget-cost_sum,"selected_items":chosen,"aggregated_bonuses":{"attack_ranged":attack,"ranged_strength":strength},"weapon":{"item_id":weapons[0]["id"],"item_name":weapons[0].get("name",""),"attack_speed_ticks":speed},"combat_result":result,"warnings":sorted(set(warnings)),"guardrails":["This is baseline ranged arithmetic using supplied effective ranged level and summed bonuses, not a complete ranged formula implementation.","Ammunition effects, prayers, potions, special attacks, weapon/style-specific mechanics and boss mechanics are not modelled.","No Vorkath-specific mechanics, supply costs, quest/unlock verification or live GE prices are included.","Evaluates a caller-selected loadout; does not search all combinations or claim best-in-slot."]}
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--selected",required=True); p.add_argument("--costs",required=True); p.add_argument("--inputs",required=True); p.add_argument("--budget",required=True,type=int); p.add_argument("--profiles",default=str(DIST/"item-combat-profiles.json")); p.add_argument("--output",default=str(REPORTS/"ranged-loadout-evaluation.json")); a=p.parse_args()
 try:
  load=lambda x:json.loads(Path(x).read_text(encoding="utf-8")); result=evaluate_ranged_loadout(load(a.profiles),load(a.selected),load(a.costs),a.budget,load(a.inputs))
 except (OSError,json.JSONDecodeError,ValueError) as e: print(json.dumps({"status":"failed","error":str(e)},indent=2)); return 1
 out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
