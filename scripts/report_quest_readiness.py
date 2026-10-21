#!/usr/bin/env python3
"""Report quest dataset completeness without overstating factual readiness."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DIST=ROOT/"dist"; REPORTS=ROOT/"reports"
def build_report(quests,relationships,import_report,relationship_report):
    errors=[]; warnings=[]
    if not isinstance(quests,list): errors.append("Quest dataset must be a JSON array"); quests=[]
    if not isinstance(relationships,list): errors.append("Quest relationship dataset must be a JSON array"); relationships=[]
    if not isinstance(import_report,dict): errors.append("Quest import report missing or malformed"); import_report={}
    if not isinstance(relationship_report,dict): errors.append("Quest relationship report missing or malformed"); relationship_report={}
    names=set(); duplicates=0; source=prereqs=skills=rewards=0
    for i,row in enumerate(quests):
        if not isinstance(row,dict) or not isinstance(row.get("name"),str) or not row["name"].strip():
            errors.append(f"Invalid quest record at index {i}"); continue
        name=" ".join(row["name"].casefold().split())
        if name in names: duplicates+=1
        names.add(name); source+=bool(row.get("source_url")); prereqs+=bool(row.get("requirements")); skills+=bool(row.get("skill_requirements")); rewards+=bool(row.get("rewards"))
    total=len(quests)
    if not total: warnings.append("No quest fact records imported; title catalogue is not a quest-fact database")
    if total and source<total: warnings.append(f"{total-source} quests lack a source URL")
    if total and prereqs<total: warnings.append(f"{total-prereqs} quests have no recorded quest prerequisites; verify whether truly none or unknown")
    if total and skills<total: warnings.append(f"{total-skills} quests have no recorded skill requirements; verify whether truly none or unknown")
    if total and rewards<total: warnings.append(f"{total-rewards} quests have no recorded rewards")
    unresolved=relationship_report.get("unresolved_requirement_count",0)
    if isinstance(unresolved,int) and unresolved: warnings.append(f"{unresolved} quest prerequisite references remain unresolved")
    if duplicates: warnings.append(f"{duplicates} duplicate normalized quest names")
    if import_report.get("status")=="missing_source": warnings.append("Quest source adapter has no supplied fact snapshot")
    status="failed" if errors or relationship_report.get("status")=="failed" else "incomplete" if warnings else "review_required"
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":status,"quest_count":total,"quests_with_source_url":source,"quests_with_requirements":prereqs,"quests_with_skill_requirements":skills,"quests_with_rewards":rewards,"duplicate_name_count":duplicates,"relationship_count":len(relationships),"unresolved_requirement_count":unresolved,"warnings":warnings,"errors":errors,"import_status":import_report.get("status"),"relationship_status":relationship_report.get("status"),"interpretation":"A structurally complete record is not automatically verified. Missing values are unknown until source review establishes otherwise."}
def main():
    def load(path,default):
        try:return json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError):return default
    result=build_report(load(DIST/"quests.json",[]),load(DIST/"quest-relationships.json",[]),load(REPORTS/"quest-coverage.json",{}),load(REPORTS/"quest-relationship-coverage.json",{}))
    REPORTS.mkdir(parents=True,exist_ok=True); (REPORTS/"quest-readiness.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 1 if result["status"]=="failed" else 0
if __name__=="__main__": raise SystemExit(main())
