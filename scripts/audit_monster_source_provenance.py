#!/usr/bin/env python3
"""Compare overlapping monster fields across raw snapshots without choosing a winner."""
from __future__ import annotations
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES={"community_monsters":ROOT/"sources/raw/community_monsters.json","original_monsters":ROOT/"sources/raw/original_monsters.json"}
ALIASES={"combat_level":("combat_level","combat","level"),"hitpoints":("hitpoints","hitpoints_level","hp"),
 "attack_level":("attack_level","attack"),"strength_level":("strength_level","strength"),
 "defence_level":("defence_level","defense_level","defence","defense"),
 "magic_level":("magic_level","magic"),"ranged_level":("ranged_level","range_level","ranged"),
 "attack_speed":("attack_speed","attackSpeed"),"max_hit":("max_hit","maxhit","maxHit")}
def rows_from(data):
    if isinstance(data,list):return [x for x in data if isinstance(x,dict)]
    if isinstance(data,dict):
        out=[]
        for key,value in data.items():
            if isinstance(value,dict):
                row=dict(value);row.setdefault("id",key);out.append(row)
        return out
    raise ValueError("source root must be an array or object")
def rid(row):
    for key in ("id","npc_id","monster_id"):
        try:
            if row.get(key) is not None:return int(row[key])
        except (TypeError,ValueError):pass
    return None
def value(row,aliases):
    for k in aliases:
        v=row.get(k)
        if isinstance(v,(int,float)) and not isinstance(v,bool) and v>=0:return v,k
    return None,None
def audit(source_data):
    indexed={}
    counts={}
    for source,raw in source_data.items():
        records=rows_from(raw);counts[source]=len(records);index={}
        for row in records:
            ident=rid(row)
            if ident is not None:index.setdefault(ident,[]).append(row)
        indexed[source]=index
    names=sorted(indexed)
    overlap=set(indexed[names[0]]) & set(indexed[names[1]]) if len(names)>=2 else set()
    comparisons=[];field_summary={k:{"both_present":0,"equal":0,"different":0,"one_missing":0} for k in ALIASES}
    for ident in sorted(overlap):
        left=indexed[names[0]][ident][0];right=indexed[names[1]][ident][0]
        for field,aliases in ALIASES.items():
            lv,la=value(left,aliases);rv,ra=value(right,aliases)
            summary=field_summary[field]
            if lv is None or rv is None:summary["one_missing"]+=1
            else:
                summary["both_present"]+=1
                if lv==rv:summary["equal"]+=1
                else:
                    summary["different"]+=1
                    comparisons.append({"id":ident,"name":left.get("name") or right.get("name") or "",
                      "field":field,"left_source":names[0],"left_field":la,"left_value":lv,
                      "right_source":names[1],"right_field":ra,"right_value":rv})
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"passed","source_record_counts":counts,
      "source_names":names,"overlapping_numeric_id_count":len(overlap),"field_summary":field_summary,
      "conflict_count":len(comparisons),"conflicts":comparisons[:1000],"conflict_detail_limit":1000,
      "guardrails":["Raw values are compared only where a non-negative numeric alias exists in both snapshots.",
       "This report does not decide which source is correct or overwrite normalized records.",
       "Only the first record per ID in each source participates; duplicate IDs require separate identity review.",
       "Field equality does not prove the mechanic or statistic is accurate."]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",type=Path,default=ROOT/"reports/monster-source-provenance-audit.json");a=p.parse_args()
    source_data={}
    try:
        for name,path in FILES.items():source_data[name]=json.loads(path.read_text(encoding="utf-8"))
        r=audit(source_data)
    except (OSError,json.JSONDecodeError,ValueError) as e:p.error(str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"overlapping_numeric_id_count":r["overlapping_numeric_id_count"],"conflict_count":r["conflict_count"]}));return 0
if __name__=="__main__":raise SystemExit(main())
