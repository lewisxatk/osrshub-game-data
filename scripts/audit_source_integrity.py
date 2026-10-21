#!/usr/bin/env python3
"""Verify downloaded source snapshots against their retrieval manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"


def audit_manifest(manifest, raw_dir: Path):
    errors = []
    checked = {}
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), dict):
        return {"status": "failed", "checked_sources": {}, "errors": ["manifest must contain a sources object"]}
    for name, metadata in sorted(manifest["sources"].items()):
        if not isinstance(metadata, dict):
            errors.append(f"{name}: metadata must be an object")
            continue
        filename = metadata.get("file")
        expected_hash = metadata.get("sha256")
        if not isinstance(filename, str) or Path(filename).name != filename:
            errors.append(f"{name}: invalid or unsafe filename")
            continue
        path = raw_dir / filename
        if not path.is_file():
            errors.append(f"{name}: missing snapshot {filename}")
            continue
        payload = path.read_bytes()
        actual_hash = hashlib.sha256(payload).hexdigest()
        entry = {"file": filename, "bytes": len(payload), "sha256": actual_hash}
        checked[name] = entry
        if metadata.get("bytes") != len(payload):
            errors.append(f"{name}: byte count mismatch")
        if not isinstance(expected_hash, str) or expected_hash != actual_hash:
            errors.append(f"{name}: SHA-256 mismatch")
        try:
            parsed = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{name}: invalid JSON ({exc})")
            continue
        expected_type = metadata.get("top_level_type")
        if expected_type and type(parsed).__name__ != expected_type:
            errors.append(f"{name}: top-level JSON type mismatch")
    return {
        "status": "failed" if errors else "passed",
        "source_count": len(manifest["sources"]),
        "checked_source_count": len(checked),
        "checked_sources": checked,
        "errors": errors,
    }


def main():
    manifest_path = RAW / "manifest.json"
    errors = []
    checked = {}
    if not manifest_path.is_file():
        result = {"status": "failed", "source_count": 0, "checked_source_count": 0,
                  "checked_sources": {}, "errors": ["sources/raw/manifest.json is missing"]}
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            result = audit_manifest(manifest, RAW)
        except (OSError, json.JSONDecodeError) as exc:
            result = {"status": "failed", "source_count": 0, "checked_source_count": 0,
                      "checked_sources": {}, "errors": [f"cannot read manifest: {exc}"]}
    output = ROOT / "reports" / "source-integrity.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
