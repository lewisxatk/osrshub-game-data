#!/usr/bin/env python3
"""Audit extracted quest skill candidates without treating them as verified facts."""
from __future__ import annotations
import json, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
REPORTS = ROOT / "reports"


def build_audit(candidates, evidence):
    if not isinstance(candidates, list):
        raise ValueError("candidate input must be a JSON array")
    if not isinstance(evidence, list):
        raise ValueError("quest evidence input must be a JSON array")
    by_skill = Counter()
    by_quest_skill = defaultdict(list)
    malformed = []
    unmatched = []
    for index, row in enumerate(candidates):
        if not isinstance(row, dict):
            malformed.append({"index": index, "reason": "candidate_not_object"})
            continue
        quest_key, skill, level = row.get("quest_key"), row.get("skill"), row.get("level")
        if not isinstance(quest_key, str) or not quest_key or not isinstance(skill, str) or not skill or type(level) is not int or not 1 <= level <= 99:
            malformed.append({"index": index, "reason": "missing_or_invalid_key_skill_level"})
            continue
        by_skill[skill] += 1
        by_quest_skill[(quest_key, skill.casefold())].append(level)
        if row.get("catalogue_match_status") != "matched":
            unmatched.append({"quest_key": quest_key, "quest_name": row.get("quest_name", ""), "skill": skill, "level": level, "catalogue_match_status": row.get("catalogue_match_status", "unknown")})
    repeated = []
    for (quest_key, skill), levels in sorted(by_quest_skill.items()):
        if len(levels) > 1:
            repeated.append({"quest_key": quest_key, "skill": skill, "levels": sorted(levels), "reason": "multiple_text_matches_for_same_quest_and_skill_need_review"})
    evidence_keys = {str(row.get("quest_key", "")) for row in evidence if isinstance(row, dict)}
    candidate_keys = {str(row.get("quest_key", "")) for row in candidates if isinstance(row, dict)}
    no_candidate_quests = len(evidence_keys - candidate_keys)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "review_required" if malformed or unmatched or repeated else "passed_with_review_limits",
        "source_url": "https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest",
        "candidate_count": len(candidates),
        "evidence_quest_count": len(evidence_keys),
        "distinct_quests_with_candidates": len(candidate_keys),
        "evidence_quests_without_skill_candidates": no_candidate_quests,
        "candidate_counts_by_skill": dict(sorted(by_skill.items())),
        "malformed_candidates": malformed,
        "unmatched_catalogue_candidates": unmatched,
        "repeated_quest_skill_matches": repeated,
        "checks": {
            "candidate_status_preserved": all(isinstance(row, dict) and row.get("candidate_status") == "raw_text_candidate_needs_manual_review" for row in candidates),
            "does_not_promote_candidates_to_facts": True,
            "no_candidate_match_is_not_proof_of_no_skill_requirement": True
        },
        "limitations": [
            "A text match does not establish whether a level is needed to start or complete a quest.",
            "A missing match does not prove that a quest has no skill requirements.",
            "Repeated matches and unmatched catalogue titles are review queues, not automatic errors in game facts.",
            "This audit checks candidate structure and coverage, not OSRS factual accuracy."
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
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["malformed_candidates"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
