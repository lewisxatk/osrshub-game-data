#!/usr/bin/env python3
"""Build a field-level review worklist from raw quest evidence and normalized facts.

This report prioritizes review work. It never promotes raw text or links into
verified quest facts and never treats absent evidence as proof of no requirement.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
FIELDS = ("requirements", "skill_requirements", "rewards", "members", "difficulty", "quest_type")
FIELD_WEIGHT = {
    "requirements": 30,
    "skill_requirements": 30,
    "members": 18,
    "rewards": 15,
    "quest_type": 8,
    "difficulty": 8,
}


def canonical(value):
    return " ".join(str(value).casefold().split())


def usable_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def build_worklist(quests, raw_evidence):
    if not isinstance(quests, list):
        raise ValueError("normalized quests must be a JSON array")
    if not isinstance(raw_evidence, list):
        raise ValueError("raw quest evidence must be a JSON array")

    evidence_by_key = {}
    evidence_by_name = {}
    for row in raw_evidence:
        if not isinstance(row, dict):
            continue
        key, name = row.get("quest_key"), row.get("quest_name")
        if isinstance(key, str) and key.strip():
            evidence_by_key.setdefault(key.strip(), []).append(row)
        if isinstance(name, str) and name.strip():
            evidence_by_name.setdefault(canonical(name), []).append(row)

    tasks = []
    seen_quest_keys = set()
    duplicate_keys = set()
    for index, quest in enumerate(quests):
        if not isinstance(quest, dict):
            tasks.append({
                "task_id": f"invalid-record:{index}",
                "quest_key": None,
                "quest_name": None,
                "field": "record",
                "task_type": "repair_malformed_record",
                "priority_score": 100,
                "priority": "critical",
                "reason": "normalized quest record is not an object",
                "source_urls": [],
                "raw_requirement_text": None,
                "candidate_links": [],
            })
            continue

        key = quest.get("key")
        name = quest.get("name")
        key_text = key.strip() if isinstance(key, str) else ""
        name_text = name.strip() if isinstance(name, str) else ""
        if not key_text or not name_text:
            tasks.append({
                "task_id": f"invalid-identity:{index}",
                "quest_key": key if isinstance(key, str) else None,
                "quest_name": name if isinstance(name, str) else None,
                "field": "identity",
                "task_type": "repair_missing_identity",
                "priority_score": 100,
                "priority": "critical",
                "reason": "quest key and name are required before facts can be safely joined",
                "source_urls": [],
                "raw_requirement_text": None,
                "candidate_links": [],
            })
            continue
        if key_text in seen_quest_keys:
            duplicate_keys.add(key_text)
        seen_quest_keys.add(key_text)

        evidence_rows = evidence_by_key.get(key_text, [])
        if not evidence_rows:
            evidence_rows = evidence_by_name.get(canonical(name_text), [])
        evidence = evidence_rows[0] if len(evidence_rows) == 1 else None
        field_status = quest.get("field_status")
        field_status = field_status if isinstance(field_status, dict) else {}
        field_sources = quest.get("field_sources")
        field_sources = field_sources if isinstance(field_sources, dict) else {}
        quest_source = quest.get("source_url")
        if not usable_url(quest_source):
            tasks.append({
                "task_id": f"{key_text}:source_url",
                "quest_key": key_text,
                "quest_name": name_text,
                "field": "source_url",
                "task_type": "add_or_repair_quest_source",
                "priority_score": 25,
                "priority": "high",
                "reason": "quest-level source URL is missing or is not a valid HTTPS URL",
                "source_urls": [],
                "raw_requirement_text": evidence.get("requirements_text") if evidence else None,
                "candidate_links": [],
            })

        if len(evidence_rows) > 1:
            tasks.append({
                "task_id": f"{key_text}:raw-evidence-identity",
                "quest_key": key_text,
                "quest_name": name_text,
                "field": "requirements",
                "task_type": "resolve_ambiguous_raw_evidence",
                "priority_score": 95,
                "priority": "critical",
                "reason": f"{len(evidence_rows)} raw evidence rows match this quest identity; do not choose one automatically",
                "source_urls": sorted({row.get("source_url") for row in evidence_rows if usable_url(row.get("source_url"))}),
                "raw_requirement_text": None,
                "candidate_links": [],
            })

        for field in FIELDS:
            state = field_status.get(field)
            source = field_sources.get(field)
            valid_source = usable_url(source)
            value = quest.get(field)
            if state != "known":
                tasks.append({
                    "task_id": f"{key_text}:{field}:verify",
                    "quest_key": key_text,
                    "quest_name": name_text,
                    "field": field,
                    "task_type": "verify_unknown_field",
                    "priority_score": FIELD_WEIGHT[field] + (8 if evidence and field in ("requirements", "skill_requirements") else 0),
                    "priority": "critical" if FIELD_WEIGHT[field] >= 30 else "high" if FIELD_WEIGHT[field] >= 15 else "medium",
                    "reason": "field is unknown or lacks an explicit known state; absence is not proof of an empty requirement",
                    "source_urls": sorted({url for url in (quest_source, evidence.get("source_url") if evidence else None) if usable_url(url)}),
                    "raw_requirement_text": evidence.get("requirements_text") if evidence and field in ("requirements", "skill_requirements") else None,
                    "candidate_links": evidence.get("requirement_links", []) if evidence and field in ("requirements", "skill_requirements") and isinstance(evidence.get("requirement_links"), list) else [],
                })
            elif not valid_source:
                tasks.append({
                    "task_id": f"{key_text}:{field}:source",
                    "quest_key": key_text,
                    "quest_name": name_text,
                    "field": field,
                    "task_type": "add_field_level_source",
                    "priority_score": max(5, FIELD_WEIGHT[field] - 5),
                    "priority": "high" if FIELD_WEIGHT[field] >= 18 else "medium",
                    "reason": "field is marked known but has no valid field-specific HTTPS evidence pointer",
                    "source_urls": sorted({url for url in (quest_source, evidence.get("source_url") if evidence else None) if usable_url(url)}),
                    "raw_requirement_text": evidence.get("requirements_text") if evidence and field in ("requirements", "skill_requirements") else None,
                    "candidate_links": [],
                })

            if state == "known" and field in ("requirements", "skill_requirements", "rewards"):
                is_empty = isinstance(value, (list, dict)) and len(value) == 0
                if is_empty and not valid_source:
                    # The source task above already captures the missing evidence; make the
                    # uncertainty about a negative claim explicit for reviewers.
                    tasks.append({
                        "task_id": f"{key_text}:{field}:empty-claim",
                        "quest_key": key_text,
                        "quest_name": name_text,
                        "field": field,
                        "task_type": "verify_known_empty_claim",
                        "priority_score": FIELD_WEIGHT[field] + 10,
                        "priority": "critical" if FIELD_WEIGHT[field] >= 30 else "high",
                        "reason": "an empty known value needs evidence that the source explicitly supports the absence",
                        "source_urls": sorted({url for url in (quest_source, evidence.get("source_url") if evidence else None) if usable_url(url)}),
                        "raw_requirement_text": evidence.get("requirements_text") if evidence and field == "requirements" else None,
                        "candidate_links": [],
                    })

        if evidence:
            links = evidence.get("requirement_links", [])
            if isinstance(links, list) and links:
                tasks.append({
                    "task_id": f"{key_text}:raw-links",
                    "quest_key": key_text,
                    "quest_name": name_text,
                    "field": "requirements",
                    "task_type": "review_unverified_prerequisite_candidates",
                    "priority_score": 42,
                    "priority": "critical",
                    "reason": "raw source links are candidates only and require manual confirmation before graph promotion",
                    "source_urls": sorted({url for url in [evidence.get("source_url")] + [link.get("url") for link in links if isinstance(link, dict)] if usable_url(url)}),
                    "raw_requirement_text": evidence.get("requirements_text") if isinstance(evidence.get("requirements_text"), str) else None,
                    "candidate_links": links,
                })
        else:
            tasks.append({
                "task_id": f"{key_text}:raw-evidence",
                "quest_key": key_text,
                "quest_name": name_text,
                "field": "requirements",
                "task_type": "collect_raw_requirement_evidence",
                "priority_score": 40,
                "priority": "critical",
                "reason": "no unique raw requirement evidence row could be matched by quest key or normalized name",
                "source_urls": [],
                "raw_requirement_text": None,
                "candidate_links": [],
            })

    for key in sorted(duplicate_keys):
        tasks.append({
            "task_id": f"{key}:duplicate-key",
            "quest_key": key,
            "quest_name": None,
            "field": "identity",
            "task_type": "resolve_duplicate_quest_key",
            "priority_score": 100,
            "priority": "critical",
            "reason": "duplicate normalized quest keys make cross-domain joins ambiguous",
            "source_urls": [],
            "raw_requirement_text": None,
            "candidate_links": [],
        })

    tasks.sort(key=lambda row: (-row["priority_score"], str(row.get("quest_name") or "").casefold(), row["task_id"]))
    counts = {level: sum(row["priority"] == level for row in tasks) for level in ("critical", "high", "medium", "low")}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": "review_required" if tasks else "passed",
        "quest_count": len(quests),
        "raw_evidence_count": len(raw_evidence),
        "task_count": len(tasks),
        "priority_counts": counts,
        "tasks": tasks[:5000],
        "truncated": len(tasks) > 5000,
        "guardrails": [
            "This worklist prioritizes review; it does not verify OSRS facts.",
            "Raw requirement text and links are unverified candidates and are never promoted automatically.",
            "Unknown or missing facts are not interpreted as no requirements, rewards, or restrictions.",
            "A source URL is a provenance pointer, not independent certification of factual correctness.",
            "Known-empty claims require explicit source support; empty data alone is not evidence of absence.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quests", type=Path, default=DIST / "quests.json")
    parser.add_argument("--evidence", type=Path, default=RAW / "quest-requirement-evidence.json")
    parser.add_argument("--output", type=Path, default=REPORTS / "quest-evidence-worklist.json")
    args = parser.parse_args()
    try:
        quests = json.loads(args.quests.read_text(encoding="utf-8"))
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        result = build_worklist(quests, evidence)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0.0",
            "status": "failed",
            "quest_count": 0,
            "raw_evidence_count": 0,
            "task_count": 0,
            "priority_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "tasks": [],
            "truncated": False,
            "errors": [str(exc)],
            "guardrails": ["Failed to build worklist; no missing fact may be interpreted as absent."],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "tasks"}, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
