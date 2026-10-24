#!/usr/bin/env python3
"""Build a full fact-card catalogue from monster records without inventing missing fields."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def build_catalog(rows: list[dict[str,Any]]) -> dict[str,Any]:
    cards=[]
    for row in rows:
        known={k:v for k,v in row.items() if v is not None and v != "" and v != [] and v != {} and not k.startswith("_")}
        unknown=sorted(k for k,v in row.items() if (v is None or v == "") and not k.startswith("_"))
        cards.append({
            "id":row.get("id"),"name":row.get("name",""),"known_field_count":len(known),
            "known_fields":sorted(known),"unknown_fields":unknown,
            "sources":row.get("sources",[]),"record":row,
            "verification_status":"source-record-present_not_independently_verified",
        })
    cards.sort(key=lambda x:(str(x["name"]).casefold(), x["id"] if isinstance(x["id"],int) else -1))
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"passed",
      "source_dataset":"dist/monsters-combat.json","record_count":len(cards),"fact_cards":cards,
      "guardrails":["Each card copies an existing generated database record.",
       "Known fields indicate presence only, not factual accuracy.","Nulls and empty fields are not inferred.",
       "This catalogue does not calculate DPS, drop rates, weaknesses, or unlocks."]}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,default=ROOT/"dist/monsters-combat.json")
    p.add_argument("--output",type=Path,default=ROOT/"reports/monster-fact-catalog.json")
    a=p.parse_args()
    try:
        rows=json.loads(a.input.read_text(encoding="utf-8"))
        if not isinstance(rows,list) or any(not isinstance(x,dict) for x in rows): raise ValueError("input must be an array of objects")
    except (OSError,json.JSONDecodeError,ValueError) as e: p.error(str(e))
    result=build_catalog(rows); a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"record_count":result["record_count"]}))
    return 0
if __name__=="__main__": raise SystemExit(main())
