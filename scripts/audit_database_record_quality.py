#!/usr/bin/env python3
"""Find structural quality issues across generated datasets without silently repairing data."""
from __future__ import annotations
import argparse, json, math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IDENTITY_FIELDS={"items.json":"id","equipment-stats.json":"id","weapons.json":"id","monsters-combat.json":"id",
 "item-requirements.json":"item_id","item-combat-profiles.json":"id","item-relationships.json":"item_id",
 "quests.json":"key","quest-relationships.json":"quest_key","npc-drops.json":"npc_id","drop-subtables.json":"table_key",
 "shops-by-shop.json":"shop_name","shops-by-npc.json":"npc_id","slayer-tasks.json":"slayer_master_id",
 "npc-interactions.json":"source_key","npc-dialogues.json":"source_key","npcs-summary.json":"id",
 "objects-summary.json":"id","models-summary.json":"source_key","prayers.json":"id"}
NUMERIC_FIELDS={"id","item_id","npc_id","combat_level","hitpoints","attack_level","strength_level","defence_level",
 "attack_speed","max_hit","attack_bonus","strength_bonus","defence_bonus","ranged_level","magic_level"}
def audit_rows(rows, filename):
    key=IDENTITY_FIELDS.get(filename,"id"); seen=set(); dup=Counter(); issues=[]; blanks=0; invalid_numeric=0; source_missing=0
    field_counts=Counter()
    for i,row in enumerate(rows):
        for k,v in row.items():
            if v is not None and v!="" and v!=[] and v!={}: field_counts[k]+=1
        ident=row.get(key)
        if ident is None or ident=="": issues.append({"index":i,"kind":"missing_identity","field":key})
        elif isinstance(ident,bool) or not isinstance(ident,(str,int)) or (isinstance(ident,str) and not ident.strip()):
            issues.append({"index":i,"kind":"invalid_identity","field":key,"value":str(ident)[:80]})
        elif ident in seen: dup[str(ident)]+=1; issues.append({"index":i,"kind":"duplicate_identity","field":key,"value":str(ident)[:80]})
        else: seen.add(ident)
        if "name" in row and (not isinstance(row.get("name"),str) or not row.get("name","").strip()):
            blanks+=1; issues.append({"index":i,"kind":"blank_name"})
        for field in NUMERIC_FIELDS.intersection(row):
            value=row[field]
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0):
                invalid_numeric+=1; issues.append({"index":i,"kind":"invalid_numeric","field":field,"value":str(value)[:80]})
        src_fields=[k for k in row if "source" in k.casefold() or k.endswith("_url") or k.endswith("_urls")]
        if src_fields and not any(row.get(k) not in (None,"",[],{}) for k in src_fields):
            source_missing+=1
    count=len(rows)
    return {"file":filename,"record_count":count,"identity_field":key,"unique_identity_count":len(seen),
      "duplicate_identity_count":sum(dup.values()),"duplicate_identity_values":len(dup),
      "missing_identity_count":sum(x["kind"]=="missing_identity" for x in issues),
      "invalid_identity_count":sum(x["kind"]=="invalid_identity" for x in issues),
      "blank_name_count":blanks,"invalid_numeric_value_count":invalid_numeric,
      "records_with_source_fields_but_no_source_value":source_missing,
      "field_presence":{k:{"present_records":n,"coverage_percent":round(100*n/count,2) if count else 0.0} for k,n in sorted(field_counts.items())},
      "issue_count":len(issues),"issues":issues[:100]}
def audit_directory(directory:Path):
    reports=[]; unreadable=[]
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        try: data=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as e: unreadable.append({"file":path.name,"error":str(e)}); continue
        if isinstance(data,list):
            if all(isinstance(x,dict) for x in data): reports.append(audit_rows(data,path.name))
            else: unreadable.append({"file":path.name,"error":"array contains non-object rows"})
        elif isinstance(data,dict): reports.append(audit_rows([data],path.name))
        else: unreadable.append({"file":path.name,"error":"root must be an array or object"})
    issues=sum(x["issue_count"] for x in reports)
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"failed" if unreadable else "review_required" if issues else "passed",
      "dataset_count":len(reports),"total_record_rows":sum(x["record_count"] for x in reports),"issue_count":issues,
      "unreadable_file_count":len(unreadable),"unreadable_files":unreadable,"datasets":reports,
      "interpretation":"This is a structural review queue, not an accuracy score. Some records intentionally use nonnumeric keys; each file's identity field is configurable and source coverage is only checked when source-like fields exist.",
      "guardrails":["No records are modified, merged, or deleted.","Zero is a valid numeric value; booleans are not accepted as numeric stats.","Missing source metadata is reported as a review issue, not proof the fact is false.","Rows across datasets can represent the same underlying entity."]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--directory",type=Path,default=ROOT/"dist");p.add_argument("--output",type=Path,default=ROOT/"reports/database-record-quality.json");a=p.parse_args()
    r=audit_directory(a.directory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:r[k] for k in ("status","dataset_count","total_record_rows","issue_count","unreadable_file_count")},indent=2));return 1 if r["status"]=="failed" else 0
if __name__=="__main__":raise SystemExit(main())
