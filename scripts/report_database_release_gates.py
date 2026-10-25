#!/usr/bin/env python3
"""Turn inventory, quality and provenance reports into explicit non-destructive release gates."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={"items.json":"item identity","equipment-stats.json":"equipment statistics","weapons.json":"weapon facts",
 "item-requirements.json":"item requirements","item-combat-profiles.json":"joined combat profiles",
 "monsters-combat.json":"monster combat facts","quests.json":"quest catalogue","quest-relationships.json":"quest graph",
 "item-relationships.json":"item relationships","npc-drops.json":"NPC drop data","prayers.json":"prayer data"}
def gate(name,status,detail,blocking=False): return {"gate":name,"status":status,"detail":detail,"blocking":blocking}
def build_gates(census,quality,freshness,matrix):
    by_name={x["file"]:x for x in census.get("datasets",[])}
    q={x["file"]:x for x in quality.get("datasets",[])}
    gates=[]
    missing=[f for f in EXPECTED if f not in by_name]
    gates.append(gate("expected_dataset_inventory","blocked" if missing else "passed",
      "Missing expected generated datasets: "+", ".join(missing) if missing else "All configured core datasets are present.",bool(missing)))
    invalid=census.get("totals",{}).get("invalid_json_file_count",0)
    gates.append(gate("generated_json_integrity","blocked" if invalid else "passed",f"Invalid JSON files: {invalid}.",bool(invalid)))
    duplicates=sum(x.get("duplicate_identity_count",0) for x in q.values())
    invalid_ids=sum(x.get("invalid_identity_count",0) for x in q.values())
    numeric=sum(x.get("invalid_numeric_value_count",0) for x in q.values())
    gates.append(gate("identity_and_numeric_quality","review_required" if duplicates or invalid_ids or numeric else "passed",
      f"Duplicate identities: {duplicates}; invalid identities: {invalid_ids}; invalid numeric values: {numeric}.",False))
    missing_sources=freshness.get("metadata_entries_without_parseable_timestamp",0)
    snap_status=freshness.get("status","unknown")
    gates.append(gate("source_snapshot_provenance","review_required" if snap_status!="passed" else "passed",
      f"Snapshot report status: {snap_status}; metadata entries without parseable retrieval time: {missing_sources}.",False))
    empty=[name for name in ("quests.json","quest-relationships.json","monsters-combat.json","weapons.json") if name in by_name and by_name[name].get("record_count",0)==0]
    gates.append(gate("combat_and_quest_domain_presence","review_required" if empty else "passed",
      "Empty core datasets: "+", ".join(empty) if empty else "Core combat and quest datasets contain records.",False))
    issues=quality.get("issue_count",0)
    gates.append(gate("record_quality_review","review_required" if issues else "passed",f"Structural issues requiring review: {issues}.",False))
    gates.append(gate("domain_coverage_report","blocked" if not matrix.get("dataset_count") else "passed",
      "Domain matrix is present." if matrix.get("dataset_count") else "Domain matrix has no datasets.",not bool(matrix.get("dataset_count"))))
    blocking=[x for x in gates if x["blocking"] and x["status"]!="passed"]
    review=[x for x in gates if x["status"]=="review_required"]
    return {"generated_at":datetime.now(timezone.utc).isoformat(),
      "status":"blocked" if blocking else "review_required" if review else "passed",
      "release_decision":"do_not_promote" if blocking else "review_before_claiming_complete" if review else "structural_checks_passed",
      "gate_count":len(gates),"passed_gate_count":sum(x["status"]=="passed" for x in gates),
      "review_gate_count":len(review),"blocking_gate_count":len(blocking),"gates":gates,
      "next_actions":[x["detail"] for x in gates if x["status"]!="passed"],
      "guardrails":["This is a structural release checklist, not an OSRS fact-accuracy certificate.",
      "Review-required gates do not automatically fail CI; they make gaps visible.",
      "A passing status means only that these configured structural gates passed.",
      "Never promote unverified mechanics, inferred drop rates, or guessed quest unlocks on the strength of this report."]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--census",type=Path,default=ROOT/"reports/database-census.json");p.add_argument("--quality",type=Path,default=ROOT/"reports/database-record-quality.json");p.add_argument("--freshness",type=Path,default=ROOT/"reports/source-snapshot-freshness.json");p.add_argument("--matrix",type=Path,default=ROOT/"reports/domain-coverage-matrix.json");p.add_argument("--output",type=Path,default=ROOT/"reports/database-release-gates.json");a=p.parse_args()
    try: c,q,f,m=[json.loads(x.read_text(encoding="utf-8")) for x in (a.census,a.quality,a.freshness,a.matrix)];r=build_gates(c,q,f,m)
    except (OSError,json.JSONDecodeError,ValueError) as e:p.error(str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:r[k] for k in ("status","release_decision","gate_count","passed_gate_count","review_gate_count","blocking_gate_count","next_actions")},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
