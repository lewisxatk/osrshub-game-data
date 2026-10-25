#!/usr/bin/env python3
"""Show how constant-DPS TTK estimates change under explicit DPS multipliers."""
from __future__ import annotations
import argparse,json,math
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MULTIPLIERS=(0.5,0.75,0.9,1.0,1.1,1.25,1.5)
def analyze(scenarios,monsters):
    by_id={r.get("id"):r for r in monsters if isinstance(r.get("id"),int) and not isinstance(r.get("id"),bool)}
    results=[]
    for s in scenarios:
        sid=s.get("scenario_id"); dps=s.get("player_dps")
        if not isinstance(sid,str) or not sid.strip(): raise ValueError("scenario_id must be non-empty")
        if isinstance(dps,bool) or not isinstance(dps,(int,float)) or not math.isfinite(dps) or dps<=0: raise ValueError(f"{sid}: player_dps must be finite and positive")
        hp=s.get("target_hitpoints"); source="explicit_scenario_hitpoints"; mid=s.get("monster_id"); name=s.get("target_name","Scenario target")
        if mid is not None:
            if isinstance(mid,bool) or not isinstance(mid,int) or mid<0: raise ValueError(f"{sid}: invalid monster_id")
            monster=by_id.get(mid)
            if monster is None:
                results.append({"scenario_id":sid,"status":"unknown_monster_id","monster_id":mid,"target_name":name,"base_player_dps":dps,"hitpoints":None,"sensitivity":[]}); continue
            name=monster.get("name","")
            hp=monster.get("hitpoints"); source="dist/monsters-combat.json"
        if isinstance(hp,bool) or not isinstance(hp,(int,float)) or not math.isfinite(hp) or hp<=0:
            results.append({"scenario_id":sid,"status":"missing_positive_hitpoints","monster_id":mid,"target_name":name,"base_player_dps":dps,"hitpoints":None,"sensitivity":[]}); continue
        curve=[]
        for mult in MULTIPLIERS:
            adjusted=dps*mult; seconds=hp/adjusted
            curve.append({"dps_multiplier":mult,"player_dps":round(adjusted,6),"time_to_kill_seconds":round(seconds,3),"time_to_kill_ticks":round(seconds/0.6,3)})
        results.append({"scenario_id":sid,"status":"estimated","monster_id":mid,"target_name":name,"base_player_dps":dps,"hitpoints":hp,"hitpoints_source":source,"sensitivity":curve})
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"passed" if results and all(x["status"]=="estimated" for x in results) else ("partial" if results else "empty"),
      "scenario_count":len(results),"multipliers":list(MULTIPLIERS),"results":results,
      "guardrails":["This is a constant-DPS sensitivity analysis, not a damage-roll simulator.",
       "DPS is supplied explicitly and is not calculated or inferred.","Unknown IDs never fall back to explicit scenario HP.",
       "Tick conversion uses 0.6 seconds per tick; phases, downtime, healing and movement are excluded."]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--input",type=Path,default=ROOT/"examples/monster-dps-scenarios.example.json");p.add_argument("--monsters",type=Path,default=ROOT/"dist/monsters-combat.json");p.add_argument("--output",type=Path,default=ROOT/"reports/monster-dps-sensitivity.json");a=p.parse_args()
    try:
        s=json.loads(a.input.read_text(encoding="utf-8"));m=json.loads(a.monsters.read_text(encoding="utf-8"))
        if not isinstance(s,list) or any(not isinstance(x,dict) for x in s):raise ValueError("scenarios must be an array of objects")
        if not isinstance(m,list) or any(not isinstance(x,dict) for x in m):raise ValueError("monsters must be an array of objects")
        r=analyze(s,m)
    except (OSError,json.JSONDecodeError,ValueError) as e:p.error(str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"scenario_count":r["scenario_count"]}));return 0
if __name__=="__main__":raise SystemExit(main())
