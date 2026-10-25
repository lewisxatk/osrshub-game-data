#!/usr/bin/env python3
"""Inventory every generated dist JSON dataset without conflating rows with unique entities."""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_FIELDS = {
    "items.json": "id", "equipment-stats.json": "id", "weapons.json": "id",
    "monsters-combat.json": "id", "item-requirements.json": "item_id",
    "item-combat-profiles.json": "id", "item-relationships.json": "item_id",
    "quests.json": "key", "quest-relationships.json": "quest_key",
    "prayers.json": "id", "npc-drops.json": "npc_id", "drop-subtables.json": "table_key",
    "shops-by-shop.json": "shop_name", "shops-by-npc.json": "npc_id",
    "slayer-tasks.json": "slayer_master_id", "npc-interactions.json": "source_key",
    "npc-dialogues.json": "source_key", "npcs-summary.json": "id",
    "objects-summary.json": "id", "models-summary.json": "source_key",
}
DOMAIN_RULES = {
    "items": ("items", "equipment-stats.json", "weapons.json", "item-requirements.json",
              "item-combat-profiles.json", "item-relationships.json"),
    "combat": ("weapons.json", "equipment-stats.json", "item-combat-profiles.json",
               "monsters-combat.json"),
    "quests": ("quests.json", "quest-relationships.json"),
    "monsters": ("monsters-combat.json", "npc-drops.json", "drop-subtables.json"),
    "world": ("npcs-summary.json", "objects-summary.json", "models-summary.json",
              "npc-interactions.json", "npc-dialogues.json", "shops-by-shop.json", "shops-by-npc.json"),
    "other": ("prayers.json", "slayer-tasks.json"),
}
def present(v):
    return v is not None and v != "" and v != [] and v != {}
def valid_identity(v):
    return isinstance(v, (str, int)) and not isinstance(v, bool) and (not isinstance(v, str) or bool(v.strip()))
def dataset_domain(filename):
    for domain, names in DOMAIN_RULES.items():
        if filename in names: return domain
    return "unclassified"
def inspect_file(path: Path):
    raw = path.read_bytes()
    try: data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"file": path.name, "path": f"dist/{path.name}", "domain": dataset_domain(path.name),
                "status": "invalid_json", "byte_size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "record_count": 0, "identity_field": IDENTITY_FIELDS.get(path.name),
                "unique_identity_count": 0, "missing_identity_count": 0, "invalid_identity_count": 0,
                "duplicate_identity_count": 0, "duplicate_identity_samples": [], "fields": {}, "error": str(exc)}
    rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    object_rows = [r for r in rows if isinstance(r, dict)]
    field_counts = Counter(k for row in object_rows for k, value in row.items() if present(value))
    identity_field = IDENTITY_FIELDS.get(path.name, "id")
    identities, duplicates = set(), set()
    missing = invalid = 0
    for row in object_rows:
        value = row.get(identity_field)
        if value is None or value == "":
            missing += 1
        elif not valid_identity(value):
            invalid += 1
        elif value in identities:
            duplicates.add(str(value))
        else:
            identities.add(value)
    status = "passed" if isinstance(data, (list, dict)) and len(object_rows) == len(rows) else "review_required"
    return {
        "file": path.name, "path": f"dist/{path.name}", "domain": dataset_domain(path.name),
        "status": status, "root_type": "array" if isinstance(data, list) else "object" if isinstance(data, dict) else type(data).__name__,
        "byte_size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "record_count": len(rows), "object_record_count": len(object_rows),
        "identity_field": identity_field, "unique_identity_count": len(identities),
        "missing_identity_count": missing, "invalid_identity_count": invalid,
        "duplicate_identity_count": len(duplicates), "duplicate_identity_samples": sorted(duplicates)[:20],
        "field_count": len(set(k for row in object_rows for k in row)),
        "fields": {k: {"present_records": n, "missing_records": len(object_rows)-n,
                       "coverage_percent": round(100*n/len(object_rows), 2) if object_rows else 0.0}
                   for k, n in sorted(field_counts.items())},
    }
def build_census(directory: Path):
    files = sorted(directory.glob("*.json")) if directory.exists() else []
    datasets = [inspect_file(path) for path in files]
    totals = {
        "dataset_file_count": len(datasets),
        "record_rows_across_files": sum(d["record_count"] for d in datasets),
        "object_records_across_files": sum(d.get("object_record_count", 0) for d in datasets),
        "unique_identity_keys_within_files": sum(d["unique_identity_count"] for d in datasets),
        "total_bytes": sum(d["byte_size"] for d in datasets),
        "files_with_duplicate_identities": sum(d["duplicate_identity_count"] > 0 for d in datasets),
        "files_with_missing_identities": sum(d["missing_identity_count"] > 0 for d in datasets),
        "invalid_json_file_count": sum(d["status"] == "invalid_json" for d in datasets),
    }
    domains = {}
    for domain in sorted({d["domain"] for d in datasets}):
        subset = [d for d in datasets if d["domain"] == domain]
        domains[domain] = {"dataset_file_count": len(subset),
            "record_rows_across_files": sum(d["record_count"] for d in subset),
            "unique_identity_keys_within_files": sum(d["unique_identity_count"] for d in subset)}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "status": "failed" if totals["invalid_json_file_count"] else "passed",
        "definition": "Inventory of generated dist/*.json files in this CI run. Counts across files overlap: the same game entity can appear in items, equipment, weapons, requirements and joined profiles. The summed unique_identity_keys_within_files is not a global unique-entity count.",
        "totals": totals, "domains": domains, "datasets": datasets,
        "guardrails": [
            "Generated artifact inventory only; it does not include ungenerated files, all source records, or live Grand Exchange data.",
            "Rows across datasets are overlapping records, not unique OSRS entities.",
            "Identity uniqueness is evaluated within each file using its configured key; IDs from different namespaces are not merged.",
            "Field presence, hashes, and structural checks do not prove source accuracy or combat-mechanics correctness."
        ]
    }
def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--directory",type=Path,default=ROOT/"dist"); p.add_argument("--output",type=Path,default=ROOT/"reports/database-census.json"); a=p.parse_args()
    result=build_census(a.directory); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"totals":result["totals"],"domains":result["domains"]},indent=2))
    return 1 if result["status"]=="failed" else 0
if __name__=="__main__": raise SystemExit(main())
