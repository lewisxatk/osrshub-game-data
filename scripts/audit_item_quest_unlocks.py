#!/usr/bin/env python3
"""Audit item-to-quest unlock evidence without inferring missing requirements.

This checks record shape, evidence pointers, duplicate item IDs, and explicit
knowledge states. It is a data-quality gate, not an independent fact verifier.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_INPUT = ROOT / "examples" / "combat-studio-dps-unlocks.example.json"
REPORTS = ROOT / "reports"
VALID_STATES = {"known", "known_empty", "unknown"}


def is_item_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def valid_https_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def audit_item_quest_unlocks(records):
    errors, warnings = [], []
    if not isinstance(records, list):
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0.0",
            "status": "failed",
            "record_count": 0,
            "knowledge_counts": {"known": 0, "known_empty": 0, "unknown": 0},
            "source_url_coverage_percent": 0.0,
            "duplicate_item_ids": [],
            "errors": ["Item-to-quest unlock input must be a JSON array."],
            "warnings": [],
            "guardrails": guardrails(),
        }

    seen_ids = set()
    duplicate_ids = set()
    counts = {"known": 0, "known_empty": 0, "unknown": 0}
    source_count = 0
    evidence_gaps = 0
    placeholder_sources = 0

    for index, row in enumerate(records):
        if not isinstance(row, dict):
            errors.append(f"Record at index {index} is not an object.")
            continue

        item_id = row.get("item_id")
        if not is_item_id(item_id):
            errors.append(f"Record at index {index} has an invalid item_id.")
        elif item_id in seen_ids:
            duplicate_ids.add(item_id)
        seen_ids.add(item_id)

        state = row.get("requirements_status")
        if state not in VALID_STATES:
            errors.append(f"Item {item_id!r} has an invalid requirements_status.")
            continue
        counts[state] += 1

        required_quests = row.get("required_quests")
        if not isinstance(required_quests, list) or any(
            not isinstance(name, str) or not name.strip() for name in required_quests
        ):
            errors.append(f"Item {item_id!r} must have required_quests as an array of non-empty quest names.")
            required_quests = []

        normalized = [" ".join(name.casefold().split()) for name in required_quests]
        if len(normalized) != len(set(normalized)):
            warnings.append(f"Item {item_id!r} contains duplicate quest names after case/space normalization.")

        if state == "known" and not required_quests:
            errors.append(f"Item {item_id!r} is marked known but has no required quest; use known_empty only when a source confirms none.")
        elif state == "known_empty" and required_quests:
            errors.append(f"Item {item_id!r} is marked known_empty but lists required quests.")
        elif state == "unknown" and required_quests:
            errors.append(f"Item {item_id!r} is marked unknown but lists quest requirements.")

        source_url = row.get("source_url")
        if valid_https_url(source_url):
            source_count += 1
            host = urlparse(source_url).hostname or ""
            if host == "example.test" or host.endswith(".example.test"):
                placeholder_sources += 1
        else:
            evidence_gaps += 1
            warnings.append(f"Item {item_id!r} has no valid HTTPS source URL.")

    for item_id in sorted(duplicate_ids):
        errors.append(f"Duplicate item_id {item_id} appears more than once in the unlock dataset.")

    if counts["unknown"]:
        warnings.append(f"{counts['unknown']} item records have unknown quest-requirement status.")
    if placeholder_sources:
        warnings.append(f"{placeholder_sources} records use reserved example.test URLs; they are fixtures, not production evidence.")
    if not records:
        warnings.append("No item-to-quest unlock records were supplied; coverage is unknown, not zero requirements.")
    if evidence_gaps:
        warnings.append(f"{evidence_gaps} records lack a valid HTTPS source URL.")

    total = len(records)
    coverage = round(100.0 * source_count / total, 2) if total else 0.0
    status = "failed" if errors else "review_required" if warnings else "passed"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": status,
        "record_count": total,
        "knowledge_counts": counts,
        "source_url_coverage_percent": coverage,
        "duplicate_item_ids": sorted(duplicate_ids),
        "errors": errors[:500],
        "warnings": warnings[:500],
        "guardrails": guardrails(),
    }


def guardrails():
    return [
        "A missing item-to-quest record is unknown, not proof that no quest unlock is required.",
        "known_empty is valid only when evidence explicitly supports that no quest requirement applies.",
        "HTTPS source URLs are evidence pointers, not independent verification of the claim.",
        "Reserved example.test URLs are illustrative fixtures and never count as production evidence.",
        "This audit does not infer item eligibility, quest prerequisites, or combat accuracy.",
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=EXAMPLE_INPUT)
    parser.add_argument("--output", type=Path, default=REPORTS / "item-quest-unlock-audit.json")
    args = parser.parse_args()
    try:
        records = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = audit_item_quest_unlocks(None)
        result["errors"].append(f"Could not load item-to-quest unlock input: {exc}")
        result["status"] = "failed"
    else:
        result = audit_item_quest_unlocks(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
