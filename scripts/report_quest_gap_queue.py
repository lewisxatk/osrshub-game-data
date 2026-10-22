#!/usr/bin/env python3
"""Prioritize missing quest facts and unresolved prerequisite evidence."""
import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DIST=ROOT/"dist";REPORTS=ROOT/"reports"
FIELDS=("requirements","skill_requirements","rewards","members","difficulty","quest_type")
def build_queue(quests,relationships_report,evidence_report):
 if not isinstance(quests,list):raise ValueError("quests must be an array")
 rel=relationships_report if isinstance(relationships_report,dict) else {}
 ev=evidence_report if isinstance(evidence_report,dict) else {}
 unresolved=rel.get("unresolved_requirement_count",0);unresolved=unresolved if isinstance(unresolved,int) and unresolved>=0 else 0
 evidence_count=ev.get("record_count",0);evidence_count=evidence_count if isinstance(evidence_count,int) and evidence_count>=0 else 0
 rows=[]
 for q in quests:
  if not isinstance(q,dict):continue
  states=q.get("field_status") if isinstance(q.get("field_status"),dict) else {}
  sources=q.get("field_sources") if isinstance(q.get("field_sources"),dict) else {}
  unknown=[f for f in FIELDS if states.get(f)!="known"]
  known_without_source=[f for f in FIELDS if states.get(f)=="known" and not (isinstance(sources.get(f),str) and sources[f].startswith("https://"))]
  evidence=q.get("requirement_evidence") if isinstance(q.get("requirement_evidence"),dict) else {}
  candidates=evidence.get("requirement_links",[]) if isinstance(evidence.get("requirement_links"),list) else []
  score=len(unknown)*10+len(known_without_source)*5+(3 if not q.get("source_url") else 0)+(2 if evidence else 0)
  if unknown or known_without_source or not q.get("source_url"):
   rows.append({"quest_key":q.get("key"),"quest_name":q.get("name"),"priority_score":score,"priority":"critical" if score>=50 else "high" if score>=35 else "medium" if score>=20 else "low","unknown_fields":unknown,"known_fields_without_field_source":known_without_source,"has_quest_source_url":bool(q.get("source_url")),"has_raw_requirement_evidence":bool(evidence),"raw_requirement_link_count":len(candidates),"next_action":"verify raw requirement evidence and populate structured fields" if evidence else "collect field-level source evidence and verify quest facts"})
 rows.sort(key=lambda x:(-x["priority_score"],str(x["quest_name"]).casefold()))
 return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"review_required" if rows or unresolved else "passed","quest_count":len(quests),"quests_with_gaps":len(rows),"unresolved_prerequisite_reference_count":unresolved,"raw_requirement_evidence_records":evidence_count,"prioritized_gaps":rows,"interpretation":"Priority is a work-order heuristic, not a measure of game accuracy. Candidate links and raw text are not treated as verified prerequisites."}
def main():
 REPORTS.mkdir(parents=True,exist_ok=True)
 try:
  quests=json.loads((DIST/"quests.json").read_text(encoding="utf-8"))
  rel=json.loads((REPORTS/"quest-relationship-coverage.json").read_text(encoding="utf-8"))
  ev=json.loads((REPORTS/"quest-requirement-evidence-coverage.json").read_text(encoding="utf-8"))
  result=build_queue(quests,rel,ev)
 except (OSError,json.JSONDecodeError,ValueError) as exc:
  result={"generated_at":datetime.now(timezone.utc).isoformat(),"status":"failed","quest_count":0,"quests_with_gaps":0,"unresolved_prerequisite_reference_count":None,"raw_requirement_evidence_records":0,"prioritized_gaps":[],"errors":[str(exc)]}
 (REPORTS/"quest-gap-queue.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if result["status"]=="failed" else 0
if __name__=="__main__":raise SystemExit(main())
