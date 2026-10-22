#!/usr/bin/env python3
"""Extract conservative, source-linked skill-level candidates from raw quest requirement text.

These are review candidates, not authoritative planner rules: text may describe a
requirement for starting or completing a quest, and boosts/other context are not inferred.
"""
from __future__ import annotations
import json,re,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"sources"/"raw"
REPORTS=ROOT/"reports"
SKILLS=("Attack","Strength","Defence","Ranged","Prayer","Magic","Runecraft","Hitpoints","Crafting","Mining","Smithing","Fishing","Cooking","Firemaking","Woodcutting","Agility","Herblore","Thieving","Fletching","Slayer","Farming","Construction","Hunter","Sailing")
# Deliberately strict: require a numeric level immediately followed by a known skill name.
PATTERN=re.compile(r"(?<![A-Za-z0-9])(?P<level>\d{1,2})\s+(?P<skill>"+ "|".join(re.escape(s) for s in sorted(SKILLS,key=len,reverse=True))+r")(?![A-Za-z])",re.I)
SOURCE="https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest"
def extract_candidates(records):
 if not isinstance(records,list): raise ValueError("quest evidence must be an array")
 output=[]; seen=set()
 for row in records:
  if not isinstance(row,dict): continue
  text=row.get("requirements_text")
  if not isinstance(text,str): continue
  for match in PATTERN.finditer(text):
   skill=next((s for s in SKILLS if s.casefold()==match.group("skill").casefold()),match.group("skill"))
   level=int(match.group("level"))
   if not 1<=level<=99: continue
   key=(str(row.get("quest_key","")),skill.casefold(),level,match.start())
   if key in seen: continue
   seen.add(key)
   output.append({"quest_key":str(row.get("quest_key","")),"quest_name":str(row.get("quest_name","")),"skill":skill,"level":level,"matched_text":match.group(0),"source_url":row.get("source_url") if isinstance(row.get("source_url"),str) else SOURCE,"catalogue_match_status":row.get("catalogue_match_status","unknown"),"candidate_status":"raw_text_candidate_needs_manual_review","interpretation_limits":["does_not_distinguish_starting_from_completion_requirement","does_not_infer_boostability","does_not_prove_source_context_or_currentness"]})
 return sorted(output,key=lambda x:(x["quest_name"].casefold(),x["skill"].casefold(),x["level"]))
def main():
 try:
  records=json.loads((RAW/"quest-requirement-evidence.json").read_text(encoding="utf-8"))
  candidates=extract_candidates(records)
 except (OSError,json.JSONDecodeError,ValueError) as exc:
  print("Quest skill candidate extraction failed: "+str(exc),file=sys.stderr);return 1
 RAW.mkdir(parents=True,exist_ok=True);REPORTS.mkdir(parents=True,exist_ok=True)
 (RAW/"quest-skill-requirement-candidates.json").write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 matched=sum(x["catalogue_match_status"]=="matched" for x in candidates)
 report={"generated_at":datetime.now(timezone.utc).isoformat(),"status":"review_required","source_url":SOURCE,"candidate_count":len(candidates),"matched_catalogue_candidates":matched,"unmatched_catalogue_candidates":len(candidates)-matched,"distinct_quests_with_candidates":len({x["quest_key"] for x in candidates}),"distinct_skills_found":sorted({x["skill"] for x in candidates}),"candidates":candidates,"not_claimed":["verified quest planner skill requirements","whether requirement is needed to start or complete","boostability","absence of requirements when no pattern matches"],"note":"Strict text matches are review candidates only. No candidate is silently promoted into the normalized quest dataset."}
 (REPORTS/"quest-skill-requirement-candidates.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({k:v for k,v in report.items() if k!="candidates"},ensure_ascii=False,indent=2))
 return 0
if __name__=="__main__":raise SystemExit(main())
