#!/usr/bin/env python3
"""Summarize implementation and verification readiness for registered OSRS combat mechanics.

This is a gap report, not proof that an equation or game fact is correct.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "combat-mechanics-registry.json"
DEFAULT_OUTPUT = ROOT / "reports" / "combat-mechanics-readiness.json"
IMPLEMENTATION_STATES = ("implemented_scoped", "data_dependent", "not_implemented")
VERIFICATION_STATES = ("verified", "in_review", "unverified", "unsupported")


def percent(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def build_report(registry: dict) -> dict:
    mechanics = registry.get("mechanics")
    if not isinstance(mechanics, list):
        raise ValueError("registry mechanics must be an array")
    implementation_counts, verification_counts = Counter(), Counter()
    domain_rows, gaps, seen_ids, errors = defaultdict(list), [], set(), []
    for index, row in enumerate(mechanics):
        if not isinstance(row, dict):
            errors.append(f"mechanic at index {index} is not an object")
            continue
        mechanic_id = row.get("mechanic_id")
        if not isinstance(mechanic_id, str) or not mechanic_id.strip():
            errors.append(f"mechanic at index {index} has no valid mechanic_id")
            mechanic_id = f"invalid-record-{index}"
        if mechanic_id in seen_ids:
            errors.append(f"duplicate mechanic_id: {mechanic_id}")
        seen_ids.add(mechanic_id)
        implementation, verification = row.get("implementation_status"), row.get("verification_status")
        if implementation not in IMPLEMENTATION_STATES:
            errors.append(f"{mechanic_id}: invalid implementation_status")
        if verification not in VERIFICATION_STATES:
            errors.append(f"{mechanic_id}: invalid verification_status")
        implementation_counts[implementation] += 1
        verification_counts[verification] += 1
        sources = row.get("source_references") if isinstance(row.get("source_references"), list) else []
        fixtures = row.get("regression_fixtures") if isinstance(row.get("regression_fixtures"), list) else []
        blockers = []
        if verification != "verified": blockers.append(f"verification_status is {verification!r}, not 'verified'")
        if not sources: blockers.append("no source references")
        if not fixtures: blockers.append("no regression fixtures")
        if implementation == "not_implemented": blockers.append("mechanic is not implemented")
        if not isinstance(row.get("scope"), str) or not row["scope"].strip(): blockers.append("scope is missing")
        if not isinstance(row.get("limitations"), list) or not row["limitations"]: blockers.append("limitations are not documented")
        domain = row.get("domain") if isinstance(row.get("domain"), str) else "unknown"
        domain_rows[domain].append({"mechanic_id": mechanic_id, "implementation_status": implementation, "verification_status": verification, "source_reference_count": len(sources), "regression_fixture_count": len(fixtures)})
        if blockers:
            gaps.append({"mechanic_id": mechanic_id, "label": row.get("label") if isinstance(row.get("label"), str) else mechanic_id, "domain": domain, "implementation_status": implementation, "verification_status": verification, "source_reference_count": len(sources), "regression_fixture_count": len(fixtures), "blockers": blockers})
    total = len(mechanics)
    verified, implemented = verification_counts["verified"], implementation_counts["implemented_scoped"]
    domains = []
    for name in sorted(domain_rows):
        rows = domain_rows[name]
        domains.append({"domain": name, "mechanic_count": len(rows), "verified_count": sum(row["verification_status"] == "verified" for row in rows), "implemented_scoped_count": sum(row["implementation_status"] == "implemented_scoped" for row in rows), "source_reference_count": sum(row["source_reference_count"] for row in rows), "regression_fixture_count": sum(row["regression_fixture_count"] for row in rows), "mechanics": rows})
    status = "failed" if errors else "review_required" if gaps else "passed"
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "schema_version": "1.0.0", "status": status, "registry_status": registry.get("registry_status", "unknown"), "mechanic_count": total, "implementation_counts": {key: implementation_counts[key] for key in IMPLEMENTATION_STATES}, "verification_counts": {key: verification_counts[key] for key in VERIFICATION_STATES}, "implemented_scoped_percent": percent(implemented, total), "verified_percent": percent(verified, total), "domain_summaries": domains, "verification_gaps": sorted(gaps, key=lambda item: (item["verification_status"] == "verified", item["domain"], item["mechanic_id"])), "error_count": len(errors), "errors": errors[:100], "guardrails": ["This report measures registry completeness, not factual correctness of OSRS combat mechanics.", "A source reference is an evidence pointer and does not by itself prove the rule or implementation is correct.", "A verified label requires separate human review, source references, and regression fixtures.", "Scoped implementation does not imply complete coverage of boosts, equipment effects, target phases, immunities, or special cases.", "Unknown and unsupported mechanics must remain visible; this report never upgrades their status."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        if not isinstance(registry, dict): raise ValueError("registry root must be an object")
        report = build_report(registry)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Could not build combat mechanics readiness report: {exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0

if __name__ == "__main__":
    raise SystemExit(main())