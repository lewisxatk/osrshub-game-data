#!/usr/bin/env python3
"""Audit numeric ranges and source provenance in generated OSRS game datasets."""
from __future__ import annotations
import json, math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"
REPORTS=ROOT/"reports"
BONUS_FIELDS=("attack_stab","attack_slash","attack_crush","attack_magic","attack_ranged",
 "defence_stab","defence_slash","defence_crush","defence_magic","defence_ranged",
 "melee_strength","ranged_strength","magic_damage","prayer")
MONSTER_FIELDS=("combat_level","hitpoints","attack_level","strength_level","defence_level",
 "magic_level","ranged_level","attack_speed","max_hit","slayer_level","size")

def load_array(name):
 try: data=json.loads((DIST/name).read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as exc: raise ValueError(f"Cannot read dist/{name}: {exc}") from exc
 if not isinstance(data,list) or any(not isinstance(row,dict) for row in data):
  raise ValueError(f"dist/{name} must be an array of objects")
 return data

def numeric(value):
 if isinstance(value,bool) or value is None: return None
 if isinstance(value,(int,float)): return float(value) if math.isfinite(value) else None
 if isinstance(value,str):
  try:
   result=float(value.strip())
   return result if math.isfinite(result) else None
  except ValueError: return None
 return None

def valid_http_url(value):
 if not isinstance(value,str): return False
 try:
  p=urlparse(value)
  return p.scheme in ("http","https") and bool(p.netloc)
 except ValueError: return False

def audit_numeric_ranges(datasets):
 errors=[]; warnings=[]; checked={}
 def issue(target,index,row,kind,field=None,value=None,message=None):
  obj={"dataset":target,"index":index,"id":row.get("id"),"issue":kind}
  if field is not None: obj["field"]=field
  if value is not None: obj["value"]=value
  if message: obj["message"]=message
  (errors if kind.startswith("invalid_") or kind in ("duplicate_id","invalid_source_url") else warnings).append(obj)
 def check_ids(name,rows):
  seen=set()
  for i,row in enumerate(rows):
   rid=row.get("id")
   if isinstance(rid,bool) or not isinstance(rid,int) or rid<0: issue(name,i,row,"invalid_id","id",rid)
   elif rid in seen: issue(name,i,row,"duplicate_id","id",rid)
   seen.add(rid)
  checked[name]={"records":len(rows)}
 for name in ("items.json","equipment-stats.json","weapons.json","monsters-combat.json","item-combat-profiles.json"):
  check_ids(name,datasets[name])
 equipment=datasets["equipment-stats.json"]
 for i,row in enumerate(equipment):
  bonuses=row.get("bonuses")
  if not isinstance(bonuses,dict):
   issue("equipment-stats.json",i,row,"invalid_bonuses_object","bonuses",bonuses); continue
  for field in BONUS_FIELDS:
   if field not in bonuses or bonuses[field] is None or bonuses[field]=="": continue
   value=numeric(bonuses[field])
   if value is None: issue("equipment-stats.json",i,row,"invalid_bonus_number",field,bonuses[field])
   elif abs(value)>1000: issue("equipment-stats.json",i,row,"extreme_bonus_review",field,bonuses[field],"Outside a deliberately broad review threshold; verify source rather than auto-correcting.")
  sources=row.get("sources",[])
  if not isinstance(sources,list): issue("equipment-stats.json",i,row,"invalid_sources_list","sources",sources)
  elif not sources: issue("equipment-stats.json",i,row,"missing_source_provenance","sources",message="No source labels retained.",warning=True)
 weapons=datasets["weapons.json"]
 for i,row in enumerate(weapons):
  speed=row.get("attack_speed")
  if speed is not None and (isinstance(speed,bool) or not isinstance(speed,int) or speed<=0):
   issue("weapons.json",i,row,"invalid_attack_speed","attack_speed",speed)
  elif speed is not None and speed>20:
   issue("weapons.json",i,row,"attack_speed_review","attack_speed",speed,"Unusually high tick count; confirm source record.")
  if not row.get("source_url") and not row.get("sources"):
   issue("weapons.json",i,row,"missing_source_provenance","sources",message="No source URL or source labels retained.",warning=True)
 monsters=datasets["monsters-combat.json"]
 for i,row in enumerate(monsters):
  for field in MONSTER_FIELDS:
   if field not in row or row[field] is None: continue
   value=numeric(row[field])
   if value is None or value<0: issue("monsters-combat.json",i,row,"invalid_nonnegative_combat_field",field,row[field])
   elif field in ("combat_level","hitpoints","attack_level","strength_level","defence_level","magic_level","ranged_level","slayer_level","size") and value>100000:
    issue("monsters-combat.json",i,row,"combat_field_review",field,row[field],"Very large value; verify source.")
 for name,rows in datasets.items():
  for i,row in enumerate(rows):
   urls=[]
   if isinstance(row.get("source_url"),str) and row.get("source_url"): urls.append(row["source_url"])
   for key in ("source_urls","sources"):
    value=row.get(key)
    if isinstance(value,list): urls.extend(x for x in value if isinstance(x,str) and (x.startswith("http://") or x.startswith("https://")))
   for url in urls:
    if not valid_http_url(url): issue(name,i,row,"invalid_source_url","source_url",url)
 # Reclassify provenance absence as warnings regardless of the record type.
 for collection in (errors,warnings):
  for obj in collection:
   if obj["issue"]=="missing_source_provenance": obj["severity"]="warning"
 errors=[e for e in errors if e["issue"]!="missing_source_provenance"]
 return {"generated_at":datetime.now(timezone.utc).isoformat(),
  "status":"failed" if errors else ("review_required" if warnings else "passed"),
  "counts":{"datasets_checked":len(checked),"records_checked":sum(x["records"] for x in checked.values()),
   "error_count":len(errors),"warning_count":len(warnings)},
  "datasets":checked,"errors":errors[:300],"warnings":warnings[:300],
  "guardrails":["Range checks are anomaly detection, not proof of factual correctness.",
   "Extreme but parseable values are flagged for review, never silently clamped.",
   "Null combat values remain unknown and are not converted to zero.",
   "Only HTTP(S) source URLs are accepted as URLs; source labels alone are not URLs."]}

def main():
 names=("items.json","equipment-stats.json","weapons.json","monsters-combat.json","item-combat-profiles.json")
 try: report=audit_numeric_ranges({name:load_array(name) for name in names})
 except ValueError as exc:
  print(json.dumps({"status":"failed","error":str(exc)},indent=2)); return 1
 REPORTS.mkdir(parents=True,exist_ok=True)
 (REPORTS/"numeric-provenance-audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False,indent=2))
 return 1 if report["status"]=="failed" else 0

if __name__=="__main__": raise SystemExit(main())
