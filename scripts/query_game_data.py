#!/usr/bin/env python3
"""Search generated OSRS Hub datasets, including quest dependencies and unlock references."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]; DIST=ROOT/"dist"
DATASETS={"items":"items.json","equipment-stats":"equipment-stats.json","weapons":"weapons.json","monsters":"monsters.json","monsters-combat":"monsters-combat.json","quests":"quests.json","quest-relationships":"quest-relationships.json","item-requirements":"item-requirements.json","item-relationships":"item-relationships.json"}
def get_field(value:Any,path:str)->Any:
    current=value
    for part in path.split("."):
        if not isinstance(current,dict) or part not in current:return None
        current=current[part]
    return current
def search_rows(rows,query=None,record_id=None,field=None,limit=20):
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=200: raise ValueError("limit must be between 1 and 200")
    needle=query.casefold().strip() if query else None; matches=[]
    for row in rows:
        if record_id is not None and row.get("id",row.get("item_id"))!=record_id:continue
        haystack=get_field(row,field) if field else row
        searchable=json.dumps(haystack,ensure_ascii=False,sort_keys=True,default=str).casefold()
        if needle and needle not in searchable:continue
        matches.append(row)
        if len(matches)>=limit:break
    return matches
def run_query(dataset,query=None,record_id=None,field=None,limit=20,dist_dir=DIST):
    if dataset not in DATASETS:return {"status":"failed","dataset":dataset,"error":"unsupported dataset","supported_datasets":sorted(DATASETS)}
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=200:return {"status":"failed","dataset":dataset,"error":"limit must be between 1 and 200"}
    if not query and record_id is None:return {"status":"failed","dataset":dataset,"error":"provide a search query and/or record ID"}
    path=dist_dir/DATASETS[dataset]
    try:data=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:return {"status":"unavailable","dataset":dataset,"record_count":None,"match_count":0,"results":[],"warning":f"Generated dataset {path.name} is not present. Run the pipeline first."}
    except (OSError,json.JSONDecodeError) as exc:return {"status":"failed","dataset":dataset,"error":f"cannot read {path.name}: {exc}"}
    if not isinstance(data,list) or any(not isinstance(row,dict) for row in data):return {"status":"failed","dataset":dataset,"error":f"{path.name} must contain a JSON array of objects"}
    matches=search_rows(data,query,record_id,field,limit)
    return {"status":"ok","dataset":dataset,"record_count":len(data),"match_count":len(matches),"truncated":len(matches)==limit,"results":matches,"warning":"Only facts present in this dataset are returned. Missing fields are unknown, not proof that a requirement or unlock does not exist."}
def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--dataset",required=True,choices=sorted(DATASETS)); parser.add_argument("--search"); parser.add_argument("--id",type=int); parser.add_argument("--field"); parser.add_argument("--limit",type=int,default=20); parser.add_argument("--compact",action="store_true")
    args=parser.parse_args()
    if not args.search and args.id is None:parser.error("provide --search and/or --id")
    if not 1<=args.limit<=200:parser.error("--limit must be between 1 and 200")
    result=run_query(args.dataset,args.search,args.id,args.field,args.limit)
    print(json.dumps(result,ensure_ascii=False,indent=None if args.compact else 2)); return 1 if result["status"]=="failed" else 0
if __name__=="__main__":raise SystemExit(main())
