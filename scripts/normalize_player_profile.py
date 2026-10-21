#!/usr/bin/env python3
"""Normalize a manual or imported OSRS account profile without inventing missing data."""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKILLS=("Attack","Hitpoints","Mining","Strength","Agility","Smithing","Defence","Herblore","Fishing","Ranged","Thieving","Cooking","Prayer","Crafting","Firemaking","Magic","Fletching","Woodcutting","Runecraft","Slayer","Farming","Construction","Hunter")
def canon(s): return " ".join(s.casefold().split()) if isinstance(s,str) else ""
def normalize_profile(raw):
 if not isinstance(raw,dict): raise ValueError("profile root must be an object")
 errors=[]; warnings=[]; rawskills=raw.get("skills",{})
 if not isinstance(rawskills,dict): errors.append("skills must be an object"); rawskills={}
 known={canon(s):s for s in SKILLS}; skills={}; seen=set()
 for name,level in rawskills.items():
  k=canon(name)
  if k not in known: warnings.append(f"Unknown skill ignored: {name!r}"); continue
  if k in seen: errors.append(f"Duplicate skill after normalization: {name!r}"); continue
  seen.add(k)
  if isinstance(level,bool) or not isinstance(level,int) or not 1<=level<=99: errors.append(f"{known[k]} must be an integer from 1 to 99"); continue
  skills[known[k]]=level
 missing=[s for s in SKILLS if s not in skills]
 if missing: warnings.append("Partial account; missing skills: "+", ".join(missing))
 def strings(field):
  value=raw.get(field,[])
  if not isinstance(value,list): errors.append(f"{field} must be an array"); return []
  out=[]; used=set()
  for x in value:
   if not isinstance(x,str) or not x.strip(): errors.append(f"{field} entries must be non-empty strings"); continue
   k=canon(x)
   if k in used: warnings.append(f"Duplicate {field} entry ignored: {x!r}"); continue
   used.add(k); out.append(" ".join(x.split()))
  return out
 quests=strings("completed_quests"); excluded_names=strings("excluded_item_names")
 ids=raw.get("excluded_item_ids",[]); normalized_ids=[]
 if not isinstance(ids,list): errors.append("excluded_item_ids must be an array"); ids=[]
 for x in ids:
  if isinstance(x,bool) or not isinstance(x,int) or x<0: errors.append("excluded item IDs must be non-negative integers")
  elif x not in normalized_ids: normalized_ids.append(x)
 source=raw.get("source_url"); checked=raw.get("checked_on")
 if source is not None and (not isinstance(source,str) or not source.startswith(("https://","http://"))): errors.append("source_url must be HTTP(S)")
 if checked is not None and (not isinstance(checked,str) or len(checked)!=10 or checked[4:5]!="-" or checked[7:8]!="-"): errors.append("checked_on must use YYYY-MM-DD")
 if not source: warnings.append("Account source provenance missing")
 if not checked: warnings.append("Account freshness date missing")
 return {"label":raw.get("label","Imported account") if isinstance(raw.get("label","Imported account"),str) else "Imported account","skills":skills,"completed_quests":quests,"excluded_item_ids":sorted(normalized_ids),"excluded_item_names":excluded_names,"source_url":source if isinstance(source,str) else None,"checked_on":checked if isinstance(checked,str) else None,"profile_completeness":{"known_skill_count":len(skills),"total_skill_count":len(SKILLS),"missing_skills":missing,"complete":not missing},"import_status":"invalid" if errors else "partial" if warnings else "validated","errors":errors,"warnings":warnings}
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--input",required=True); p.add_argument("--output",default="reports/normalized-player-profile.json"); a=p.parse_args()
 try: result=normalize_profile(json.loads(Path(a.input).read_text(encoding="utf-8")))
 except (OSError,json.JSONDecodeError,ValueError) as e: print(json.dumps({"import_status":"invalid","errors":[str(e)]},indent=2)); return 1
 result["normalized_at"]=datetime.now(timezone.utc).isoformat(); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,ensure_ascii=False,indent=2)); return 1 if result["import_status"]=="invalid" else 0
if __name__=="__main__": raise SystemExit(main())
