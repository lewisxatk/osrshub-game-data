#!/usr/bin/env python3
"""Validate the combat mechanics registry's provenance and verification claims."""
from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "combat-mechanics-registry.json"
SCHEMA = ROOT / "schemas" / "combat-mechanics-registry.schema.json"


def validate_registry(registry: dict, schema: dict) -> list[str]:
    errors = [
        f"schema: {error.message}"
        for error in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(registry)
    ]
    mechanics = registry.get("mechanics", [])
    ids = [row.get("mechanic_id") for row in mechanics]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    errors.extend(f"duplicate mechanic_id: {value}" for value in duplicates)
    for row in mechanics:
        key = row.get("mechanic_id", "<unknown>")
        status = row.get("verification_status")
        implementation = row.get("implementation_status")
        sources = row.get("source_references", [])
        fixtures = row.get("regression_fixtures", [])
        if status == "verified" and not sources:
            errors.append(f"{key}: verified mechanics require at least one source reference")
        if status == "verified" and not fixtures:
            errors.append(f"{key}: verified mechanics require at least one regression fixture")
        if status == "verified" and implementation == "not_implemented":
            errors.append(f"{key}: a not-implemented mechanic cannot be verified as implemented")
        if status == "unsupported" and implementation == "implemented_scoped":
            errors.append(f"{key}: implemented_scoped mechanics cannot be marked unsupported")
        if status == "unsupported" and not row.get("limitations"):
            errors.append(f"{key}: unsupported mechanics must state limitations")
        if implementation == "not_implemented" and status == "verified":
            errors.append(f"{key}: not-implemented mechanics cannot be marked verified")
    if registry.get("registry_status") == "verified_subset" and any(
        row.get("verification_status") != "verified" for row in mechanics
    ):
        errors.append("verified_subset requires every listed mechanic to be verified")
    return errors


def main() -> int:
    try:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Combat mechanics registry could not be loaded: {exc}")
        return 1
    errors = validate_registry(registry, schema)
    if errors:
        print("Combat mechanics registry validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Combat mechanics registry valid: {len(registry['mechanics'])} entries; no unsupported mechanics promoted to verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
