#!/usr/bin/env python3
"""Merge raw OSRSBox/community snapshots into normalized JSON datasets."""
from __future__ import annotations
import hashlib, json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW, DIST, REPORTS = ROOT/"sources"/"raw", ROOT/"dist", ROOT/"reports"
INPUTS = {"community_items":"items", "original_items":"items", "community_monsters":"monsters", "original_monsters":"monsters"}
def load_records(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # Some datasets may be keyed by ID; normalize to values while retaining key as fallback ID.
        result = []
        for key, value in data.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("id", key)
                result.append(row)
        return result
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    raise ValueError(f"Unsupported top-level JSON type in {path}: {type(data).__name__}")
def numeric_id(record):
    for key in ("id", "item_id", "npc_id", "monster_id"):
        value = record.get(key)
        try:
            if value is not None: return int(value)
        except (TypeError, ValueError): pass
    return None
def name_of(record):
    for key in ("name", "item_name", "npc_name", "monster_name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip(): return value.strip()
    return ""
def merge_category(category):
    merged, sources_for_id, conflicts = {}, defaultdict(list), []
    source_names = [name for name, cat in INPUTS.items() if cat == category]
    for source_name in source_names:
        path = RAW / f"{source_name}.json"
        if not path.exists(): raise FileNotFoundError(f"Missing {path}; run scripts/download_sources.py first")
        for record in load_records(path):
            record_id = numeric_id(record)
            if record_id is None:
                conflicts.append({"category":category,"source":source_name,"reason":"missing_or_non_numeric_id","record_name":name_of(record)})
                continue
            key = str(record_id)
            sources_for_id[key].append(source_name)
            if key not in merged:
                merged[key] = {"id":record_id,"name":name_of(record),"sources":[source_name],"source_records":{source_name:record}}
                # Keep normalized source fields available at the top level without claiming a universal schema.
                for field, value in record.items():
                    if field not in ("id","item_id","npc_id","monster_id","name","item_name","npc_name","monster_name"):
                        merged[key][field] = value
            else:
                target = merged[key]
                target["sources"] = sorted(set(target["sources"] + [source_name]))
                target["source_records"][source_name] = record
                if not target.get("name") and name_of(record): target["name"] = name_of(record)
                for field, value in record.items():
                    if field in ("id","item_id","npc_id","monster_id","name","item_name","npc_name","monster_name"): continue
                    if field not in target:
                        target[field] = value
                    elif target[field] != value:
                        conflicts.append({"category":category,"id":record_id,"field":field,"kept_source":target["sources"][0],"other_source":source_name,"kept_value":target[field],"other_value":value})
    records = sorted(merged.values(), key=lambda r:r["id"])
    for row in records:
        row["sources"] = sorted(set(row["sources"]))
    return records, conflicts
def main():
    DIST.mkdir(parents=True, exist_ok=True); REPORTS.mkdir(parents=True, exist_ok=True)
    all_conflicts, counts, input_hashes = [], {}, {}
    for path in sorted(RAW.glob("*.json")):
        if path.name != "manifest.json": input_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for category in ("items","monsters"):
        records, conflicts = merge_category(category)
        (DIST/f"{category}.json").write_text(json.dumps(records, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
        counts[category] = len(records); all_conflicts.extend(conflicts)
        if category == "items":
            equipment = [r for r in records if r.get("equipable") is True or isinstance(r.get("equipment"),dict) or isinstance(r.get("equipable_by_player"),bool) and r.get("equipable_by_player")]
            (DIST/"equipment.json").write_text(json.dumps(equipment, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
            counts["equipment_candidates"] = len(equipment)
    (REPORTS/"source-conflicts.json").write_text(json.dumps(all_conflicts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    manifest={"generated_at":datetime.now(timezone.utc).isoformat(),"inputs_sha256":input_hashes,"counts":counts,"conflict_count":len(all_conflicts),"note":"Source precedence is first source listed in scripts/build_dataset.py; disagreements are reported for review."}
    (DIST/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))
if __name__ == "__main__": main()
