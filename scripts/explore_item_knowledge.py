#!/usr/bin/env python3
"""Explore source-attributed item relationships using generated datasets only.

The explorer resolves exact dataset/record-ID links emitted by the item graph.
It does not infer drop sources, recipe ingredients, quest unlocks or mechanics.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
TARGETS = {
    "items.json": ("items.json", ("id", "name", "tradeable", "equipable", "members", "quest_item")),
    "equipment-stats.json": ("equipment-stats.json", ("id", "name", "slot", "bonuses", "requirements", "source_url")),
    "weapons.json": ("weapons.json", ("id", "name", "attack_speed", "weapon_type", "stances", "source_url")),
    "item-requirements.json": ("item-requirements.json", ("item_id", "requirements", "source_url")),
    "item-combat-profiles.json": ("item-combat-profiles.json", ("id", "name", "slot", "bonuses", "attack_speed", "weapon_type", "skill_requirements", "source_urls", "data_status")),
}
def load_json_array(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"{path} must be a JSON array of objects")
    return data

def record_key(row: dict[str, Any]) -> Any:
    return row.get("id", row.get("item_id"))

def resolve_relationships(item_id: int, dist_dir: Path = DIST) -> dict[str, Any]:
    graph_rows = load_json_array(dist_dir / "item-relationships.json")
    graph = next((r for r in graph_rows if r.get("item_id") == item_id), None)
    if graph is None:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "not_found", "item_id": item_id, "item_name": None,
            "relationships": [], "unresolved_relationships": [],
            "guardrails": ["A missing graph node is unknown, not proof that the item has no relationships."]
        }
    cache: dict[str, list[dict[str, Any]]] = {}
    resolved, unresolved = [], []
    for edge in graph.get("relationships", []):
        target_name = edge.get("dataset")
        target_id = edge.get("record_id")
        if target_name not in TARGETS or not isinstance(target_id, int):
            unresolved.append({"edge": edge, "reason": "Unsupported target dataset or invalid record ID"})
            continue
        filename, fields = TARGETS[target_name]
        if filename not in cache:
            cache[filename] = load_json_array(dist_dir / filename)
        target = next((row for row in cache[filename] if record_key(row) == target_id), None)
        if target is None:
            unresolved.append({"edge": edge, "reason": "Target record not present in generated dataset"})
            continue
        resolved.append({
            "relationship_type": edge.get("type"),
            "target_dataset": target_name,
            "target_record_id": target_id,
            "target_name": target.get("name", target.get("item_name")),
            "data_status": target.get("data_status", edge.get("data_status")),
            "source_urls": target.get("source_urls", [target.get("source_url")] if target.get("source_url") else []),
            "record_facts": {field: target.get(field) for field in fields if field in target},
            "known_fields": [field for field in fields if field in target and target.get(field) not in (None, "", [], {})],
            "unknown_fields": [field for field in fields if field not in target or target.get(field) in (None, "", [], {})],
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "found",
        "item_id": item_id,
        "item_name": graph.get("item_name"),
        "graph_sources": graph.get("sources", []),
        "relationship_count": len(graph.get("relationships", [])),
        "resolved_relationship_count": len(resolved),
        "relationships": resolved,
        "unresolved_relationships": unresolved,
        "guardrails": [
            "Only exact graph edges and exact target IDs are followed.",
            "A missing target is reported as unresolved; no substitute record is guessed.",
            "The graph currently describes generated item/equipment/weapon/requirement/profile joins, not a complete OSRS knowledge graph.",
            "Presence and source URLs do not independently verify a fact; absent fields remain unknown."
        ]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-id", required=True, type=int)
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()
    try:
        result = resolve_relationships(args.item_id)
    except ValueError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result["status"] == "found" else 2

if __name__ == "__main__":
    raise SystemExit(main())
