#!/usr/bin/env python3
"""Summarize quest and item unlock evidence without inferring unknown prerequisites."""
from __future__ import annotations
import argparse, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"; REPORTS=ROOT/"reports"

def load(path, required=True):
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required: raise ValueError(f"Required input missing: {path}")
        return None
    except json.JSONDecodeError as exc: raise ValueError(f"Invalid JSON {path}: {exc}") from exc
    return value

def status_counts(rows, field):
    counts=Counter()
    for row in rows:
        value=row.get(field)
        counts[value if isinstance(value,str) and value else "unspecified"]+=1
    return dict(sorted(counts.items()))

def summarize_quest_records(quests):
    out={"record_count":len(quests),"unique_key_count":0,"duplicate_keys":[],"requirement_state_counts":{},
         "requirement_source_coverage_percent":0.0,"reward_state_counts":{},"reward_source_coverage_percent":0.0,
         "unknown_requirement_samples":[],"unknown_reward_samples":[]}
    keys=[]; req_sources=reward_sources=0
    for q in quests:
        key=q.get("key")
        if isinstance(key,str) and key.strip(): keys.append(key)
        fs=q.get("field_status") if isinstance(q.get("field_status"),dict) else {}
        src=q.get("field_sources") if isinstance(q.get("field_sources"),dict) else {}
        req_state=fs.get("requirements","unspecified")
        reward_state=fs.get("rewards","unspecified")
        out["requirement_state_counts"][req_state]=out["requirement_state_counts"].get(req_state,0)+1
        out["reward_state_counts"][reward_state]=out["reward_state_counts"].get(reward_state,0)+1
        if isinstance(src.get("requirements"),str) and src["requirements"].startswith("https://"): req_sources+=1
        if isinstance(src.get("rewards"),str) and src["rewards"].startswith("https://"): reward_sources+=1
        if req_state not in ("known","known_empty") and len(out["unknown_requirement_samples"])<30:
            out["unknown_requirement_samples"].append({"key":key,"name":q.get("name"),"state":req_state})
        if reward_state not in ("known","known_empty") and len(out["unknown_reward_samples"])<30:
            out["unknown_reward_samples"].append({"key":key,"name":q.get("name"),"state":reward_state})
    duplicates=sorted(k for k,c in Counter(keys).items() if c>1)
    out["unique_key_count"]=len(set(keys)); out["duplicate_keys"]=duplicates[:100]
    n=len(quests)
    out["requirement_source_coverage_percent"]=round(100*req_sources/n,2) if n else 0.0
    out["reward_source_coverage_percent"]=round(100*reward_sources/n,2) if n else 0.0
    return out

def summarize_item_unlocks(records, items):
    counts=Counter(); bad_ids=[]; duplicate_ids=[]; seen=set(); sourced=0; evidence_gaps=0
    for row in records:
        iid=row.get("item_id")
        if isinstance(iid,bool) or not isinstance(iid,int) or iid<0: bad_ids.append(iid)
        elif iid in seen: duplicate_ids.append(iid)
        seen.add(iid)
        state=row.get("requirements_status","unspecified"); counts[state]+=1
        url=row.get("source_url")
        if isinstance(url,str) and url.startswith("https://"): sourced+=1
        else: evidence_gaps+=1
    item_ids={r.get("id") for r in items if isinstance(r.get("id"),int) and not isinstance(r.get("id"),bool)}
    linked={r.get("item_id") for r in records if isinstance(r.get("item_id"),int) and not isinstance(r.get("item_id"),bool)}
    return {"record_count":len(records),"knowledge_state_counts":dict(sorted(counts.items())),
            "unique_item_id_count":len(seen),"duplicate_item_id_count":len(set(duplicate_ids)),
            "invalid_item_id_count":len(bad_ids),"items_without_unlock_record_count":len(item_ids-linked),
            "unlock_records_without_item_count":len(linked-item_ids),"source_url_coverage_percent":round(100*sourced/len(records),2) if records else 0.0,
            "records_without_source_url_count":evidence_gaps,"duplicate_item_id_samples":sorted(set(duplicate_ids))[:50],
            "invalid_item_id_samples":bad_ids[:50]}

