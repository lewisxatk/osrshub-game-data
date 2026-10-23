#!/usr/bin/env python3
"""Audit quest skill-text candidates for provenance and internal consistency.

Candidate matches remain review-only: this audit never promotes them into quest facts.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
REPORTS = ROOT / "reports"
SOURCE_HOST = "oldschool.runescape.wiki"
EXPECTED_CANDIDATE_STATUS = "raw_text_candidate_needs_manual_review"
VALID_CATALOGUE_STATUSES = {"matched", "unmatched_catalogue_title"}


def valid_source_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https"
            and parsed.hostname == SOURCE_HOST
            and not parsed.username
            and not parsed.password
            and not parsed.port
        )
    except ValueError:
        return False


def build_audit(candidates, evidence):
    if not isinstance(candidates, list):
        raise ValueError("candidate input must be a JSON array")
    if not isinstance(evidence, list):
        raise ValueError("quest evidence input must be a JSON array")

    errors, unmatched, repeated, duplicate_candidates = [], [], [], []
    by_skill = Counter()
    by_quest_skill = defaultdict(list)
    evidence_by_key = defaultdict(list)

    for index, row in enumerate(evidence):
        if not isinstance(row, dict):
            errors.append({"source": "evidence", "index": index, "reason": "record_not_object"})
            continue
        key = row.get("quest_key")
        if not isinstance(key, str) or not key.strip():
            errors.append({"source": "evidence", "index": index, "reason": "missing_quest_key"})
            continue
        evidence_by_key[key].append(row)
        if not valid_source_url(row.get("source_url")):
            errors.append({"source": "evidence", "index": index, "quest_key": key, "reason": "missing_or_untrusted_source_url"})

    seen = set()
    candidate_keys = set()
    for index, row in enumerate(candidates):
        if not isinstance(row, dict):
            errors.append({"source": "candidate", "index": index, "reason": "record_not_object"})
            continue
        key, name, skill, level = row.get("quest_key"), row.get("quest_name"), row.get("skill"), row.get("level")
        if (not isinstance(key, str) or not key.strip()
                or not isinstance(name, str) or not name.strip()
                or not isinstance(skill, str) or not skill.strip()
                or type(level) is not int or not 1 <= level <= 99):
            errors.append({"source": "candidate", "index": index, "reason": "missing_or_invalid_key_name_skill_level"})
            continue

        candidate_keys.add(key)
        by_skill[skill] += 1
        by_quest_skill[(key, skill.casefold())].append(level)
        if row.get("candidate_status") != EXPECTED_CANDIDATE_STATUS:
            errors.append({"source": "candidate", "index": index, "quest_key": key, "reason": "candidate_not_explicitly_review_only"})
        if row.get("catalogue_match_status") not in VALID_CATALOGUE_STATUSES:
            errors.append({"source": "candidate", "index": index, "quest_key": key, "reason": "invalid_catalogue_match_status"})
        if not valid_source_url(row.get("source_url")):
            errors.append({"source": "candidate", "index": index, "quest_key": key, "reason": "missing_or_untrusted_source_url"})
        if key not in evidence_by_key:
            errors.append({"source": "candidate", "index": index, "quest_key": key, "reason": "candidate_has_no_matching_evidence_record"})
        else:
            source_rows = evidence_by_key[key]
            if len(source_rows) != 1:
                errors.append({"source": "candidate", "index": index, "quest_key": key, "reason": "evidence_key_is_not_unique"})
            elif row.get("source_url") != source_rows[0].get("source_url"):
                errors.append({"source": "candidate", "index": index, "quest_key": key, "reason": "candidate_source_does_not_match_evidence_source"})
            if row.get("catalogue_match_status") == "matched" and len(source_rows) == 1:
                if name != source_rows[0].get("quest_name"):
                    errors.append({"source": "candidate", "index": index, "quest_key": key, "reason": "matched_candidate_name_disagrees_with_evidence"})

        identity = (key, skill.casefold(), level, row.get("matched_text"))
        if identity in seen:
            duplicate_candidates.append({"index": index, "quest_key": key, "skill": skill, "level": level})
            errors.append({"source": "candidate", "index": index, "quest_key": key, "reason": "duplicate_candidate_record"})
        seen.add(identity)
        if row.get("catalogue_match_status") != "matched":
            unmatched.append({
                "quest_key": key, "quest_name": name, "skill": skill, "level": level,
                "catalogue_match_status": row.get("catalogue_match_status", "unknown")
            })

    for (key, skill), levels in sorted(by_quest_skill.items()):
        if len(levels) > 1:
            repeated.append({
                "quest_key": key, "skill": skill, "levels": sorted(levels),
                "reason": "multiple_text_matches_for_same_quest_and_skill_need_review"
            })

    evidence_keys = set(evidence_by_key)
    no_candidate_keys = sorted(evidence_keys - candidate_keys)
    duplicate_evidence_keys = sorted(key for key, rows in evidence_by_key.items() if len(rows) > 1)
    for key in duplicate_evidence_keys:
        errors.append({"source": "evidence", "quest_key": key, "reason": "duplicate_evidence_key"})

    status = "failed" if errors else "review_required" if unmatched or repeated else "passed_with_review_limits"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_url": "https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest",
        "candidate_count": len(candidates),
        "evidence_quest_count": len(evidence_keys),
        "distinct_quests_with_candidates": len(candidate_keys),
        "evidence_quests_without_skill_candidates": len(no_candidate_keys),
        "evidence_quest_keys_without_skill_candidates": no_candidate_keys[:100],
        "candidate_counts_by_skill": dict(sorted(by_skill.items())),
        "errors": errors,
        "unmatched_catalogue_candidates": unmatched,
        "repeated_quest_skill_matches": repeated,
        "duplicate_candidates": duplicate_candidates,
        "checks": {
            "candidate_status_preserved": not any(x.get("reason") == "candidate_not_explicitly_review_only" for x in errors),
            "candidate_provenance_matches_raw_evidence": not any("source" in x.get("reason", "") for x in errors),
            "does_not_promote_candidates_to_facts": True,
            "no_candidate_match_is_not_proof_of_no_skill_requirement": True
        },
        "limitations": [
            "A text match does not establish whether a level is needed to start or complete a quest.",
            "A missing match does not prove that a quest has no skill requirements.",
            "Repeated matches and unmatched catalogue titles are review queues, not automatic errors in game facts.",
            "This audit checks provenance and internal consistency, not OSRS factual accuracy."
        ]
    }


def main():
    try:
        candidates = json.loads((RAW / "quest-skill-requirement-candidates.json").read_text(encoding="utf-8"))
        evidence = json.loads((RAW / "quest-requirement-evidence.json").read_text(encoding="utf-8"))
        report = build_audit(candidates, evidence)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Quest skill candidate audit failed: {exc}", file=sys.stderr)
        return 1
    REPORTS.mkdir(parents=True, exist_ok=True)
    target = REPORTS / "quest-skill-candidate-audit.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
