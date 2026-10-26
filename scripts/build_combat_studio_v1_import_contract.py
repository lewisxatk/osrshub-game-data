#!/usr/bin/env python3
"""Describe whether generated database artifacts meet the current Combat Studio V1 import contract."""
import argparse,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTRACT={
 "items.json":{"identity":"id","purpose":"canonical item identity","required":True},
 "equipment-stats.json":{"identity":"id","purpose":"equipment bonuses","required":True},
 "weapons.json":{"identity":"id","purpose":"weapon metadata and attack styles","required":True},
 "item-requirements.json":{"identity":"item_id","purpose":"item skill and other requirements","required":True},
 "item-combat-profiles.json":{"identity":"id","purpose":"joined item combat profile","required":True},
 "monsters-combat.json":{"identity":"id","purpose":"monster combat attributes","required":True},
 "quests.json":{"identity":"key","purpose":"quest identity and fact status","required":True},
 "quest-relationships.json":{"identity":"quest_key","purpose":"quest prerequisite graph","required":True},
 "item-relationships.json":{"identity":"item_id","purpose":"item relationship summary","required":True},
}
def inspect(path,contract):
 try:
  raw=path.read_bytes()
 except OSError as e:return {"file":path.name,"state":"missing","record_count":None,"sha256":None,"identity_field":contract["identity"],"missing_identity_count":None,"duplicate_identity_count":None,"errors":[str(e)]}
 digest=hashlib.sha256(raw).hexdigest()
 try:data=json.loads(raw.decode("utf-8"))
 except (UnicodeDecodeError,json.JSONDecodeError) as e:return {"file":path.name,"state":"invalid_json","record_count":None,"sha256":digest,"identity_field":contract["identity"],"missing_identity_count":None,"duplicate_identity_count":None,"errors":[str(e)]}
 if not isinstance(data,list) or any(not isinstance(row,dict) for row in data):
  return {"file":path.name,"state":"invalid_shape","record_count":None,"sha256":digest,"identity_field":contract["identity"],"missing_identity_count":None,"duplicate_identity_count":None,"errors":["Expected JSON array of objects"]}
 key=contract["identity"];ids=[];missing=0
 for row in data:
  value=row.get(key)
  if value is None or value=="" or (isinstance(value,str) and not value.strip()) or isinstance(value,bool):missing+=1
  else:ids.append(str(value))
 duplicate=len(ids)-len(set(ids))
 state="ready" if not missing and not duplicate and len(data)>0 else "review_required"
 return {"file":path.name,"state":state,"record_count":len(data),"sha256":digest,"identity_field":key,"missing_identity_count":missing,"duplicate_identity_count":duplicate,"errors":[]}
def build_report(dist_dir):
 datasets={name:inspect(dist_dir/name,spec) for name,spec in CONTRACT.items()}
 blockers=[];warnings=[]
 for name,row in datasets.items():
  if row["state"] in ("missing","invalid_json","invalid_shape"):blockers.append({"dataset":name,"reason":row["state"]})
  elif row["state"]=="review_required":warnings.append({"dataset":name,"reason":"empty_dataset_or_identity_integrity_issue","record_count":row["record_count"],"missing_identity_count":row["missing_identity_count"],"duplicate_identity_count":row["duplicate_identity_count"]})
 status="blocked" if blockers else "review_required" if warnings else "ready_for_consumer_smoke_test"
 return {"generated_at":datetime.now(timezone.utc).isoformat(),"schema_version":"1.0.0","contract_version":"combat-studio-v1-data-contract-1","status":status,"interpretation":"Artifact contract and identity integrity check only. Ready_for_consumer_smoke_test does not mean combat formulas are complete, facts are verified, or production import has been tested.","required_dataset_count":len(CONTRACT),"ready_dataset_count":sum(x["state"]=="ready" for x in datasets.values()),"datasets":datasets,"blocking_issues":blockers,"review_warnings":warnings,"consumer_contract":{"encoding":"UTF-8 JSON","root_type":"array of objects","identity_fields":{k:v["identity"] for k,v in CONTRACT.items()},"unknown_fields_policy":"Consumers must tolerate additive fields and must not convert unknown or missing mechanics into zero.","eligibility_policy":"Quest and item requirement evidence must be checked separately; presence of an item record alone does not establish account eligibility."},"guardrails":["This report does not change or copy production data.","A valid ID does not prove field-level factual accuracy.","A source URL is not independent fact verification.","No data is synthesized to make a dataset pass.","Production import still requires a consumer-side smoke test."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--dist-dir",type=Path,default=ROOT/"dist");p.add_argument("--output",type=Path,default=ROOT/"reports/combat-studio-v1-import-contract.json");a=p.parse_args();r=build_report(a.dist_dir);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(f"Combat Studio V1 import contract: {r['status']} ({r['ready_dataset_count']}/{r['required_dataset_count']} datasets identity-ready; blockers={len(r['blocking_issues'])}; warnings={len(r['review_warnings'])})")
if __name__=="__main__":main()
