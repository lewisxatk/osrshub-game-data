#!/usr/bin/env python3
"""Bounded search of account-eligible melee loadouts using scoped baseline DPS."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from build_combat_studio_plan import build_plan
from evaluate_combat_loadout import evaluate_loadout
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"; REPORTS=ROOT/"reports"

def search_loadouts(equipment, requirements, quest_unlocks, profiles, profile, costs, budget, inputs, attack_style="slash", candidates_per_slot=8, node_limit=100000):
    if attack_style not in ("stab","slash","crush"): raise ValueError("attack_style must be stab, slash or crush")
    if not isinstance(profiles,list) or any(not isinstance(x,dict) for x in profiles): raise ValueError("profiles must be an array of objects")
    if not isinstance(inputs,dict): raise ValueError("combat inputs must be an object")
    if isinstance(budget,bool) or not isinstance(budget,int) or budget<0: raise ValueError("budget must be a non-negative integer")
    if isinstance(candidates_per_slot,bool) or not isinstance(candidates_per_slot,int) or not 1<=candidates_per_slot<=25: raise ValueError("candidates_per_slot must be between 1 and 25")
    if isinstance(node_limit,bool) or not isinstance(node_limit,int) or node_limit<1: raise ValueError("node_limit must be positive")
    classification_budget=sum(v for v in costs.values() if isinstance(v,int) and not isinstance(v,bool) and v>=0)
    audited=build_plan(equipment,requirements,quest_unlocks,profile,costs,classification_budget,"melee_strength",50,1)
    eligible={r["item_id"] for r in audited["audit"] if r["status"]=="eligible"}
    byid={}
    for row in profiles:
        rid=row.get("id")
        if isinstance(rid,bool) or not isinstance(rid,int) or rid<0: continue
        if rid in byid: raise ValueError(f"duplicate combat profile ID {rid}")
        byid[rid]=row
    grouped={}; unmatched=[]
    style_field={"stab":"attack_stab","slash":"attack_slash","crush":"attack_crush"}[attack_style]
    for rid in sorted(eligible):
        row=byid.get(rid)
        if row is None: unmatched.append({"item_id":rid,"reason":"No joined combat profile"}); continue
        slot=row.get("slot"); cost=costs.get(str(rid),costs.get(rid)); bonuses=row.get("bonuses")
        if not isinstance(slot,str) or not slot.strip(): unmatched.append({"item_id":rid,"reason":"Combat profile has no known slot"}); continue
        if isinstance(cost,bool) or not isinstance(cost,int) or cost<0: unmatched.append({"item_id":rid,"reason":"No valid caller-supplied cost"}); continue
        if cost>budget: continue
        if not isinstance(bonuses,dict) or any(isinstance(bonuses.get(k),bool) or not isinstance(bonuses.get(k),int) for k in (style_field,"melee_strength")):
            unmatched.append({"item_id":rid,"reason":"Required attack or strength bonus is unknown"}); continue
        grouped.setdefault(" ".join(slot.casefold().split()),[]).append(row)
    if "weapon" not in grouped:
        return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"no_eligible_weapon","attack_style":attack_style,"budget_gp":budget,"best_loadout":None,"top_loadouts":[],"search":{"nodes_visited":0,"node_limit":node_limit,"truncated":False},"candidate_counts":{"eligible_ids":len(eligible),"profiled_candidates":sum(map(len,grouped.values())),"unmatched_or_unknown":len(unmatched)},"eligibility_audit":audited["audit"],"unmatched_candidates":unmatched,"guardrails":["No complete loadout is claimed without an eligible weapon."]}
    slot_rows=[]
    for slot,rows in grouped.items():
        rows.sort(key=lambda r:(costs.get(str(r["id"]),costs.get(r["id"])),-r["bonuses"]["melee_strength"],str(r.get("name","")).casefold(),r["id"]))
        slot_rows.append((slot,rows[:candidates_per_slot]))
    slot_rows.sort(key=lambda p:(p[0]!="weapon",p[0]))
    results=[]; nodes=0; truncated=False
    def visit(i,selected,spend):
        nonlocal nodes,truncated
        if nodes>=node_limit: truncated=True; return
        nodes+=1
        if i==len(slot_rows):
            if not any(r.get("slot")=="weapon" for r in selected): return
            try: result=evaluate_loadout(profiles,[r["id"] for r in selected],costs,budget,inputs,attack_style)
            except ValueError: return
            results.append(result)
            results.sort(key=lambda r:(-r["combat_result"]["dps"],r["total_cost_gp"],tuple(x["item_id"] for x in r["selected_items"])))
            del results[20:]; return
        slot,rows=slot_rows[i]
        if slot!="weapon": visit(i+1,selected,spend)
        for row in rows:
            rid=row["id"]; cost=costs.get(str(rid),costs.get(rid))
            if spend+cost>budget or any(x["id"]==rid for x in selected): continue
            visit(i+1,selected+[row],spend+cost)
            if truncated: return
    visit(0,[],0)
    best=results[0] if results else None
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"search_truncated" if truncated else ("dps_ranked_candidates" if results else "no_valid_loadout"),"attack_style":attack_style,"budget_gp":budget,"best_loadout":best,
      "top_loadouts":[{"rank":i+1,"total_cost_gp":r["total_cost_gp"],"remaining_budget_gp":r["remaining_budget_gp"],"dps":r["combat_result"]["dps"],"hit_chance":r["combat_result"]["hit_chance"],"max_hit":r["combat_result"]["max_hit"],"weapon":r["weapon"],"selected_items":r["selected_items"],"warnings":r["warnings"]} for i,r in enumerate(results)],
      "search":{"nodes_visited":nodes,"node_limit":node_limit,"truncated":truncated,"slots_considered":len(slot_rows),"candidate_cap_per_slot":candidates_per_slot},
      "candidate_counts":{"eligible_ids":len(eligible),"profiled_candidates":sum(map(len,grouped.values())),"unmatched_or_unknown":len(unmatched),"loadouts_evaluated":len(results)},
      "eligibility_audit":audited["audit"],"unmatched_candidates":unmatched,
      "guardrails":["DPS ranking uses the existing scoped baseline melee formula and identical caller-supplied combat inputs for every candidate.","This is not boss-verified DPS: prayers, potions, special attacks, target phases, immunities, set effects, damage caps and supplies are not modelled.","Only items passing explicit skill and item-to-quest evidence are searched; unknown or missing requirement data is withheld.","Prices are caller-supplied, not live GE data. Search is bounded by candidate and node limits.","Unique slots and one weapon are checked, but complete item compatibility and source accuracy are not proven."]}

def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--equipment",default=str(DIST/"equipment-stats.json")); p.add_argument("--requirements",default=str(DIST/"item-requirements.json"))
    p.add_argument("--quest-unlocks",required=True); p.add_argument("--profiles",default=str(DIST/"item-combat-profiles.json"))
    p.add_argument("--profile",required=True); p.add_argument("--costs",required=True); p.add_argument("--combat-inputs",required=True)
    p.add_argument("--budget",required=True,type=int); p.add_argument("--style",choices=("stab","slash","crush"),default="slash")
    p.add_argument("--candidates-per-slot",type=int,default=8); p.add_argument("--node-limit",type=int,default=100000); p.add_argument("--output",default=str(REPORTS/"combat-studio-dps-search.json"))
    a=p.parse_args()
    try: result=search_loadouts(read_json(a.equipment),read_json(a.requirements),read_json(a.quest_unlocks),read_json(a.profiles),read_json(a.profile),read_json(a.costs),a.budget,read_json(a.combat_inputs),a.style,a.candidates_per_slot,a.node_limit)
    except (OSError,json.JSONDecodeError,ValueError) as exc: print(json.dumps({"status":"failed","error":str(exc)},indent=2)); return 1
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k in ("status","best_loadout","top_loadouts","search","candidate_counts","guardrails")},ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
