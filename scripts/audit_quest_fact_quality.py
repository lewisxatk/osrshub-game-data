#!/usr/bin/env python3
"""Audit quest fact coverage, explicit unknowns, and field-level source evidence.

This is a coverage/evidence report, not a factual verifier. A supplied field is
not automatically accurate; source URLs identify evidence to review.
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
FIELDS = ("requirements", "skill_requirements", "rewards", "members", "difficulty", "quest_type")
VALID_STATES = {"known", "unknown"}

def audit_quest_facts(quests, relationship_report=None):
    errors, warnings = [], []
    if not isinstance(quests, list):
        return {"status":"failed","quest_count":0,"errors":["Quest data must be an array"],"warnings":[],"fields":{}}
    relationship_report = relationship_report if isinstance(relationship_report, dict) else {}
    field_summary = {}
    duplicate_keys, duplicate_names = set(), set()
    keys, names = set(), set()
    for i, row in enumerate(quests):
        if not isinstance(row, dict):
            errors.append({"index":i,"issue":"record_not_object"})
            continue
        key, name = row.get("key"), row.get("name")
        if not isinstance(key, str) or not key.strip():
            errors.append({"index":i,"issue":"missing_quest_key"})
        elif key in keys:
            duplicate_keys.add(key)
        keys.add(key)
        normalized_name = " ".join(name.casefold().split()) if isinstance(name, str) else ""
        if not normalized_name:
            errors.append({"index":i,"issue":"missing_quest_name"})
        elif normalized_name in names:
            duplicate_names.add(normalized_name)
        names.add(normalized_name)
        states = row.get("field_status")
        if not isinstance(states, dict):
            warnings.append({"index":i,"issue":"field_status_missing","quest_key":key})
            states = {}
        sources = row.get("field_sources")
        if not isinstance(sources, dict):
            sources = {}
        for field in FIELDS:
            state = states.get(field)
            if state not in VALID_STATES:
                warnings.append({"index":i,"issue":"field_state_unknown_or_missing","quest_key":key,"field":field})
                state = "unknown"
            if state == "known":
                value = row.get(field)
                valid_empty = isinstance(value, list) and len(value) == 0
                if field in ("requirements","skill_requirements","rewards") and field not in row:
                    warnings.append({"index":i,"issue":"known_field_value_missing","quest_key":key,"field":field})
            source_url = sources.get(field)
            has_source = isinstance(source_url, str) and source_url.startswith("https://")
            if field not in field_summary:
                field_summary[field] = {"known_count":0,"unknown_count":0,"known_empty_count":0,"source_url_count":0,"known_without_field_source_count":0}
            bucket = field_summary[field]
            bucket[state + "_count"] += 1
            if state == "known" and field in ("requirements","skill_requirements","rewards") and isinstance(row.get(field), list) and not row[field]:
                bucket["known_empty_count"] += 1
            if has_source:
                bucket["source_url_count"] += 1
            elif state == "known":
                bucket["known_without_field_source_count"] += 1
    for key in duplicate_keys:
        errors.append({"issue":"duplicate_quest_key","quest_key":key})
    for name in duplicate_names:
        warnings.append({"issue":"duplicate_normalized_quest_name","normalized_name":name})
    unresolved = relationship_report.get("unresolved_requirement_count", 0)
    if not isinstance(unresolved, int) or isinstance(unresolved, bool) or unresolved < 0:
        warnings.append({"issue":"invalid_unresolved_requirement_count"})
        unresolved = None
    elif unresolved:
        warnings.append({"issue":"unresolved_prerequisite_references","count":unresolved})
    total = len(quests)
    if not total:
        warnings.append({"issue":"empty_quest_dataset","message":"No imported quest facts are available to assess."})
    for field, summary in field_summary.items():
        if summary["unknown_count"]:
            warnings.append({"issue":"field_coverage_gap","field":field,"unknown_count":summary["unknown_count"]})
        if summary["known_without_field_source_count"]:
            warnings.append({"issue":"known_facts_without_field_level_evidence","field":field,"count":summary["known_without_field_source_count"]})
    return {
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "status":"failed" if errors else "review_required" if warnings else "passed",
        "quest_count":total,
        "fields":field_summary,
        "duplicate_key_count":len(duplicate_keys),
        "duplicate_normalized_name_count":len(duplicate_names),
        "unresolved_prerequisite_reference_count":unresolved,
        "errors":errors[:500],
        "warnings":warnings[:500],
        "guardrails":[
            "Known means the source snapshot explicitly supplied a field, not that the fact is independently verified.",
            "Known-empty lists and unknown/missing fields are counted separately.",
            "Field-level source URLs are evidence pointers and still require review.",
            "This audit does not infer prerequisites, skill requirements, rewards, membership or unlocks."
        ]
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quests",type=Path,default=DIST/"quests.json")
    parser.add_argument("--relationships-report",type=Path,default=REPORTS/"quest-relationship-coverage.json")
    parser.add_argument("--output",type=Path,default=REPORTS/"quest-fact-quality.json")
    args=parser.parse_args()
    try:
        quests=json.loads(args.quests.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc:
        quests=None
        load_error=str(exc)
    else:
        load_error=None
    try:
        rel_report=json.loads(args.relationships_report.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):
        rel_report={}
    result=audit_quest_facts(quests,rel_report)
    if load_error:
        result["errors"].append({"issue":"quest_dataset_load_error","message":load_error})
        result["status"]="failed"
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 1 if result["status"]=="failed" else 0
if __name__=="__main__":
    raise SystemExit(main())
