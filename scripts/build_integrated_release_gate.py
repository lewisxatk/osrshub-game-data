#!/usr/bin/env python3
"""Summarize generated data-quality reports into one conservative release gate.

This gate checks whether expected reports exist and whether their reported status
is structurally acceptable. It does not claim that imported OSRS facts are true.
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUTS = {
    "database_census": "database-census.json",
    "database_integrity": "database-integrity.json",
    "database_record_quality": "database-record-quality.json",
    "source_freshness": "source-snapshot-freshness.json",
    "domain_coverage": "domain-coverage-matrix.json",
    "hub_readiness": "hub-readiness-matrix.json",
    "quest_evidence": "quest-evidence-reconciliation.json",
    "monster_identity": "monster-identity-audit.json",
    "monster_drops": "monster-drop-link-audit.json",
    "combat_readiness": "combat-mechanics-readiness.json",
    "combat_upgrade_readiness": "combat-upgrade-readiness.json",
    "combat_studio_readiness_matrix": "combat-studio-readiness-matrix.json",
}
ACCEPTED = {"passed", "pass", "success", "review_required", "warning", "warnings", "passed_with_warnings"}
BLOCKING = {"failed", "failure", "error", "invalid", "blocked"}

def load_report(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"Missing report: {path.as_posix()}"
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"Unreadable report {path.as_posix()}: {exc}"
    if not isinstance(value, dict):
        return None, f"Report root must be an object: {path.as_posix()}"
    return value, None

def classify(report, error):
    if error:
        return "missing_or_invalid"
    raw = str(report.get("status", "unspecified")).strip().lower()
    if raw in BLOCKING:
        return "blocking"
    if raw in ACCEPTED:
        return "review_required" if raw == "review_required" else "acceptable"
    return "review_required"

def build_gate(reports_dir: Path, inputs=None):
    inputs = inputs or DEFAULT_INPUTS
    components, errors, warnings = {}, [], []
    for key, filename in inputs.items():
        report, error = load_report(reports_dir / filename)
        state = classify(report, error)
        entry = {"file": filename, "state": state}
        if error:
            entry["message"] = error
            errors.append({"component": key, "message": error})
        else:
            entry["reported_status"] = report.get("status", "unspecified")
            for field in ("error_count", "warning_count", "record_count", "dataset_file_count", "gap_count"):
                value = report.get(field)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    entry[field] = value
            if state == "blocking":
                message = f"{key} reports blocking status {report.get('status')!r}"
                errors.append({"component": key, "message": message})
            elif state == "review_required":
                warnings.append({"component": key, "message": "Report requires interpretation or review; do not treat as verified facts."})
            elif state == "acceptable" and report.get("warning_count", 0):
                warnings.append({"component": key, "message": f"Report contains {report.get('warning_count')} warning(s)."})
        components[key] = entry
    blocking_count = sum(v["state"] in {"missing_or_invalid", "blocking"} for v in components.values())
    review_count = sum(v["state"] == "review_required" for v in components.values())
    status = "failed" if blocking_count else "review_required" if review_count or warnings else "passed"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "status": status,
        "interpretation": "Structural release signal only; passing does not certify factual accuracy, completeness, or source freshness.",
        "component_count": len(components),
        "blocking_component_count": blocking_count,
        "review_required_component_count": review_count,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "components": components,
        "errors": errors,
        "warnings": warnings,
        "guardrails": [
            "Missing reports are blocking, not silently treated as empty datasets.",
            "Review-required source evidence is not promoted to verified game facts.",
            "Counts across overlapping files are not a global unique-entity count.",
            "A successful release gate is not proof that combat formulas are complete or accurate."
        ]
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/database-integrated-release-gate.json")
    args = parser.parse_args()
    result = build_gate(args.reports_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Integrated release gate: {result['status']} ({result['component_count']} components, {result['error_count']} errors, {result['warning_count']} warnings)")
    if result["status"] == "failed":
        raise SystemExit(1)
if __name__ == "__main__":
    main()
