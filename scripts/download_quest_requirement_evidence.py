#!/usr/bin/env python3
"""Extract raw source-backed quest requirement evidence from the OSRS Wiki."""
import hashlib,json,re,sys,unicodedata,urllib.error,urllib.parse,urllib.request
from collections import Counter
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/"sources"/"raw"; REPORTS=ROOT/"reports"
API="https://oldschool.runescape.wiki/api.php"; PAGE="Quests/Requirements_by_quest"
SOURCE_URL="https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest"
class Tables(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.table=0;self.row=None;self.cell=None;self.rows=[];self.link=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="table" and "wikitable" in a.get("class",""):self.table+=1
  if not self.table:return
  if tag=="tr":self.row=[]
  elif tag in ("td","th") and self.row is not None:self.cell={"tag":tag,"text":[],"links":[]}
  elif tag=="a" and self.cell is not None:self.link={"href":a.get("href",""),"title":a.get("title",""),"text":[]}
  elif tag=="img" and self.cell is not None:
   alt=a.get("alt") or a.get("title")
   if alt:self.cell["text"].append(" "+alt+" ")
 def handle_data(self,data):
  if self.cell is not None:
   self.cell["text"].append(data)
   if self.link is not None:self.link["text"].append(data)
 def handle_endtag(self,tag):
  if not self.table:return
  if tag=="a" and self.link is not None:
   self.link["text"]=" ".join("".join(self.link["text"]).split());self.cell["links"].append(self.link);self.link=None
  elif tag in ("td","th") and self.cell is not None:
   self.cell["text"]=" ".join("".join(self.cell["text"]).split());self.row.append(self.cell);self.cell=None
  elif tag=="tr" and self.row is not None:
   if self.row:self.rows.append(self.row)
   self.row=None
  elif tag=="table":self.table=max(0,self.table-1)
def canonical_title(value):
 value=unicodedata.normalize("NFKC",str(value or "")).replace("\u00a0"," ").replace("_"," ")
 value=value.replace("’","'").replace("‘","'").replace("＇","'")
 return " ".join(value.casefold().split())
def fetch_html():
 params={"action":"parse","page":PAGE,"prop":"text","format":"json","formatversion":"2"}
 req=urllib.request.Request(API+"?"+urllib.parse.urlencode(params),headers={"User-Agent":"OSRSHub-Game-Data/0.2","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=60) as response:payload=response.read()
 data=json.loads(payload)
 if not isinstance(data,dict) or "error" in data:raise ValueError("Wiki parse API returned an error")
 page=data.get("parse",{}).get("text")
 if not isinstance(page,str) or not page:raise ValueError("Wiki parse API returned no HTML")
 return page,payload
def _links_for(cell):
 links=[]
 for link in cell.get("links",[]):
  href=link.get("href","");title=link.get("title") or link.get("text")
  if not title:continue
  if href.startswith("/w/"):url="https://oldschool.runescape.wiki"+href
  elif href.startswith("https://oldschool.runescape.wiki/"):url=href
  else:continue
  links.append({"title":title,"url":url})
 return links
def extract_rows(page_html,catalogue):
 """Support title/requirements and ordinal/title/requirements table layouts."""
 parser=Tables();parser.feed(page_html)
 by_name={canonical_title(x.get("name")):x for x in catalogue if isinstance(x,dict) and isinstance(x.get("name"),str) and x.get("name").strip()}
 chosen={};duplicate_titles=[];shape_counts=Counter();numeric_index_rows=0
 for row in parser.rows:
  cells=[c for c in row if c["tag"]=="td"]
  if len(cells)<2:continue
  first=canonical_title(cells[0]["text"])
  if first in by_name:name_index,req_index,shape=0,1,"title_requirements"
  elif len(cells)>=3 and canonical_title(cells[1]["text"]) in by_name:name_index,req_index,shape=1,2,"ordinal_title_requirements"
  elif re.fullmatch(r"\d+(?:\.\d+)*",cells[0]["text"].strip()):numeric_index_rows+=1;continue
  else:name_index,req_index,shape=0,1,"unmatched_two_column"
  name=cells[name_index]["text"].strip();norm=canonical_title(name)
  if not norm or re.fullmatch(r"\d+(?:\.\d+)*",name):continue
  req=cells[req_index];links=_links_for(req);quest=by_name.get(norm)
  out={"quest_key":str(quest.get("id") or norm.replace(" ","-")) if quest else "unmatched-"+norm.replace(" ","-"),
   "quest_name":quest["name"] if quest else name,"source_title":name,"requirements_text":req["text"],
   "requirement_links":links,"source_url":SOURCE_URL,"evidence_status":"raw_source_extracted_needs_structured_review",
   "catalogue_match_status":"matched" if quest else "unmatched_catalogue_title","source_row_shape":shape}
  shape_counts[shape]+=1
  if norm in chosen:
   duplicate_titles.append(out["quest_name"]);old=chosen[norm]
   old_score=(old["catalogue_match_status"]=="matched",len(old["requirement_links"]),old["requirements_text"].strip() not in ("","-"),len(old["requirements_text"]))
   new_score=(out["catalogue_match_status"]=="matched",len(out["requirement_links"]),out["requirements_text"].strip() not in ("","-"),len(out["requirements_text"]))
   if new_score>old_score:chosen[norm]=out
  else:chosen[norm]=out
 return sorted(chosen.values(),key=lambda x:canonical_title(x["quest_name"])),{
  "duplicate_source_row_count":len(duplicate_titles),"duplicate_source_titles":sorted(set(duplicate_titles),key=str.casefold)[:100],
  "source_rows_discarded_as_numeric_indices":numeric_index_rows,"extraction_shape_counts":dict(sorted(shape_counts.items()))}
def main():
 RAW.mkdir(parents=True,exist_ok=True);REPORTS.mkdir(parents=True,exist_ok=True)
 try:
  catalogue=json.loads((RAW/"quest-catalog.json").read_text(encoding="utf-8"))
  if not isinstance(catalogue,list):raise ValueError("quest catalogue is not an array")
  page,payload=fetch_html();rows,diagnostics=extract_rows(page,catalogue)
  if not rows:raise ValueError("no requirement rows extracted from source table")
 except (OSError,urllib.error.URLError,TimeoutError,json.JSONDecodeError,ValueError) as exc:
  print("Quest requirement evidence extraction failed: "+str(exc),file=sys.stderr);return 1
 (RAW/"quest-requirement-evidence.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 matched=sum(x["catalogue_match_status"]=="matched" for x in rows)
 matched_names={canonical_title(x["quest_name"]) for x in rows if x["catalogue_match_status"]=="matched"}
 catalogue_names={canonical_title(x.get("name")) for x in catalogue if isinstance(x,dict) and isinstance(x.get("name"),str)}
 report={"generated_at":datetime.now(timezone.utc).isoformat(),"status":"review_required","source_url":SOURCE_URL,
  "source_response_sha256":hashlib.sha256(payload).hexdigest(),"record_count":len(rows),"catalogue_record_count":len(catalogue),
  "matched_catalogue_records":matched,"unmatched_source_records":sum(x["catalogue_match_status"]!="matched" for x in rows),
  "catalogue_titles_without_source_row":sorted(catalogue_names-matched_names)[:100],
  "matched_coverage_percent":round(100*matched/len(catalogue),2) if catalogue else 0,
  "unmatched_source_titles":[x["quest_name"] for x in rows if x["catalogue_match_status"]!="matched"][:100],
  "records_with_requirement_links":sum(bool(x["requirement_links"]) for x in rows),
  "records_with_non_placeholder_requirement_text":sum(bool(x["requirements_text"].strip() and x["requirements_text"].strip()!="-") for x in rows),
  "not_claimed":["normalized skill requirements","boostability","required-to-start distinction","quest-point requirements","rewards","membership restrictions"],
  "diagnostics":diagnostics,"note":"Raw source text is evidence for review, not normalized quest-planner rules. A dash is not promoted to a verified empty requirement list."}
 (REPORTS/"quest-requirement-evidence-coverage.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
