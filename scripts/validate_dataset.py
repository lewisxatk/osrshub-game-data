#!/usr/bin/env python3
"""Structural validation for generated OSRS Hub game datasets."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST, REPORTS=ROOT/"dist",ROOT/"reports"
EXPECTED_ITEMS=("Fighter torso","Helm of Neitiznot","Slayer helmet (i)")
def read_json(path):
    with path.open(encoding="utf-8") as f: return json.load(f)
def main():
    errors=[]; warnings=[]; counts={}
    for filename in ("items.json","equipment.json","monsters.json","manifest.json"):
        path=DIST/filename
        if not path.exists(): errors.append(f"Missing generated file: dist/{filename}"); continue
        try: data=read_json(path)
        except (OSError,json.JSONDecodeError) as exc: errors.append(f"Invalid JSON in {filename}: {exc}"); continue
        if filename in ("items.json","equipment.json","monsters.json"):
            if not isinstance(data,list): errors.append(f"{filename} must contain a JSON array"); continue
            counts[filename]=len(data); seen=set()
            for i,row in enumerate(data):
                if not isinstance(row,dict): errors.append(f"{filename}[{i}] is not an object"); continue
                item_id=row.get("id")
                if not isinstance(item_id,int): errors.append(f"{filename}[{i}] has no integer id")
                elif item_id in seen: errors.append(f"{filename} has duplicate id {item_id}")
                else: seen.add(item_id)
                if not isinstance(row.get("name"),str) or not row["name"].strip(): warnings.append(f"{filename}[{i}] id={item_id} has no name")
    items_path=DIST/"items.json"
    if items_path.exists():
        try:
            names={r.get("name","").casefold() for r in read_json(items_path) if isinstance(r,dict)}
            for name in EXPECTED_ITEMS:
                if name.casefold() not in names: warnings.append(f"Expected item not found by exact name: {name}")
        except (OSError,json.JSONDecodeError): pass
    result={"status":"failed" if errors else "passed_with_warnings" if warnings else "passed","counts":counts,"errors":errors,"warnings":warnings}
    REPORTS.mkdir(parents=True,exist_ok=True)
    (REPORTS/"validation.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return 1 if errors else 0
if __name__=="__main__": raise SystemExit(main())
