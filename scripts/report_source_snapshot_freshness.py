#!/usr/bin/env python3
"""Summarize raw snapshot inventory, hashes and available source retrieval metadata."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def walk_metadata(value, trail="$"):
    found=[]
    if isinstance(value,dict):
        keys={str(k).casefold():k for k in value}
        url=next((value[k] for lk,k in keys.items() if lk in {"url","source_url","download_url","html_url"} and isinstance(value[k],str) and value[k].startswith("http")),None)
        timestamp=next((value[k] for lk,k in keys.items() if lk in {"retrieved_at","downloaded_at","fetched_at","updated_at","timestamp"} and isinstance(value[k],str)),None)
        digest=next((value[k] for lk,k in keys.items() if lk in {"sha256","checksum","content_sha256"} and isinstance(value[k],str)),None)
        if url or timestamp or digest: found.append({"path":trail,"url":url,"retrieved_at":timestamp,"sha256":digest})
        for k,v in value.items(): found.extend(walk_metadata(v,f"{trail}.{k}"))
    elif isinstance(value,list):
        for i,v in enumerate(value): found.extend(walk_metadata(v,f"{trail}[{i}]"))
    return found
def build_freshness(directory:Path, manifest_path:Path, now=None):
    now=now or datetime.now(timezone.utc); snapshots=[]; metadata=[]; errors=[]
    if manifest_path.exists():
        try: manifest=json.loads(manifest_path.read_text(encoding="utf-8")); metadata=walk_metadata(manifest)
        except (OSError,json.JSONDecodeError) as e: errors.append({"file":str(manifest_path),"error":str(e)})
    else: errors.append({"file":str(manifest_path),"error":"manifest_missing"})
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        if path.resolve()==manifest_path.resolve(): continue
        try:
            raw=path.read_bytes(); data=json.loads(raw.decode("utf-8"))
            rows=len(data) if isinstance(data,list) else 1 if isinstance(data,dict) else 0
            snapshots.append({"file":path.name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
                              "root_type":"array" if isinstance(data,list) else "object" if isinstance(data,dict) else "other",
                              "record_count":rows})
        except (OSError,UnicodeDecodeError,json.JSONDecodeError) as e: errors.append({"file":path.name,"error":str(e)})
    dated=[]; undated=0
    for entry in metadata:
        age=None
        if entry["retrieved_at"]:
            try:
                stamp=datetime.fromisoformat(entry["retrieved_at"].replace("Z","+00:00"))
                if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
                age=max(0,(now-stamp.astimezone(timezone.utc)).total_seconds()/86400)
            except ValueError: pass
        if age is None: undated+=1
        dated.append({**entry,"age_days":round(age,2) if age is not None else None})
    return {"generated_at":now.isoformat(),"status":"failed" if any(e["error"]!="manifest_missing" for e in errors) else "review_required" if not metadata or undated else "passed",
      "raw_snapshot_file_count":len(snapshots),"raw_snapshot_record_rows":sum(x["record_count"] for x in snapshots),
      "raw_snapshot_bytes":sum(x["bytes"] for x in snapshots),"manifest_metadata_entry_count":len(metadata),
      "metadata_entries_without_parseable_timestamp":undated,"metadata_entries":dated[:5000],"snapshots":snapshots,
      "errors":errors,"guardrails":["Snapshot file hashes are computed from the checked-out bytes; they do not authenticate the source publisher.",
      "Retrieval timestamps are only reported when present and parseable; absent timestamps are unknown, not fresh.",
      "Raw source rows are not additive with normalized dist rows and may contain overlapping entities.",
      "No source file is modified and no conflicting source is silently selected."]}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--directory",type=Path,default=ROOT/"sources/raw");p.add_argument("--manifest",type=Path,default=ROOT/"sources/raw/manifest.json");p.add_argument("--output",type=Path,default=ROOT/"reports/source-snapshot-freshness.json");a=p.parse_args()
    r=build_freshness(a.directory,a.manifest);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:r[k] for k in ("status","raw_snapshot_file_count","raw_snapshot_record_rows","manifest_metadata_entry_count","metadata_entries_without_parseable_timestamp")},indent=2));return 1 if r["status"]=="failed" else 0
if __name__=="__main__":raise SystemExit(main())
