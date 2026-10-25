#!/usr/bin/env python3
"""Audit quest evidence joins without promoting raw source text into planner facts."""
import argparse,json,sys,unicodedata
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/"sources"/"raw";REPORTS=ROOT/"reports"
SOURCE_HOST="oldschool.runescape.wiki";SOURCE_URL="https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest"
def canonical_title(value):
 value=unicodedata.normalize("NFKC",str(value or "")).replace("\u00a0"," ").replace("_"," ").replace("’","'").replace("‘","'").replace("＇","'")
 return " ".join(value.casefold().split())
def trusted_url(value):
 if not isinstance(value,str):return False
 try:
  p=urlparse(value)
  return p.scheme=="https" and p.hostname==SOURCE_HOST and p.port is None and p.username is None and p.password is None
 except ValueError:return False
def audit(evidence,catalogue):
 if not isinstance(evidence,list):raise ValueError("evidence must be a JSON array")
 if not isinstance(catalogue,list):raise ValueError("catalogue must be a JSON array")
 by_name={}
 for i,row in enumerate(catalogue):
  if not isinstance(row,dict) or not isinstance(row.get("name"),str) or not row["name"].strip():raise ValueError(f"catalogue record {i} has no usable name")
  norm=canonical_title(row["name"])
  if norm in by_name:raise ValueError("duplicate normalized catalogue title: "+row["name"])
  by_name[norm]=row
 errors=[];warnings=[];seen=defaultdict(list);matched=set();shapes=Counter();link_count=text_count=placeholder_count=0
 for i,row in enumerate(evidence):
  if not isinstance(row,dict):errors.append({"index":i,"reason":"record_not_object"});continue
  name=row.get("quest_name");norm=canonical_title(name)
  if not isinstance(name,str) or not norm:errors.append({"index":i,"reason":"missing_quest_name"});continue
  seen[norm].append(i);key=row.get("quest_key")
  if not isinstance(key,str) or not key.strip():errors.append({"index":i,"quest_name":name,"reason":"missing_quest_key"})
  if not trusted_url(row.get("source_url")):errors.append({"index":i,"quest_name":name,"reason":"untrusted_source_url"})
  if row.get("evidence_status")!="raw_source_extracted_needs_structured_review":errors.append({"index":i,"quest_name":name,"reason":"evidence_not_marked_review_only"})
  status=row.get("catalogue_match_status")
  if status not in {"matched","unmatched_catalogue_title"}:errors.append({"index":i,"quest_name":name,"reason":"invalid_catalogue_match_status"})
  shape=row.get("source_row_shape")
  if shape not in {"title_requirements","ordinal_title_requirements","unmatched_two_column"}:errors.append({"index":i,"quest_name":name,"reason":"invalid_source_row_shape"})
  shapes[str(shape)]+=1;txt=row.get("requirements_text")
  if not isinstance(txt,str):errors.append({"index":i,"quest_name":name,"reason":"requirements_text_not_string"});txt=""
  if txt.strip() and txt.strip()!="-":text_count+=1
  else:placeholder_count+=1
  links=row.get("requirement_links",[])
  if not isinstance(links,list):errors.append({"index":i,"quest_name":name,"reason":"requirement_links_not_array"});links=[]
  for j,link in enumerate(links):
   if not isinstance(link,dict) or not trusted_url(link.get("url")):errors.append({"index":i,"quest_name":name,"reason":"untrusted_requirement_link","link_index":j})
   else:link_count+=1
  cat=by_name.get(norm)
  if status=="matched":
   if cat is None:errors.append({"index":i,"quest_name":name,"reason":"marked_matched_but_missing_from_catalogue"})
   else:
    matched.add(norm);expected=str(cat.get("id") or norm.replace(" ","-"))
    if key!=expected:errors.append({"index":i,"quest_name":name,"reason":"catalogue_key_mismatch","expected_key":expected,"actual_key":key})
  elif cat is not None:warnings.append({"index":i,"quest_name":name,"reason":"catalogue_title_present_but_row_unmatched"})
 duplicates=[{"title":by_name.get(n,{}).get("name",n),"row_indices":ix} for n,ix in sorted(seen.items()) if len(ix)>1]
 if duplicates:errors.append({"reason":"duplicate_normalized_evidence_titles","count":len(duplicates)})
 missing=sorted(set(by_name)-matched);unmatched=[r.get("quest_name") for r in evidence if isinstance(r,dict) and r.get("catalogue_match_status")!="matched"]
 return {"generated_at":datetime.now(timezone.utc).isoformat(),"schema_version":"1.0.0","status":"failed" if errors else "review_required",
  "source_url":SOURCE_URL,"catalogue_record_count":len(catalogue),"evidence_record_count":len(evidence),
  "matched_catalogue_record_count":len(matched),"unmatched_evidence_record_count":len(unmatched),
  "catalogue_titles_without_matched_evidence":missing[:200],"duplicate_normalized_evidence_titles":duplicates[:100],
  "records_with_non_placeholder_requirement_text":text_count,"records_with_placeholder_or_empty_requirement_text":placeholder_count,
  "trusted_requirement_link_count":link_count,"source_row_shape_counts":dict(sorted(shapes.items())),
  "errors":errors[:200],"error_count":len(errors),"warnings":warnings[:200],"warning_count":len(warnings),
  "interpretation_limits":["raw text is not a normalized quest requirement","a dash is not proof of no requirements","starting and completion requirements are not distinguished","boostability, rewards, and membership are not inferred","structural success does not prove current game accuracy"]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--input",default=str(RAW/"quest-requirement-evidence.json"));p.add_argument("--catalogue",default=str(RAW/"quest-catalog.json"));p.add_argument("--output",default=str(REPORTS/"quest-evidence-reconciliation.json"));a=p.parse_args()
 try:r=audit(json.loads(Path(a.input).read_text(encoding="utf-8")),json.loads(Path(a.catalogue).read_text(encoding="utf-8")))
 except (OSError,json.JSONDecodeError,ValueError) as exc:print("Quest evidence audit failed: "+str(exc),file=sys.stderr);return 1
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps(r,ensure_ascii=False,indent=2))
 return 1 if r["status"]=="failed" else 0
if __name__=="__main__":raise SystemExit(main())
