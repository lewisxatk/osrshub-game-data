#!/usr/bin/env python3
"""Download source snapshots for the OSRS Hub game-data pipeline with hashes."""
from __future__ import annotations
import hashlib, json, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
BASE = "https://raw.githubusercontent.com/RSPSApp/osrsreboxed-db/master/docs/"
SOURCES = {
    # Core entity databases
    "community_items": BASE + "items-complete.json",
    "community_monsters": BASE + "monsters-complete.json",
    "original_items": "https://raw.githubusercontent.com/osrsbox/osrsbox-db/master/docs/items-complete.json",
    "original_monsters": "https://raw.githubusercontent.com/osrsbox/osrsbox-db/master/docs/monsters-complete.json",
    "original_items_summary": "https://raw.githubusercontent.com/osrsbox/osrsbox-db/master/docs/items-summary.json",
    # Additional source domains retained as independent snapshots; never merged into
    # item/monster records unless a separate, explicit normalizer defines that join.
    "community_prayers": BASE + "prayers-complete.json",
    "community_npc_drops": BASE + "drops-json/npc-drops.json",
    "community_drop_subtables": BASE + "drops-json/subtables.json",
    "community_shops_by_shop": BASE + "shops-items-by-shop.json",
    "community_shops_by_npc": BASE + "shops-by-npc.json",
    "community_slayer_tasks": BASE + "slayer-tasks.json",
    "community_npc_interactions": BASE + "npcs-interactions.json",
    "community_npc_dialogues": BASE + "npc-dialogues.json",
    "community_npcs_summary": BASE + "npcs-summary.json",
    "community_objects_summary": BASE + "objects-summary.json",
    "community_models_summary": BASE + "models-summary.json",
}

def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "sources": {}}
    failed = []
    for name, url in SOURCES.items():
        request = urllib.request.Request(url, headers={"User-Agent": "OSRSHub-Game-Data/0.2", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
                status = getattr(response, "status", 200)
            parsed = json.loads(payload)
            if not isinstance(parsed, (dict, list)):
                raise ValueError(f"unexpected top-level JSON type: {type(parsed).__name__}")
            if not parsed:
                raise ValueError("source returned an empty JSON container")
            path = RAW / f"{name}.json"
            path.write_bytes(payload)
            manifest["sources"][name] = {
                "url": url, "http_status": status, "file": path.name,
                "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                "top_level_type": type(parsed).__name__,
                "top_level_record_count": len(parsed),
            }
            print(f"OK {name}: {len(payload):,} bytes; {len(parsed):,} top-level records")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
            failed.append((name, str(exc)))
            print(f"FAIL {name}: {exc}", file=sys.stderr)
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if failed:
        print(f"{len(failed)} source(s) failed; see sources/raw/manifest.json", file=sys.stderr)
        return 1
    print(f"Downloaded and JSON-checked {len(SOURCES)} sources.")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
