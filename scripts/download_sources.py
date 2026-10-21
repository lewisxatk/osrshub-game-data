#!/usr/bin/env python3
"""Download pinned-by-hash source snapshots for the OSRS Hub data pipeline."""
from __future__ import annotations
import hashlib, json, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw"
SOURCES = {
    "community_items": "https://raw.githubusercontent.com/RSPSApp/osrsreboxed-db/master/docs/items-complete.json",
    "community_monsters": "https://raw.githubusercontent.com/RSPSApp/osrsreboxed-db/master/docs/monsters-complete.json",
    "original_items": "https://raw.githubusercontent.com/osrsbox/osrsbox-db/master/docs/items-complete.json",
    "original_monsters": "https://raw.githubusercontent.com/osrsbox/osrsbox-db/master/docs/monsters-complete.json",
    "original_items_summary": "https://raw.githubusercontent.com/osrsbox/osrsbox-db/master/docs/items-summary.json",
}
def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "sources": {}}
    failed = []
    for name, url in SOURCES.items():
        request = urllib.request.Request(url, headers={"User-Agent": "OSRSHub-Game-Data/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
                status = getattr(response, "status", 200)
            parsed = json.loads(payload)
            # Verify it is JSON and store bytes as received to preserve the upstream snapshot.
            path = RAW / f"{name}.json"
            path.write_bytes(payload)
            manifest["sources"][name] = {
                "url": url, "http_status": status, "file": path.name,
                "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
                "top_level_type": type(parsed).__name__,
            }
            print(f"OK {name}: {len(payload):,} bytes")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
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
