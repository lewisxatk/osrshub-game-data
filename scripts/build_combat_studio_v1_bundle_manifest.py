#!/usr/bin/env python3
"""Create a hash-pinned manifest for the generated Combat Studio V1 artifact bundle."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES={
 "items.json":{"identity":"id","role":"item_catalogue"},
 "equipment-stats.json":{"identity":"id","role":"equipment_bonuses"},
 "weapons.json":{"identity":"id","role":"weapon_metadata"},
 "item-requirements.json":{"identity":"item_id","role":"item_requirements"},
 "item-combat-profiles.json":{"identity":"id","role":"joined_combat_profiles"},
 "monsters-combat.json":{"identity":"id","role":"monster_combat"},
 "quests.json":{"identity":"key","role":"quest_catalogue"},
 "quest-relationships.json":{"identity":"quest_key","role":"quest_prerequisites"},
 "item-relationships.json":{"identity":"item_id","role":"item_relationships"}}
def inspect(path,identity):
 try:raw=path.read_bytes()
 except OSError as e:return {"state":"missing","record_count":None,"sha256":None,"identity_field":identity,"unique_identity_count":None,"duplicate_identity_count":None,"missing_identity_count":None,"error":str(e)}
 digest=hashlib.sha256(raw).hexdigest()
 try:data=json.loads(raw.decode("utf-8"))
 except (UnicodeDecodeError,json.JSONDecodeError) as e:return {"state":"invalid_json","record_count":None,"sha256":digest,"identity_field":identity,"unique_identity_count":None,"duplicate_identity_count":None,"missing_identity_count":None,"error":str(e)}
 if not isinstance(data,list) or any(not isinstance(x,dict) for x in data):return {"state":"invalid_shape","record_count":None,"sha256":digest,"identity_field":identity,"unique_identity_count":None,"duplicate_identity_count":None,"missing_identity_count":None,"error":"Expected array of objects"}
 ids=[];missing=0
 for row in data:
  v=row.get(identity)
  if v is None or v=="" or isinstance(v,bool) or (isinstance(v,str) and not v.strip()):missing+=1
  else:ids.append(str(v))
 dup=len(ids)-len(set(ids));state="ready" if data and not missing and not dup else "review_required"
 return {"state":state,"record_count":len(data),"sha256":digest,"identity_field":identity,"unique_identity_count":len(set(ids)),"duplicate_identity_count":dup,"missing_identity_count":missing,"error":None}
def build_manifest(dist):
 datasets={}
 for filename,spec in FILES.items():
  datasets[filename]={"role":spec["role"],**inspect(dist/filename,spec["identity"])}
 blocking=[{"file":f,"reason":v["state"]} for f,v in datasets.items() if v["state"] in ("missing","invalid_json","invalid_shape")]
 review=[{"file":f,"reason":"identity_or_empty_dataset","duplicate_identity_count":v["duplicate_identity_count"],"missing_identity_count":v["missing_identity_count"],"record_count":v["record_count"]} for f,v in datasets.items() if v["state"]=="review_required"]
 return {"schema_version":"1.0.0","contract_version":"combat-studio-v1-data-contract-1","generated_at":datetime.now(timezone.utc).isoformat(),"status":"blocked" if blocking else "review_required" if review else "bundle_integrity_passed","interpretation":"Hash-pinned artifact inventory and structural integrity report only; not factual verification, formula validation or consumer import acceptance.","bundle_root":"dist","file_count":len(datasets),"ready_file_count":sum(v["state"]=="ready" for v in datasets.values()),"datasets":datasets,"blocking_issues":blocking,"review_warnings":review,"consumer_rules":{"encoding":"UTF-8","root_shape":"JSON array of objects","additive_fields":"Consumers should ignore unknown additive fields unless explicitly versioned otherwise","unknown_values":"Do not coerce unknown or missing combat mechanics to zero","eligibility":"Use explicit requirements and quest evidence; item presence alone does not prove account eligibility"},"guardrails":["Hashes identify exact file contents and do not establish correctness.","Record counts across files must not be summed as unique OSRS entities.","No missing data is synthesized.","A clean manifest does not replace website consumer integration tests."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--dist-dir",type=Path,default=ROOT/"dist");p.add_argument("--output",type=Path,default=ROOT/"reports/combat-studio-v1-bundle-manifest.json");a=p.parse_args();r=build_manifest(a.dist_dir);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");print(f"Combat Studio V1 bundle manifest: {r['status']} ({r['ready_file_count']}/{r['file_count']} files clean)")
if __name__=="__main__":main()
