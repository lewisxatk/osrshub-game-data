#!/usr/bin/env python3
"""Search generated monster data with explicit name and numeric-field filters."""
from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def search(rows,query="",min_level=None,max_level=None,min_hp=None,max_hp=None,limit=50):
    if limit<1 or limit>500:raise ValueError("limit must be between 1 and 500")
    q=query.casefold().strip()
    out=[]
    for r in rows:
        name=r.get("name","")
        if q and q not in str(name).casefold():continue
        level=r.get("combat_level"); hp=r.get("hitpoints")
        if min_level is not None and (not isinstance(level,(int,float)) or isinstance(level,bool) or level<min_level):continue
        if max_level is not None and (not isinstance(level,(int,float)) or isinstance(level,bool) or level>max_level):continue
        if min_hp is not None and (not isinstance(hp,(int,float)) or isinstance(hp,bool) or hp<min_hp):continue
        if max_hp is not None and (not isinstance(hp,(int,float)) or isinstance(hp,bool) or hp>max_hp):continue
        out.append(r)
    out.sort(key=lambda r:(str(r.get("name","")).casefold(),r.get("id") if isinstance(r.get("id"),int) else -1))
    return {"status":"passed","query":query,"filters":{"min_combat_level":min_level,"max_combat_level":max_level,"min_hitpoints":min_hp,"max_hitpoints":max_hp},
      "match_count":len(out),"returned_count":min(limit,len(out)),"results":out[:limit],
      "guardrails":["Search is limited to the supplied generated snapshot.","Missing numeric values do not match numeric filters.","Results are sorted for reproducibility; no records are inferred."]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--input",type=Path,default=ROOT/"dist/monsters-combat.json");p.add_argument("--query",default="");p.add_argument("--min-level",type=float);p.add_argument("--max-level",type=float);p.add_argument("--min-hp",type=float);p.add_argument("--max-hp",type=float);p.add_argument("--limit",type=int,default=50);p.add_argument("--output",type=Path);a=p.parse_args()
    try:
        rows=json.loads(a.input.read_text(encoding="utf-8"))
        if not isinstance(rows,list) or any(not isinstance(x,dict) for x in rows):raise ValueError("input must be an array of objects")
        r=search(rows,a.query,a.min_level,a.max_level,a.min_hp,a.max_hp,a.limit)
    except (OSError,json.JSONDecodeError,ValueError) as e:p.error(str(e))
    rendered=json.dumps(r,indent=2)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered+"\n",encoding="utf-8")
    print(rendered);return 0
if __name__=="__main__":raise SystemExit(main())
