#!/usr/bin/env python3
"""Build an explicit quest prerequisite graph and report unresolved references."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"


def canonical(value):
    return " ".join(str(value).casefold().split())


def parse_requirement(value):
    """Return normalized quest name and required completion stage."""
    if not isinstance(value, str) or not value.strip():
        return None, None
    value = " ".join(value.split())
    if value.casefold().startswith("started:"):
        name = value.split(":", 1)[1].strip()
        return (canonical(name), "started") if name else (None, None)
    return canonical(value), "completed"


def build_graph(quests):
    by_key = {}
    by_name = defaultdict(list)
    for index, quest in enumerate(quests):
        if not isinstance(quest, dict):
            raise ValueError(f"quests[{index}] must be an object")
        key, name = quest.get("key"), quest.get("name")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"quests[{index}] has no valid key")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"quests[{index}] has no valid name")
        if key in by_key:
            raise ValueError(f"duplicate quest key: {key}")
        by_key[key] = quest
        by_name[canonical(name)].append(key)

    dependents = defaultdict(set)
    graph = {}
    unresolved = []
    for key, quest in by_key.items():
        raw_requirements = quest.get("requirements", [])
        if not isinstance(raw_requirements, list):
            unresolved.append({"quest_key": key, "requirement": repr(raw_requirements), "reason": "malformed_requirement_list"})
            raw_requirements = []
        prereq_keys = {}
        unresolved_names = []
        for requirement in raw_requirements:
            lookup_name, completion_state = parse_requirement(requirement)
            if lookup_name is None:
                unresolved_names.append(str(requirement))
                unresolved.append({"quest_key": key, "requirement": requirement, "reason": "invalid_requirement"})
                continue
            matches = by_name.get(lookup_name, [])
            if len(matches) == 1:
                prerequisite_key = matches[0]
                if prerequisite_key == key:
                    unresolved_names.append(requirement)
                    unresolved.append({"quest_key": key, "requirement": requirement, "reason": "self_reference"})
                else:
                    prereq_keys[prerequisite_key] = completion_state
                    dependents[prerequisite_key].add(key)
            elif len(matches) > 1:
                unresolved_names.append(requirement)
                unresolved.append({"quest_key": key, "requirement": requirement, "reason": "ambiguous_name", "candidate_keys": sorted(matches)})
            else:
                unresolved_names.append(requirement)
                unresolved.append({"quest_key": key, "requirement": requirement, "reason": "not_found"})
        graph[key] = {
            "quest_key": key,
            "name": quest["name"],
            "prerequisites": [
                {"quest_key": prereq, "name": by_key[prereq]["name"], "completion_state": prereq_state}
                for prereq, prereq_state in sorted(prereq_keys.items())
            ],
            "dependents": [],
            "unresolved_requirements": sorted(set(unresolved_names), key=str.casefold),
            "skill_requirements": quest.get("skill_requirements", []),
            "source_url": quest.get("source_url"),
        }
    for key in graph:
        graph[key]["dependents"] = [
            {"quest_key": child, "name": by_key[child]["name"]}
            for child in sorted(dependents.get(key, set()))
        ]

    state = {}
    stack = []
    cycles = set()
    def visit(key):
        state[key] = 1
        stack.append(key)
        for prerequisite in (x["quest_key"] for x in graph[key]["prerequisites"]):
            if state.get(prerequisite, 0) == 0:
                visit(prerequisite)
            elif state.get(prerequisite) == 1:
                cycles.add(tuple(stack[stack.index(prerequisite):] + [prerequisite]))
        stack.pop()
        state[key] = 2
    for key in sorted(graph):
        if state.get(key, 0) == 0:
            visit(key)

    duplicate_names = [
        {"name": by_key[keys[0]]["name"], "quest_keys": sorted(keys)}
        for keys in by_name.values() if len(keys) > 1
    ]
    records = [graph[key] for key in sorted(graph, key=lambda k: (graph[k]["name"].casefold(), k))]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if cycles else "passed",
        "quest_count": len(quests),
        "quests_with_prerequisites": sum(bool(row["prerequisites"]) for row in records),
        "resolved_prerequisite_edges": sum(len(row["prerequisites"]) for row in records),
        "unresolved_requirement_count": len(unresolved),
        "unresolved_requirements": unresolved[:200],
        "unresolved_examples_truncated": len(unresolved) > 200,
        "duplicate_name_groups": duplicate_names,
        "cycle_count": len(cycles),
        "cycles": [list(cycle) for cycle in sorted(cycles)[:50]],
        "note": "Relationships are matched by normalized quest name only. Unresolved and ambiguous references are retained as warnings; the graph is not proof of factual completeness.",
    }
    return records, report


def main():
    source = DIST / "quests.json"
    try:
        quests = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(quests, list):
            raise ValueError("dist/quests.json must be a JSON array")
        records, report = build_graph(quests)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(), "status": "failed",
            "quest_count": 0, "quests_with_prerequisites": 0, "resolved_prerequisite_edges": 0,
            "unresolved_requirement_count": 0, "unresolved_requirements": [],
            "unresolved_examples_truncated": False, "duplicate_name_groups": [],
            "cycle_count": 0, "cycles": [], "errors": [str(exc)],
            "note": "Quest relationship graph could not be built.",
        }
        records = []
    DIST.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (DIST / "quest-relationships.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (REPORTS / "quest-relationship-coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
