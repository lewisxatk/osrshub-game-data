#!/usr/bin/env python3
"""Smoke-test the data bundle's minimum consumer contract without claiming combat correctness."""
import argparse,json
from pathlib import Path
from build_combat_studio_v1_bundle_manifest import build_manifest,FILES
def smoke(dist):
 manifest=build_manifest(dist);checks=[]
 for name,spec in FILES.items():
  row=manifest["datasets"][name];checks.append({"check":"artifact_available","file":name,"passed":row["state"] in ("ready","review_required"),"state":row["state"]})
  if row["state"] in ("ready","review_required"):
   try:data=json.loads((dist/name).read_text(encoding="utf-8"))
   except (OSError,json.JSONDecodeError):data=[]
   keys={k for item in data if isinstance(item,dict) for k in item}
   checks.append({"check":"identity_field_declared","file":name,"field":spec["identity"],"passed":not data or spec["identity"] in keys})
   checks.append({"check":"records_nonempty","file":name,"record_count":len(data),"passed":len(data)>0})
  else:
   checks.append({"check":"identity_field_declared","file":name,"field":spec["identity"],"passed":False})
 passed=sum(c["passed"] for c in checks)
 failed=[c for c in checks if not c["passed"]]
 return {"schema_version":"1.0.0","status":"passed_structural_smoke" if not failed else "review_required","checks_run":len(checks),"checks_passed":passed,"checks_failed":len(failed),"checks":checks,"failures":failed,"interpretation":"Checks file readability, non-empty records and declared identity-field presence only. It does not validate field semantics, source facts, combat formula accuracy, eligibility, or actual website import.","guardrails":["A passed smoke test is not a production acceptance test.","Empty or missing datasets are visible failures.","Unknown values must remain unknown and must not be coerced to zero."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--dist-dir",type=Path,default=Path(__file__).resolve().parents[1]/"dist");p.add_argument("--output",type=Path,default=Path(__file__).resolve().parents[1]/"reports/combat-studio-consumer-smoke.json");a=p.parse_args();r=smoke(a.dist_dir);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8");print(f"Consumer bundle smoke test: {r['status']} ({r['checks_passed']}/{r['checks_run']} checks)");raise SystemExit(1 if r["checks_failed"] else 0)
if __name__=="__main__":main()
