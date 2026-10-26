#!/usr/bin/env python3
"""Measure field coverage and explicit-ID joins in generated OSRS datasets."""
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPECS={"items":("items.json","id",["name"]),"equipment":("equipment-stats.json","id",["attack_stab","attack_slash","attack_crush","attack_magic","attack_ranged"]),"weapons":("weapons.json","id",["attack_speed"]),"profiles":("item-combat-profiles.json","id",["attack_stab","attack_slash","attack_crush","attack_magic","attack_ranged"]),"requirements":("item-requirements.json","item_id",[]),"monsters":("monsters-combat.json","id",["hitpoints","combat_level","max_hit"]),"quests":("quests.json","key",["name"]),"quest_links":("quest-relationships.json","quest_key",[]),"item_links":("item-relationships.json","item_id",[])}
EDGES=[("items","equipment","equipment"),("items","weapons","weapons"),("items","profiles","combat_profiles"),("items","requirements","requirements"),("items","item_links","item_relationships"),("quests","quest_links","quest_prerequisites")]
def load(p):
 try:d=json.loads(p.read_text(encoding="utf-8"))
 except FileNotFoundError:return None,"missing_file"
 except (OSError,json.JSONDecodeError):return None,"invalid_json"
 return (d,None) if isinstance(d,list) and all(isinstance(x,dict) for x in d) else (None,"invalid_shape")
def build_report(root):
 data={};rows={};gaps=[];errors=[]
 for n,(fn,key,fields) in SPECS.items():
  r,e=load(root/fn);rows[n]=r
  if e:data[n]={"file":fn,"state":e,"record_count":None,"missing_id_count":None,"duplicate_id_count":None,"field_coverage_percent":None};errors.append({"dataset":n,"issue":e});continue
  ids=[str(x[key]) for x in r if x.get(key) not in (None,"")];missing=sum(x.get(key) in (None,"") for x in r);dups=sum(c-1 for c in Counter(ids).values() if c>1)
  good=sum(all(x.get(f) is not None and (not isinstance(x.get(f),str) or x[f].strip()) for f in fields) for x in r);cov=round(100*good/len(r),2) if r else 0.0
  data[n]={"file":fn,"state":"available","record_count":len(r),"unique_id_count":len(set(ids)),"missing_id_count":missing,"duplicate_id_count":dups,"field_coverage_percent":cov,"fields_checked":fields}
  if missing or dups:gaps.append({"priority":"high","dataset":n,"gap":"identity_integrity","missing_ids":missing,"duplicate_ids":dups})
  if cov<100:gaps.append({"priority":"high" if n in ("equipment","profiles","monsters") else "medium","dataset":n,"gap":"field_coverage","coverage_percent":cov,"records_missing_fields":len(r)-good})
 edges=[]
 for s,t,label in EDGES:
  if data[s]["state"]!="available" or data[t]["state"]!="available":edges.append({"relationship":label,"state":"not_assessed","source":s,"target":t,"coverage_percent":None});gaps.append({"priority":"high","dataset":s,"gap":"relationship_not_assessed","relationship":label});continue
  a={str(x[SPECS[s][1]]) for x in rows[s] if x.get(SPECS[s][1]) not in (None,"")};b={str(x[SPECS[t][1]]) for x in rows[t] if x.get(SPECS[t][1]) not in (None,"")};m=a-b;o=b-a
  edges.append({"relationship":label,"state":"assessed","source":s,"target":t,"source_count":len(a),"target_count":len(b),"linked_count":len(a&b),"unlinked_source_count":len(m),"orphan_target_count":len(o),"coverage_percent":round(100*len(a&b)/len(a),2) if a else 0.0,"unlinked_samples":sorted(m)[:20],"orphan_samples":sorted(o)[:20]})
  if m or o:gaps.append({"priority":"high" if label in ("equipment","weapons","combat_profiles") else "medium","dataset":s,"gap":"relationship_coverage","relationship":label,"unlinked_source_count":len(m),"orphan_target_count":len(o)})
 return {"generated_at":datetime.now(timezone.utc).isoformat(),"schema_version":"1.0.0","status":"review_required" if errors or gaps else "passed","interpretation":"Field presence and shared IDs measure structure only, not factual accuracy or verified combat rules.","dataset_count":len(data),"available_dataset_count":sum(x["state"]=="available" for x in data.values()),"datasets":data,"relationships":edges,"priority_gap_count":len(gaps),"priority_gaps":gaps[:500],"input_errors":errors,"guardrails":["Missing datasets are not treated as empty.","ID joins do not prove unlock eligibility.","Unknown values are never filled with guesses.","Coverage is not correctness or complete OSRS coverage."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--dist-dir",type=Path,default=ROOT/"dist");p.add_argument("--output",type=Path,default=ROOT/"reports/combat-studio-readiness-matrix.json");a=p.parse_args();r=build_report(a.dist_dir);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8");print(f"Readiness matrix: {r['status']} ({r['available_dataset_count']}/{r['dataset_count']} datasets; {r['priority_gap_count']} gaps)")
if __name__=="__main__":main()