def summarize_relationships(rows, quests):
    keys={r.get("key") for r in quests if isinstance(r.get("key"),str)}
    seen=set(); duplicates=[]; unresolved=Counter(); edges=0; source_linked=0; samples=[]
    for row in rows:
        key=row.get("quest_key")
        if not isinstance(key,str) or not key.strip(): continue
        if key in seen: duplicates.append(key)
        seen.add(key)
        prereqs=row.get("prerequisites")
        if not isinstance(prereqs,list): prereqs=[]
        edges+=len(prereqs)
        if row.get("source_url") or row.get("source_urls"): source_linked+=1
        for p in prereqs:
            if not isinstance(p,dict): unresolved["malformed_prerequisite"]+=1; continue
            target=p.get("quest_key")
            if target not in keys:
                reason=p.get("resolution_status","unresolved_or_missing_target")
                unresolved[str(reason)]+=1
                if len(samples)<50: samples.append({"quest_key":key,"target":target,"resolution_status":reason})
    return {"record_count":len(rows),"unique_quest_key_count":len(seen),"duplicate_quest_key_count":len(set(duplicates)),
            "quest_keys_without_relationship_record_count":len(keys-seen),"orphan_quest_relationship_count":len(seen-keys),
            "prerequisite_edge_count":edges,"unresolved_prerequisite_counts":dict(sorted(unresolved.items())),
            "source_linked_record_count":source_linked,"source_link_coverage_percent":round(100*source_linked/len(rows),2) if rows else 0.0,
            "unresolved_samples":samples}

def build_report(quests, items, unlocks, relationships):
    quest=summarize_quest_records(quests); item=summarize_item_unlocks(unlocks,items); rel=summarize_relationships(relationships,quests)
    issues=[]
    if quest["duplicate_keys"]: issues.append("duplicate_quest_keys")
    if item["duplicate_item_id_count"] or item["invalid_item_id_count"]: issues.append("invalid_or_duplicate_unlock_ids")
    if item["unlock_records_without_item_count"]: issues.append("orphan_unlock_records")
    if rel["duplicate_quest_key_count"] or rel["orphan_quest_relationship_count"]: issues.append("quest_relationship_identity_issues")
    if rel["unresolved_prerequisite_counts"]: issues.append("unresolved_prerequisite_edges")
    unknown_quests=sum(quest["requirement_state_counts"].get(s,0) for s in ("unknown","unspecified","candidate","review_required"))
    unknown_items=sum(item["knowledge_state_counts"].get(s,0) for s in ("unknown","unspecified","review_required"))
    status="review_required" if issues or unknown_quests or unknown_items else "passed"
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"schema_version":"1.0.0","status":status,
            "interpretation":"Evidence coverage and identity audit only. Unknown does not mean no requirement; a reward match does not prove an unlock.",
            "quest_requirements":quest,"item_unlock_evidence":item,"quest_relationships":rel,
            "review_queue":{"unknown_or_unspecified_quest_requirement_count":unknown_quests,
                            "unknown_or_unspecified_item_unlock_count":unknown_items,
                            "issue_categories":issues},
            "guardrails":["Do not infer no quest requirement from a blank, dash, or missing record.",
                          "Quest reward text matching an item name is not proof of permanent unlock or equipment eligibility.",
                          "Quest prerequisite names that are ambiguous or unresolved remain unresolved.",
                          "Source URL presence is not independent verification of the source's contents.",
                          "This report measures generated records only; it does not fetch or invent external facts."]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--quests",type=Path,default=DIST/"quests.json")
    p.add_argument("--items",type=Path,default=DIST/"items.json")
    p.add_argument("--item-unlocks",type=Path,default=DIST/"item-quest-unlocks.json")
    p.add_argument("--quest-relationships",type=Path,default=DIST/"quest-relationships.json")
    p.add_argument("--output",type=Path,default=REPORTS/"quest-unlock-coverage.json")
    a=p.parse_args()
    data=[load(a.quests),load(a.items),load(a.item_unlocks,required=False) or [],load(a.quest_relationships)]
    report=build_report(*data); a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Quest/unlock evidence coverage: {report['status']} (unknown quest requirements={report['review_queue']['unknown_or_unspecified_quest_requirement_count']}, unknown item unlocks={report['review_queue']['unknown_or_unspecified_item_unlock_count']})")
if __name__=="__main__": main()
