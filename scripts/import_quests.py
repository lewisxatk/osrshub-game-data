#!/usr/bin/env python3
"""Import traceable quest records from a pinned, explicitly configured source file."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
DIST = ROOT / "dist"
REPORTS = ROOT / "reports"
SOURCE_NAME = "quests"
SOURCE_PATH = RAW / "quests.json"
SCHEMA_PATH = ROOT / "schemas" / "quests.schema.json"


def normalize_record(row):
    """Normalize a source record while retaining unknowns instead of inventing facts."""
    if not isinstance(row, dict):
        return None, "record is not an object"
    name = row.get("name") or row.get("title")
    if not isinstance(name, str) or not name.strip():
        return None, "missing quest name"
    name = name.strip()
    raw_id = row.get("id", row.get("quest_id"))
    if raw_id is None:
        # A stable slug is an identity key, not a claim that an upstream numeric ID exists.
        key = name.casefold().replace(" ", "-")
    else:
        key = str(raw_id).strip()
    if not key:
        return None, "missing identity key"
    def string_list(value):
        if not isinstance(value, list):
            return []
        return sorted({x.strip() for x in value if isinstance(x, str) and x.strip()})
    requirements_key = "requirements" if "requirements" in row else "quest_requirements" if "quest_requirements" in row else None
    requirements = string_list(row.get(requirements_key)) if requirements_key else []
    skills = []
    raw_skills = row.get("skill_requirements")
    if isinstance(raw_skills, dict):
        for skill, level in sorted(raw_skills.items()):
            try:
                level = int(level)
            except (TypeError, ValueError):
                continue
            if level >= 0:
                skills.append({"skill": str(skill), "level": level})
    rewards = string_list(row.get("rewards"))
    # Presence means the source explicitly supplied the field; it does not independently certify accuracy.
    field_status = {
        "requirements": "known" if requirements_key is not None and isinstance(row.get(requirements_key), list) else "unknown",
        "skill_requirements": "known" if isinstance(raw_skills, dict) else "unknown",
        "rewards": "known" if isinstance(row.get("rewards"), list) else "unknown",
        "members": "known" if isinstance(row.get("members"), bool) else "unknown",
        "difficulty": "known" if isinstance(row.get("difficulty"), str) and row.get("difficulty").strip() else "unknown",
        "quest_type": "known" if isinstance(row.get("quest_type", row.get("type")), str) and str(row.get("quest_type", row.get("type"))).strip() else "unknown",
    }
    raw_field_sources = row.get("field_sources", {})
    field_sources = {}
    if isinstance(raw_field_sources, dict):
        for field, url in raw_field_sources.items():
            if field in field_status and isinstance(url, str) and url.strip().startswith("https://"):
                field_sources[field] = url.strip()
    members = row.get("members") if isinstance(row.get("members"), bool) else None
    difficulty = row.get("difficulty") if isinstance(row.get("difficulty"), str) else None
    quest_type = row.get("quest_type", row.get("type"))
    quest_type = quest_type if isinstance(quest_type, str) else None
    source_url = row.get("url") or row.get("wiki_url") or row.get("source_url")
    source_url = source_url.strip() if isinstance(source_url, str) and source_url.strip().startswith("https://") else None
    normalized = {
        "key": key,
        "name": name,
        "requirements": requirements,
        "skill_requirements": skills,
        "rewards": rewards,
        "members": members,
        "difficulty": difficulty,
        "quest_type": quest_type,
        "source_url": source_url,
        "source_fields": sorted(row.keys()),
        "field_status": field_status,
        "field_sources": field_sources,
    }
    return normalized, None


def load_source(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Permit keyed source objects but do not silently accept arbitrary scalar values.
        rows = []
        for key, value in data.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("id", key)
                rows.append(row)
        return rows
    raise ValueError("quest source must be a JSON array or object of records")


def main():
    errors = []
    warnings = []
    records = []
    source_sha256 = None
    if not SOURCE_PATH.exists():
        warnings.append("No quest source snapshot configured yet; generated dataset is empty until a source adapter is supplied")
    else:
        payload = SOURCE_PATH.read_bytes()
        source_sha256 = hashlib.sha256(payload).hexdigest()
        try:
            raw_rows = load_source(SOURCE_PATH)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raw_rows = []
            errors.append(f"Cannot load quest source: {exc}")
        seen = set()
        for index, row in enumerate(raw_rows):
            normalized, error = normalize_record(row)
            if error:
                warnings.append({"index": index, "reason": error})
                continue
            if normalized["key"] in seen:
                errors.append(f"duplicate quest key {normalized['key']}")
                continue
            seen.add(normalized["key"])
            records.append(normalized)
        records.sort(key=lambda row: (row["name"].casefold(), row["key"]))
        if not records:
            warnings.append("No valid quest records were imported")
    DIST.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (DIST / "quests.json").write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if errors else "missing_source" if not SOURCE_PATH.exists() else "passed_with_warnings" if warnings else "passed",
        "source": "sources/raw/quests.json",
        "source_sha256": source_sha256,
        "source_record_count": len(raw_rows) if SOURCE_PATH.exists() and "raw_rows" in locals() else 0,
        "imported_record_count": len(records),
        "records_with_source_url": sum(bool(row["source_url"]) for row in records),
        "records_with_requirements": sum(bool(row["requirements"]) for row in records),
        "records_with_skill_requirements": sum(row["field_status"]["skill_requirements"] == "known" for row in records),
        "field_status_counts": {field: {state: sum(row["field_status"][field] == state for row in records) for state in ("known", "unknown")} for field in ("requirements", "skill_requirements", "rewards", "members", "difficulty", "quest_type")},
        "field_source_url_counts": {field: sum(bool(row.get("field_sources", {}).get(field)) for row in records) for field in ("requirements", "skill_requirements", "rewards", "members", "difficulty", "quest_type")},
        "warnings": warnings[:100],
        "warning_count": len(warnings),
        "errors": errors,
        "note": "This adapter only imports a supplied snapshot. It does not download or invent quest facts; missing source data remains unknown.",
    }
    (REPORTS / "quest-coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
