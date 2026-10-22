#!/usr/bin/env python3
"""Extract raw source-backed quest requirement evidence from the OSRS Wiki."""
import hashlib,json,sys,urllib.error,urllib.parse,urllib.request
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/"sources"/"raw"; REPORTS=ROOT/"reports"
API="https://oldschool.runescape.wiki/api.php"; PAGE="Quests/Requirements_by_quest"
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
def fetch_html():
 params={"action":"parse","page":PAGE,"prop":"text","format":"json","formatversion":"2"}
 req=urllib.request.Request(API+"?"+urllib.parse.urlencode(params),headers={"User-Agent":"OSRSHub-Game-Data/0.1","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=60) as response:payload=response.read()
 data=json.loads(payload)
 if not isinstance(data,dict) or "error" in data:raise ValueError("Wiki parse API returned an error")
 page=data.get("parse",{}).get("text")
 if not isinstance(page,str) or not page:raise ValueError("Wiki parse API returned no HTML")
 return page,payload
def extract_rows(page_html,catalogue):
 parser=Tables();parser.feed(page_html)
 by_name={" ".join(str(x.get("name","")).casefold().split()):x for x in catalogue if isinstance(x,dict)}
 rows=[];seen=set()
 for row in parser.rows:
  cells=[c for c in row if c["tag"]=="td"]
  if len(cells)<2:continue
  name=cells[0]["text"];norm=" ".join(name.casefold().split())
  if not norm or norm in seen:continue
  seen.add(norm);req=cells[1];links=[]
  for link in req["links"]:
   href=link["href"];title=link.get("title") or link.get("text")
   if not title:continue
   if href.startswith("/w/"):url="https://oldschool.runescape.wiki"+href
   elif href.startswith("https://oldschool.runescape.wiki/"):url=href
   else:continue
   links.append({"title":title,"url":url})
  quest=by_name.get(norm)
  rows.append({"quest_key":str(quest.get("id") or norm.replace(" ","-")) if quest else "unmatched-"+norm.replace(" ","-"),"quest_name":quest["name"] if quest else name,"requirements_text":req["text"],"requirement_links":links,"source_url":"https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest","evidence_status":"raw_source_extracted_needs_structured_review","catalogue_match_status":"matched" if quest else "unmatched_catalogue_title"})
 return sorted(rows,key=lambda x:x["quest_name"].casefold())
def main():
 RAW.mkdir(parents=True,exist_ok=True);REPORTS.mkdir(parents=True,exist_ok=True)
 try:
  catalogue=json.loads((RAW/"quest-catalog.json").read_text(encoding="utf-8"))
  if not isinstance(catalogue,list):raise ValueError("quest catalogue is not an array")
  page,payload=fetch_html();rows=extract_rows(page,catalogue)
  if not rows:raise ValueError("no requirement rows extracted from source table")
 except (OSError,urllib.error.URLError,TimeoutError,json.JSONDecodeError,ValueError) as exc:
  print("Quest requirement evidence extraction failed: "+str(exc),file=sys.stderr);return 1
 (RAW/"quest-requirement-evidence.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 report={"generated_at":datetime.now(timezone.utc).isoformat(),"status":"review_required","source_url":"https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest","source_response_sha256":hashlib.sha256(payload).hexdigest(),"record_count":len(rows),"catalogue_record_count":len(catalogue),"matched_catalogue_records":sum(x["catalogue_match_status"]=="matched" for x in rows),"unmatched_source_records":sum(x["catalogue_match_status"]!="matched" for x in rows),"matched_coverage_percent":round(100*sum(x["catalogue_match_status"]=="matched" for x in rows)/len(catalogue),2) if catalogue else 0,"unmatched_source_titles":[x["quest_name"] for x in rows if x["catalogue_match_status"]!="matched"][:100],"records_with_requirement_links":sum(bool(x["requirement_links"]) for x in rows),"not_claimed":["normalized skill requirements","boostability","required-to-start distinction","quest-point requirements","rewards","membership restrictions"],"note":"Raw source text is evidence for review, not normalized quest-planner rules."}
 (REPORTS/"quest-requirement-evidence-coverage.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
