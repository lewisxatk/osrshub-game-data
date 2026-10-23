#!/usr/bin/env python3
"""Choose a budget-constrained multi-slot stat shortlist from planner candidates.

This is a combinatorial stat optimiser, not a verified boss DPS optimiser.
Only candidates marked candidate_with_unknown_restrictions are selectable;
quest/unlock uncertainty remains visible in the output. Missing slots may be
left empty. Candidate generation and costs come from the caller's prior report.
"""
from __future__ import annotations
import argparse,json,math
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/"reports"
def optimize_loadout(shortlist,budget,top_per_slot=8,node_limit=100000):
    if not isinstance(shortlist,dict) or not isinstance(shortlist.get("results_by_slot"),dict):
        raise ValueError("shortlist must contain results_by_slot object")
    if isinstance(budget,bool) or not isinstance(budget,int) or budget<0:
        raise ValueError("budget must be a non-negative integer")
    if isinstance(top_per_slot,bool) or not isinstance(top_per_slot,int) or not 1<=top_per_slot<=50:
        raise ValueError("top_per_slot must be between 1 and 50")
    if isinstance(node_limit,bool) or not isinstance(node_limit,int) or node_limit<1:
        raise ValueError("node_limit must be positive")
    slots=[]
    skipped={}
    for slot,rows in sorted(shortlist["results_by_slot"].items()):
        if not isinstance(rows,list):
            skipped[slot]="malformed candidate list"; continue
        candidates=[]
        for row in rows:
            if not isinstance(row,dict): continue
            if row.get("status")!="candidate_with_unknown_restrictions": continue
            cost=row.get("cost"); value=row.get("objective_value"); item_id=row.get("item_id")
            if isinstance(cost,bool) or not isinstance(cost,int) or cost<0: continue
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value): continue
            if isinstance(item_id,bool) or not isinstance(item_id,int): continue
            if cost>budget: continue
            candidates.append({**row,"cost":cost,"objective_value":float(value),"slot":slot})
        candidates.sort(key=lambda x:(-x["objective_value"],x["cost"],x.get("item_name","").casefold(),x["item_id"]))
        if candidates: slots.append((slot,candidates[:top_per_slot]))
        else: skipped[slot]="no selectable candidates with known cost and objective value"
    # Search highest total objective value subject to total budget. The empty
    # choice is always available, so a slot can be skipped if all choices cost too much.
    suffix_max=[0.0]*(len(slots)+1)
    for i in range(len(slots)-1,-1,-1):
        suffix_max[i]=suffix_max[i+1]+max([0.0]+[x["objective_value"] for x in slots[i][1]])
    best={"value":0.0,"cost":0,"items":[]}
    nodes=0; truncated=False; duplicate_item_conflicts=0
    def visit(index,cost,value,chosen):
        nonlocal best,nodes,truncated,duplicate_item_conflicts
        nodes+=1
        if nodes>node_limit:
            truncated=True; return
        if value+suffix_max[index] < best["value"]: return
        if index==len(slots):
            if (value>best["value"] or (value==best["value"] and cost<best["cost"])):
                best={"value":value,"cost":cost,"items":list(chosen)}
            return
        slot,candidates=slots[index]
        visit(index+1,cost,value,chosen)
        if truncated: return
        chosen_ids = {item["item_id"] for item in chosen}
        for candidate in candidates:
            # One physical item cannot occupy two equipment slots at once.
            if candidate["item_id"] in chosen_ids:
                duplicate_item_conflicts += 1
                continue
            next_cost=cost+candidate["cost"]
            if next_cost<=budget:
                visit(index+1,next_cost,value+candidate["objective_value"],chosen+[candidate])
                if truncated: return
    visit(0,0,0.0,[])
    return {
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "status":"search_truncated" if truncated else "stat_loadout_candidate",
      "budget_gp":budget,"total_cost_gp":best["cost"],
      "objective":shortlist.get("objective"),"objective_field":shortlist.get("objective_field"),
      "objective_total":round(best["value"],6),
      "selected_items":[{"item_id":x["item_id"],"item_name":x["item_name"],"slot":x["slot"],"cost":x["cost"],"objective_value":x["objective_value"],"eligibility_status":x["status"],"reasons":x.get("reasons",[])} for x in best["items"]],
      "selected_slot_count":len(best["items"]),"slots_considered":len(slots),"skipped_slots":skipped,
      "duplicate_item_conflict_branches_skipped":duplicate_item_conflicts,
      "search_nodes":min(nodes,node_limit),"search_node_limit":node_limit,
      "guardrails":[
        "Optimises the sum of one selected stat per slot; it does not calculate complete-loadout DPS.",
        "Only candidates with known supplied costs are considered; no live GE prices are fetched.",
        "Candidates may still have unknown quest, unlock, item-variant or requirement restrictions.",
        "The same item ID cannot be selected for multiple equipment slots in one loadout.",
        "This is a shortlist for review, not a confirmed usable or best-in-slot setup."
      ]
    }
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shortlist",default=str(REPORTS/"equipment-shortlist.json"))
    p.add_argument("--budget",required=True,type=int)
    p.add_argument("--top-per-slot",type=int,default=8)
    p.add_argument("--node-limit",type=int,default=100000)
    p.add_argument("--output",default=str(REPORTS/"equipment-loadout-candidate.json"))
    a=p.parse_args()
    try:
        shortlist=json.loads(Path(a.shortlist).read_text(encoding="utf-8"))
        result=optimize_loadout(shortlist,a.budget,a.top_per_slot,a.node_limit)
    except (OSError,json.JSONDecodeError,ValueError) as exc:
        print(json.dumps({"status":"failed","error":str(exc)},indent=2)); return 1
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
