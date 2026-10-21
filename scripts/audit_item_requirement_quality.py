#!/usr/bin/env python3
"""Audit requirement coverage and provenance without treating absence as proof."""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"; REPORTS=ROOT/"reports"
def audit_requirements(items,requirements):
    errors=[]; warnings=[]
    if not isinstance(items,list) or any(not isinstance(x,dict) for x in items):
        raise ValueError("items must be an array of objects")
    if not isinstance(requirements,list) or any(not isinstance(x,dict) for x in requirements):
        raise ValueError("requirements must be an array of objects")
    ids=[]
    for row in items:
        rid=row.get("id")
        if isinstance(rid,bool) or not isinstance(rid,int) or rid<0: errors.append(f"Invalid item ID: {rid!r}")
        else: ids.append(rid)
    duplicate_item_ids=[rid for rid,n in Counter(ids).items() if n>1]
    if duplicate_item_ids: errors.append("Duplicate item IDs: "+", ".join(map(str,duplicate_item_ids[:25])))
    item_ids=set(ids); by_id={}; malformed=[]; source_urls=0; source_names=0; entries=0
    for index,row in enumerate(requirements):
        rid=row.get("item_id")
        if isinstance(rid,bool) or not isinstance(rid,int) or rid<0:
            malformed.append({"index":index,"reason":"invalid_item_id"}); continue
        by_id.setdefault(rid,[]).append(row)
        reqs=row.get("requirements")
        if not isinstance(reqs,list):
            malformed.append({"index":index,"item_id":rid,"reason":"requirements_not_array"}); continue
        for j,req in enumerate(reqs):
            if not isinstance(req,dict) or not isinstance(req.get("skill"),str) or not req["skill"].strip() or isinstance(req.get("level"),bool) or not isinstance(req.get("level"),int) or req["level"]<0:
                malformed.append({"index":index,"item_id":rid,"requirement_index":j,"reason":"invalid_requirement_entry"})
            else: entries+=1
        if isinstance(row.get("source_url"),str) and row["source_url"].startswith("https://"): source_urls+=1
        sources=row.get("sources")
        if isinstance(sources,list) and any(isinstance(s,str) and s.strip() for s in sources): source_names+=1
    duplicate_requirement_ids=sorted(rid for rid,rows in by_id.items() if len(rows)>1)
    orphan_ids=sorted(set(by_id)-item_ids)
    items_with_records=len(set(by_id)&item_ids)
    missing=max(0,len(item_ids)-items_with_records)
    if missing: warnings.append(f"{missing} items have no normalized skill-requirement record; absence does not mean no requirement")
    if malformed: warnings.append(f"{len(malformed)} malformed requirement records or entries need review")
    if duplicate_requirement_ids: warnings.append(f"{len(duplicate_requirement_ids)} item IDs have multiple requirement records; inspect source conflicts")
    if orphan_ids: warnings.append(f"{len(orphan_ids)} requirement records reference IDs absent from the item dataset")
    if requirements and source_urls<len(requirements): warnings.append(f"{len(requirements)-source_urls} requirement records lack HTTPS source URLs")
    if requirements and source_names<len(requirements): warnings.append(f"{len(requirements)-source_names} requirement records lack source names")
    status="failed" if errors else "incomplete" if warnings else "review_required"
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":status,"item_count":len(items),"item_ids_unique":not duplicate_item_ids,"requirement_record_count":len(requirements),"items_with_requirement_record":items_with_records,"items_without_requirement_record":missing,"item_requirement_record_coverage_percent":round(100*items_with_records/len(item_ids),2) if item_ids else 0.0,"requirement_entry_count":entries,"records_with_https_source_url":source_urls,"records_with_source_name":source_names,"duplicate_requirement_item_ids":duplicate_requirement_ids,"orphan_requirement_item_ids":orphan_ids,"malformed_entries":malformed[:100],"errors":errors,"warnings":warnings,"guardrails":["Requirement-record coverage is not the same as full requirement completeness.","Items without records remain unknown; they must not be interpreted as having no skill or quest requirements.","Even sourced skill requirements do not establish quest, unlock, variant or account-mode eligibility."]}
def main():
    try:
        items=json.loads((DIST/"equipment-stats.json").read_text(encoding="utf-8"))
        requirements=json.loads((DIST/"item-requirements.json").read_text(encoding="utf-8"))
        result=audit_requirements(items,requirements)
    except (OSError,json.JSONDecodeError,ValueError) as exc:
        result={"generated_at":datetime.now(timezone.utc).isoformat(),"status":"failed","errors":[str(exc)],"warnings":[]}
    REPORTS.mkdir(parents=True,exist_ok=True)
    (REPORTS/"item-requirement-quality.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result["status"]=="failed" else 0
if __name__=="__main__":raise SystemExit(main())
