#!/usr/bin/env python3
"""Cross-domain consistency audit for OSRS Hub generated game data.

Checks relationships among generated item, equipment, weapon, requirement,
combat-profile and quest datasets. It validates structure and joins only; it
does not fetch external sources or claim that imported game facts are correct.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"

REQUIRED = (
    "items.json", "equipment-stats.json", "weapons.json", "item-requirements.json",
    "item-relationships.json", "item-combat-profiles.json", "monsters-combat.json",
    "quests.json", "quest-relationships.json",
)


def load_array(name: str, dist_dir: Path = DIST) -> list[dict[str, Any]]:
    path = dist_dir / name
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{path} must be a JSON array of objects")
    return rows


def canonical(value: Any) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def index_ids(rows: list[dict[str, Any]], dataset: str, field: str,
              errors: list[dict[str, Any]]) -> set[int]:
    found: set[int] = set()
    for index, row in enumerate(rows):
        value = row.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append({"dataset": dataset, "index": index, "issue": "invalid_id", "field": field, "value": value})
            continue
        if value in found:
            errors.append({"dataset": dataset, "index": index, "issue": "duplicate_id", "field": field, "value": value})
        found.add(value)
    return found


def audit_datasets(datasets: dict[str, Any]) -> dict[str, Any]:
    missing = [name for name in REQUIRED if name not in datasets]
    if missing:
        raise ValueError("missing input datasets: " + ", ".join(missing))

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    arrays: dict[str, list[dict[str, Any]]] = {}
    for name in REQUIRED:
        rows = datasets[name]
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"{name} must be a JSON array of objects")
        arrays[name] = rows

    items = index_ids(arrays["items.json"], "items.json", "id", errors)
    equipment = index_ids(arrays["equipment-stats.json"], "equipment-stats.json", "id", errors)
    weapons = index_ids(arrays["weapons.json"], "weapons.json", "id", errors)
    requirements = index_ids(arrays["item-requirements.json"], "item-requirements.json", "item_id", errors)
    profiles = index_ids(arrays["item-combat-profiles.json"], "item-combat-profiles.json", "id", errors)
    monsters = index_ids(arrays["monsters-combat.json"], "monsters-combat.json", "id", errors)

    for dataset, joined_ids in (
        ("equipment-stats.json", equipment), ("weapons.json", weapons),
        ("item-requirements.json", requirements), ("item-combat-profiles.json", profiles),
    ):
        for item_id in sorted(joined_ids - items):
            errors.append({"dataset": dataset, "issue": "orphan_item_join", "item_id": item_id})

    for index, row in enumerate(arrays["item-combat-profiles.json"]):
        item_id = row.get("id")
        for flag, expected in (
            ("equipment_record_present", item_id in equipment),
            ("weapon_record_present", item_id in weapons),
            ("skill_requirement_record_present", item_id in requirements),
        ):
            if not isinstance(row.get(flag), bool):
                errors.append({"dataset": "item-combat-profiles.json", "index": index,
                               "issue": "presence_flag_not_boolean", "field": flag})
            elif row[flag] != expected:
                errors.append({"dataset": "item-combat-profiles.json", "index": index,
                               "issue": "presence_flag_join_mismatch", "field": flag, "item_id": item_id})

        speed = row.get("attack_speed")
        if speed is not None and (isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0):
            errors.append({"dataset": "item-combat-profiles.json", "index": index,
                           "issue": "invalid_attack_speed", "item_id": item_id, "value": speed})
        bonuses = row.get("bonuses")
        if bonuses is not None:
            if not isinstance(bonuses, dict):
                errors.append({"dataset": "item-combat-profiles.json", "index": index,
                               "issue": "bonuses_not_object", "item_id": item_id})
            else:
                for field, value in bonuses.items():
                    if value is not None and not finite_number(value):
                        errors.append({"dataset": "item-combat-profiles.json", "index": index,
                                       "issue": "non_finite_or_non_numeric_bonus", "item_id": item_id,
                                       "field": field, "value": value})
        reqs = row.get("skill_requirements")
        if reqs is not None and not isinstance(reqs, list):
            errors.append({"dataset": "item-combat-profiles.json", "index": index,
                           "issue": "skill_requirements_not_array", "item_id": item_id})
        elif isinstance(reqs, list):
            seen_req: set[tuple[str, int]] = set()
            for req_index, req in enumerate(reqs):
                if not isinstance(req, dict) or not isinstance(req.get("skill"), str) or not canonical(req.get("skill")):
                    errors.append({"dataset": "item-combat-profiles.json", "index": index,
                                   "issue": "malformed_skill_requirement", "item_id": item_id,
                                   "requirement_index": req_index})
                    continue
                level = req.get("level")
                if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 99:
                    errors.append({"dataset": "item-combat-profiles.json", "index": index,
                                   "issue": "invalid_skill_requirement_level", "item_id": item_id,
                                   "requirement_index": req_index, "value": level})
                    continue
                key = (canonical(req["skill"]), level)
                if key in seen_req:
                    errors.append({"dataset": "item-combat-profiles.json", "index": index,
                                   "issue": "duplicate_skill_requirement", "item_id": item_id,
                                   "skill": req["skill"], "level": level})
                seen_req.add(key)

    quest_rows = arrays["quest-relationships.json"]
    if not arrays["quests.json"]:
        warnings.append({"dataset": "quests.json", "issue": "empty_quest_catalogue",
                         "message": "Quest facts are not available to validate quest prerequisite coverage."})
    quest_keys: set[str] = set()
    for index, quest in enumerate(quest_rows):
        key = quest.get("quest_key")
        if not isinstance(key, str) or not key.strip():
            errors.append({"dataset": "quest-relationships.json", "index": index, "issue": "invalid_quest_key"})
        elif key in quest_keys:
            errors.append({"dataset": "quest-relationships.json", "index": index,
                           "issue": "duplicate_quest_key", "quest_key": key})
        else:
            quest_keys.add(key)

    prerequisite_edges: set[tuple[str, str]] = set()
    dependent_edges: set[tuple[str, str]] = set()
    for index, quest in enumerate(quest_rows):
        key = quest.get("quest_key")
        if not isinstance(key, str) or not key.strip():
            continue
        for field, edge_kind in (("prerequisites", "prerequisite"), ("dependents", "dependent")):
            edges = quest.get(field, [])
            if not isinstance(edges, list):
                errors.append({"dataset": "quest-relationships.json", "index": index,
                               "issue": f"{field}_not_array", "quest_key": key})
                continue
            seen_targets: set[str] = set()
            for edge_index, edge in enumerate(edges):
                if not isinstance(edge, dict) or not isinstance(edge.get("quest_key"), str) or not edge["quest_key"].strip():
                    errors.append({"dataset": "quest-relationships.json", "index": index,
                                   "issue": f"malformed_{edge_kind}_edge", "quest_key": key,
                                   "edge_index": edge_index})
                    continue
                target = edge["quest_key"]
                if target not in quest_keys:
                    errors.append({"dataset": "quest-relationships.json", "index": index,
                                   "issue": f"dangling_{edge_kind}_key", "quest_key": key, "target": target})
                if target == key:
                    errors.append({"dataset": "quest-relationships.json", "index": index,
                                   "issue": f"self_{edge_kind}", "quest_key": key})
                if target in seen_targets:
                    errors.append({"dataset": "quest-relationships.json", "index": index,
                                   "issue": f"duplicate_{edge_kind}_edge", "quest_key": key, "target": target})
                seen_targets.add(target)
                if edge_kind == "prerequisite":
                    prerequisite_edges.add((key, target))
                    if edge.get("completion_state") not in ("completed", "started"):
                        errors.append({"dataset": "quest-relationships.json", "index": index,
                                       "issue": "invalid_completion_state", "quest_key": key,
                                       "value": edge.get("completion_state")})
                else:
                    dependent_edges.add((target, key))

    # A prerequisite cycle makes a quest pathway impossible to topologically order.
    # Only edges whose endpoints exist are considered, so dangling references remain
    # reported by the checks above without being mislabelled as graph cycles.
    prerequisite_graph: dict[str, set[str]] = {key: set() for key in quest_keys}
    for quest_key, prerequisite_key in prerequisite_edges:
        if quest_key in quest_keys and prerequisite_key in quest_keys:
            prerequisite_graph[quest_key].add(prerequisite_key)
    visited: set[str] = set()
    active: set[str] = set()
    reported_cycles: set[tuple[str, ...]] = set()

    def visit_quest(node: str, path: list[str]) -> None:
        if node in active:
            start = path.index(node) if node in path else 0
            cycle = tuple(sorted(path[start:]))
            if cycle not in reported_cycles:
                reported_cycles.add(cycle)
                errors.append({"dataset": "quest-relationships.json", "issue": "prerequisite_cycle",
                               "quest_keys": list(cycle),
                               "message": "Quest prerequisites contain a cycle and cannot form a valid progression order."})
            return
        if node in visited:
            return
        active.add(node)
        path.append(node)
        for prerequisite in sorted(prerequisite_graph.get(node, set())):
            visit_quest(prerequisite, path)
        path.pop()
        active.remove(node)
        visited.add(node)

    for quest_key in sorted(quest_keys):
        if quest_key not in visited:
            visit_quest(quest_key, [])

    for edge in sorted(prerequisite_edges - dependent_edges):
        errors.append({"dataset": "quest-relationships.json", "issue": "missing_reverse_dependent_edge",
                       "quest_key": edge[0], "prerequisite_key": edge[1]})
    for edge in sorted(dependent_edges - prerequisite_edges):
        errors.append({"dataset": "quest-relationships.json", "issue": "orphan_reverse_dependent_edge",
                       "quest_key": edge[1], "prerequisite_key": edge[0]})

    relationship_types = {
        "has_equipment_stats": equipment, "has_weapon_data": weapons,
        "has_skill_requirements": requirements, "has_combat_profile": profiles,
    }
    relationship_rows = arrays["item-relationships.json"]
    relationship_owner_ids: set[int] = set()
    for index, row in enumerate(relationship_rows):
        item_id = row.get("item_id")
        if isinstance(item_id, int) and not isinstance(item_id, bool):
            if item_id in relationship_owner_ids:
                errors.append({"dataset": "item-relationships.json", "index": index,
                               "issue": "duplicate_item_relationship_row", "item_id": item_id})
            relationship_owner_ids.add(item_id)
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id not in items:
            errors.append({"dataset": "item-relationships.json", "index": index,
                           "issue": "invalid_or_orphan_item_id", "item_id": item_id})
            continue
        rels = row.get("relationships")
        if not isinstance(rels, list):
            errors.append({"dataset": "item-relationships.json", "index": index,
                           "issue": "relationships_not_array", "item_id": item_id})
            continue
        seen_links: set[tuple[str, int]] = set()
        for link_index, link in enumerate(rels):
            if not isinstance(link, dict):
                errors.append({"dataset": "item-relationships.json", "index": index,
                               "issue": "relationship_not_object", "item_id": item_id})
                continue
            kind, record_id = link.get("type"), link.get("record_id")
            if kind not in relationship_types:
                errors.append({"dataset": "item-relationships.json", "index": index,
                               "issue": "unknown_relationship_type", "item_id": item_id, "type": kind})
                continue
            if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id not in relationship_types[kind]:
                errors.append({"dataset": "item-relationships.json", "index": index,
                               "issue": "orphan_relationship_target", "item_id": item_id,
                               "type": kind, "record_id": record_id})
                continue
            pair = (kind, record_id)
            if pair in seen_links:
                errors.append({"dataset": "item-relationships.json", "index": index,
                               "issue": "duplicate_relationship", "item_id": item_id,
                               "type": kind, "record_id": record_id})
            seen_links.add(pair)

    # Coverage is reported separately from correctness: an absent record is
    # a known gap, not a fabricated zero-valued game fact.
    profile_rows = arrays["item-combat-profiles.json"]
    item_ids = set(items)
    profile_ids = set(profiles)
    quest_prerequisite_counts = {key: 0 for key in quest_keys}
    for source_key, _target_key in prerequisite_edges:
        if source_key in quest_prerequisite_counts:
            quest_prerequisite_counts[source_key] += 1
    coverage = {
        "items_with_equipment_stats": len(item_ids & equipment),
        "items_without_equipment_stats": len(item_ids - equipment),
        "items_with_weapon_data": len(item_ids & weapons),
        "items_without_weapon_data": len(item_ids - weapons),
        "items_with_skill_requirements_record": len(item_ids & requirements),
        "items_without_skill_requirements_record": len(item_ids - requirements),
        "items_with_combat_profile": len(item_ids & profile_ids),
        "items_without_combat_profile": len(item_ids - profile_ids),
        "profiles_missing_attack_speed": sum(1 for row in profile_rows if row.get("attack_speed") is None),
        "profiles_missing_bonuses": sum(1 for row in profile_rows if row.get("bonuses") is None),
        "profiles_missing_skill_requirements": sum(1 for row in profile_rows if row.get("skill_requirements") is None),
        "quest_nodes_without_prerequisites": sum(1 for count in quest_prerequisite_counts.values() if count == 0),
        "quest_nodes_with_prerequisites": sum(1 for count in quest_prerequisite_counts.values() if count > 0),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else ("review_required" if warnings else "passed"),
        "datasets": {
            "items": len(items), "equipment": len(equipment), "weapons": len(weapons),
            "requirements": len(requirements), "item_profiles": len(profiles),
            "monsters": len(monsters), "quest_graph_nodes": len(quest_keys),
            "item_relationship_rows": len(relationship_rows),
        },
        "coverage": coverage,
        "counts": {"error_count": len(errors), "warning_count": len(warnings),
                   "quest_prerequisite_edges": len(prerequisite_edges),
                   "item_relationship_rows": len(relationship_rows)},
        "errors": errors[:500], "warnings": warnings[:200],
        "guardrails": [
            "This audit checks structure, references and join consistency; it does not independently verify OSRS facts.",
            "Missing data remains unknown and is not converted into a zero or an absent game requirement.",
            "Quest keys and item IDs are separate namespaces and are never cross-compared.",
            "No network requests are made; all input comes from generated dist datasets.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=DIST)
    parser.add_argument("--output", type=Path, default=REPORTS / "domain-consistency-audit.json")
    args = parser.parse_args()
    try:
        datasets = {name: load_array(name, args.dist_dir) for name in REQUIRED}
        report = audit_datasets(datasets)
    except ValueError as exc:
        report = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "failed",
                  "datasets": {}, "counts": {"error_count": 1, "warning_count": 0},
                  "errors": [{"issue": "input_error", "message": str(exc)}], "warnings": [],
                  "guardrails": ["No facts were inferred or fetched from external services."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
