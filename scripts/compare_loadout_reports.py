#!/usr/bin/env python3
"""Compare baseline loadout reports and explain DPS/cost deltas."""
import argparse,json,math
from datetime import datetime,timezone
from pathlib import Path
REPORTS=Path(__file__).resolve().parents[1]/"reports"
def compare_reports(current,candidate):
 if not isinstance(current,dict) or not isinstance(candidate,dict): raise ValueError("reports must be objects")
 def num(r,path):
  x=r
  for p in path.split("."):
   if not isinstance(x,dict): return None
   x=x.get(p)
  return x if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) else None
 cd=num(current,"combat_result.dps"); nd=num(candidate,"combat_result.dps"); cc=num(current,"total_cost_gp"); nc=num(candidate,"total_cost_gp")
 if None in (cd,nd,cc,nc) or min(cd,nd,cc,nc)<0: raise ValueError("reports require non-negative numeric DPS and total_cost_gp")
 delta=nd-cd; cost=nc-cc; cw=current.get("weapon",{}); nw=candidate.get("weapon",{})
 return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"baseline_comparison_only","current":{"status":current.get("status"),"attack_style":current.get("attack_style"),"dps":cd,"cost_gp":cc,"weapon":cw,"items":current.get("selected_items",[])},"candidate":{"status":candidate.get("status"),"attack_style":candidate.get("attack_style"),"dps":nd,"cost_gp":nc,"weapon":nw,"items":candidate.get("selected_items",[])},"delta":{"dps":round(delta,8),"dps_percent":round(delta/cd*100,4) if cd else None,"cost_gp":cost,"additional_gp_per_dps":round(cost/delta,4) if delta>0 else None,"improved_baseline_dps":delta>0,"cheaper":cost<0},"comparability":{"same_attack_style":current.get("attack_style")==candidate.get("attack_style"),"same_weapon_speed":cw.get("attack_speed_ticks")==nw.get("attack_speed_ticks"),"assumptions_match_not_proven":False},"warnings":["Use identical target, combat inputs, formula version and mechanics for a valid comparison; this tool cannot prove assumptions match.","Baseline DPS omits unmodelled boss mechanics, boosts, prayers, ammunition and supply costs.","This compares supplied reports; it is not a loadout optimiser."]}
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--current",required=True); p.add_argument("--candidate",required=True); p.add_argument("--output",default=str(REPORTS/"loadout-comparison.json")); a=p.parse_args()
 try:
  load=lambda x:json.loads(Path(x).read_text(encoding="utf-8")); result=compare_reports(load(a.current),load(a.candidate))
 except (OSError,json.JSONDecodeError,ValueError) as e: print(json.dumps({"status":"failed","error":str(e)},indent=2)); return 1
 out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
