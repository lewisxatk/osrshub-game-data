#!/usr/bin/env python3
"""Import extended OSRS source snapshots into site-consumable generated datasets.

Records are preserved, not interpreted. No game facts are inferred and joins are
not fabricated. Each row retains its original source key and snapshot URL.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
DIST = ROOT / "dist"
BASE = "https://raw.githubusercontent.com/RSPSApp/osrsreboxed-db/master/docs/"

# source filename, output filename, identity field, preservation mode
SOURCES = {
    "community_prayers.json": ("prayers.json", "id", "records"),
    "community_npc_drops.json": ("npc-drops.json", "npc_id", "keyed_value"),
    "community_drop_subtables.json": ("drop-subtables.json", "table_key", "keyed_value"),
    "community_shops_by_shop.json": ("shops-by-shop.json", "shop_name", "records"),
    "community_shops_by_npc.json": ("shops-by-npc.json", "npc_id", "records"),
    "community_slayer_tasks.json": ("slayer-tasks.json", "slayer_master_id", "records"),
    "community_npc_interactions.json": ("npc-interactions.json", "source_key", "records"),
    "community_npc_dialogues.json": ("npc-dialogues.json", "source_key", "records"),
    "community_npcs_summary.json": ("npcs-summary.json", "id", "records"),
    "community_objects_summary.json": ("objects-summary.json", "id", "records"),
    "community_models_summary.json": ("models-summary.json", "source_key", "records"),
}

def identity_value(key: str) -> int | str:
    try:
        return int(key)
    except (TypeError, ValueError):
        return str(key)

def preserve_rows(data: Any, identity_field: str, mode: str, source_url: str) -> list[dict[str, Any]]:
    if isinstance(data, list):
        entries = [(str(index), value) for index, value in enumerate(data)]
    elif isinstance(data, dict):
        entries = list(data.items())
    else:
        raise ValueError("source root must be a JSON object or array")

    rows: list[dict[str, Any]] = []
    for key, value in entries:
        if mode == "keyed_value":
            row = {
                identity_field: identity_value(key),
                "source_key": str(key),
                "source_value": value,
                "source_snapshot_url": source_url,
            }
        elif isinstance(value, dict):
            row = dict(value)
            row.setdefault(identity_field, identity_value(key))
            row["source_key"] = str(key)
            row["source_snapshot_url"] = source_url
        else:
            row = {
                identity_field: identity_value(key),
                "source_key": str(key),
                "source_value": value,
                "source_snapshot_url": source_url,
            }
        rows.append(row)
    return rows

def build_datasets(raw_dir: Path = RAW, dist_dir: Path = DIST) -> dict[str, Any]:
    dist_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for source_file, (output_file, identity_field, mode) in SOURCES.items():
        path = raw_dir / source_file
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read required extended source {path}: {exc}") from exc
        if not data:
            raise ValueError(f"Required extended source {path.name} is empty")
        source_url = BASE + {
            "community_prayers.json": "prayers-complete.json",
            "community_npc_drops.json": "drops-json/npc-drops.json",
            "community_drop_subtables.json": "drops-json/subtables.json",
            "community_shops_by_shop.json": "shops-items-by-shop.json",
            "community_shops_by_npc.json": "shops-by-npc.json",
            "community_slayer_tasks.json": "slayer-tasks.json",
            "community_npc_interactions.json": "npcs-interactions.json",
            "community_npc_dialogues.json": "npc-dialogues.json",
            "community_npcs_summary.json": "npcs-summary.json",
            "community_objects_summary.json": "objects-summary.json",
            "community_models_summary.json": "models-summary.json",
        }[source_file]
        rows = preserve_rows(data, identity_field, mode, source_url)
        if not rows:
            raise ValueError(f"Source {source_file} produced no records")
        target = dist_dir / output_file
        target.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        outputs[output_file] = {
            "source_file": source_file,
            "source_url": source_url,
            "record_count": len(rows),
            "output_file": str(target),
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "dataset_count": len(outputs),
        "datasets": outputs,
        "guardrails": [
            "Rows preserve source fields and nested values; no item, NPC, drop or shop joins are inferred.",
            "Source keys are retained even when a numeric ID is also available.",
            "Source snapshot URLs identify provenance, not independent factual verification.",
            "Missing values are not filled with guessed OSRS facts.",
        ],
    }

def main() -> int:
    try:
        report = build_datasets()
    except ValueError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    reports = ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "extended-source-import.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
