#!/usr/bin/env python3
"""Join census and quality outputs into a domain-level operational coverage matrix."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOMAIN_ACTIONS={
 "items":"Prioritize item identity, equipment links, requirements and combat profiles.",
 "combat":"Prioritize source-backed weapon mechanics, verified formulas and join completeness.",
 "quests":"Prioritize verified quest facts and prerequisite evidence; empty is unknown, not none.",
 "monsters":"Prioritize combat-stat provenance, drop links and target-specific evidence.",
 "world":"Prioritize explicit NPC/object/shop joins and provenance for source-backed facts.",
 "other":"Review prayers, Slayer tasks and remaining imported source domains.",
 "unclassified":"Classify this dataset and assign a source/consumer owner."
}
def build_matrix(census,quality,freshness=None):
    q={x["file"]:x for x in quality.get("datasets",[])}
    entries=[]
    for ds in census.get("datasets",[]):
        qr=q.get(ds["file"],{})
        entries.append({"file":ds["file"],"domain":ds.get("domain","unclassified"),
          "record_count":ds.get("record_count",0),"unique_identity_count":ds.get("unique_identity_count",0),
          "duplicate_identity_count":qr.get("duplicate_identity_count",ds.get("duplicate_identity_count",0)),
          "missing_identity_count":qr.get("missing_identity_count",ds.get("missing_identity_count",0)),
          "invalid_numeric_value_count":qr.get("invalid_numeric_value_count",0),
          "issue_count":qr.get("issue_count",0),"byte_size":ds.get("byte_size",0),
          "field_count":ds.get("field_count",0),"status":"review_required" if qr.get("issue_count",0) else ds.get("status","passed")})
    domains={}
    for domain in sorted({x["domain"] for x in entries}):
        rows=[x for x in entries if x["domain"]==domain]
        domains[domain]={"dataset_count":len(rows),"record_rows_across_files":sum(x["record_count"] for x in rows),
          "duplicate_identity_count":sum(x["duplicate_identity_count"] for x in rows),
          "missing_identity_count":sum(x["missing_identity_count"] for x in rows),
          "quality_issue_count":sum(x["issue_count"] for x in rows),
          "bytes":sum(x["byte_size"] for x in rows),"recommended_next_action":DOMAIN_ACTIONS.get(domain,DOMAIN_ACTIONS["unclassified"])}
    return {"generated_at":datetime.now(timezone.utc).isoformat(),"status":"review_required" if any(x["issue_count"] for x in entries) or not entries else "passed",
      "dataset_count":len(entries),"record_rows_across_files":sum(x["record_count"] for x in entries),
      "unique_identity_keys_within_files":sum(x["unique_identity_count"] for x in entries),
      "domain_count":len(domains),"domains":domains,"datasets":entries,
      "source_snapshot_status":(freshness or {}).get("status","not_supplied"),
      "interpretation":"This matrix prioritizes work by data domain. Record totals are summed rows and can double-count entities shared between files; unique identities are only unique within each individual file.",
      "guardrails":["Coverage and record counts are not factual accuracy measures.","Missing records are gaps, not evidence that a game fact does not exist.","Source snapshot status is copied from its report and does not independently verify source content."]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--census",type=Path,default=ROOT/"reports/database-census.json");p.add_argument("--quality",type=Path,default=ROOT/"reports/database-record-quality.json");p.add_argument("--freshness",type=Path,default=ROOT/"reports/source-snapshot-freshness.json");p.add_argument("--output",type=Path,default=ROOT/"reports/domain-coverage-matrix.json");a=p.parse_args()
    try:
        c=json.loads(a.census.read_text(encoding="utf-8"));q=json.loads(a.quality.read_text(encoding="utf-8"))
        f=json.loads(a.freshness.read_text(encoding="utf-8")) if a.freshness.exists() else {}
        r=build_matrix(c,q,f)
    except (OSError,json.JSONDecodeError,ValueError) as e:p.error(str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"dataset_count":r["dataset_count"],"record_rows_across_files":r["record_rows_across_files"],"domains":r["domains"]},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
