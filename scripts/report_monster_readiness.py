#!/usr/bin/env python3
"""Rank monster records by explicit field coverage to prioritize data cleanup."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
CRITICAL=("id","name","combat_level","hitpoints","attack_level","strength_level","defence_level","attack_speed","max_hit","sources")
def present(v:Any)->bool: return v is not None and v!="" and v!=[] and v!={}
def report(rows:list[dict[str,Any]])->dict[str,Any]:
    details=[]; missing_counts={k:0 for k in CRITICAL}
    for row in rows:
        missing=[k for k in CRITICAL if not present(row.get(k))]
        for k in missing: missing_counts[k]+=1
        count=len(CRITICAL)-len(missing)
        details.append({"id":row.get("id"),"name":row.get("name",""),"present_critical_fields":count,
          "critical_field_count":len(CRITICAL),"field_presence_percent":round(100*count/len(CRITICAL),2),
          "missing_critical_fields":missing,"readiness_band":"high_presence" if count>=9 else ("medium_presence" if count>=6 else "low_presence")})
    details.sort(key=lambda x:(x["field_presence_percent"],str(x["name"]).casefold(),str(x["id"])))
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"passed","record_count":len(rows),
      "critical_fields":list(CRITICAL),"field_missing_counts":missing_counts,
      "readiness_band_counts":{k:sum(1 for r in details if r["readiness_band"]==k) for k in ("high_presence","medium_presence","low_presence")},
      "lowest_presence_records":details[:200],"highest_presence_records":list(reversed(details[-200:])),
      "detail_limit_per_end":200,
      "definition":"Presence-only triage score over a fixed set of identity/combat/source fields; not an accuracy, combat difficulty, or readiness guarantee.",
      "guardrails":["Unknowns are not repaired or imputed.","Critical-field selection is a pipeline triage policy, not an official OSRS schema.","High field presence does not mean mechanics are source-verified."]}
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--input",type=Path,default=ROOT/"dist/monsters-combat.json"); p.add_argument("--output",type=Path,default=ROOT/"reports/monster-readiness.json"); a=p.parse_args()
    try:
        rows=json.loads(a.input.read_text(encoding="utf-8"))
        if not isinstance(rows,list) or any(not isinstance(x,dict) for x in rows): raise ValueError("input must be an array of objects")
    except (OSError,json.JSONDecodeError,ValueError) as e:p.error(str(e))
    r=report(rows); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"record_count":r["record_count"],"readiness_band_counts":r["readiness_band_counts"]},indent=2)); return 0
if __name__=="__main__":raise SystemExit(main())
