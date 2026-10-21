# OSRS Hub Game Data

A standalone, reproducible data pipeline for structured Old School RuneScape (OSRS) game data. This repository is intentionally separate from the OSRS Hub website and its Cloudflare Worker/D1 systems.

## Goals

- Import source snapshots with URL, retrieval time, and SHA-256 provenance.
- Normalize item and monster records into predictable JSON files.
- Preserve source records and report conflicting fields instead of silently discarding disagreements.
- Validate IDs, required fields, key equipment examples, and generated JSON.
- Grow incrementally into equipment, weapon mechanics, NPCs, quests, spells, prayers, recipes, and verified combat rules.

**Important:** imported community data is evidence, not a guarantee of correctness or completeness. Keep source provenance and validate game mechanics before using them for combat decisions. Live Grand Exchange prices are out of scope; OSRS Hub's existing market feed remains separate.

## Requirements

- Python 3.10 or newer
- Internet access for source downloads

No third-party Python packages are required.

## Quick start

From the repository root:

```bash
python scripts/download_sources.py
python scripts/build_dataset.py
python scripts/validate_dataset.py
```

On Windows, these commands work in Command Prompt or PowerShell.

Outputs:
- `sources/raw/`: downloaded upstream snapshots and `manifest.json`
- `dist/items.json`: merged item records keyed by item ID
- `dist/equipment.json`: equipment candidates with equipment metadata
- `dist/monsters.json`: merged monster records
- `dist/manifest.json`: generated counts and input hashes
- `reports/source-conflicts.json`: source field disagreements
- `reports/validation.json`: validation results

Generated data files are build outputs. Do not manually edit them; fix the pipeline or source mapping and rebuild.

## Data sources

The initial pipeline uses JSON snapshots published by:
- OSRSBox database: https://github.com/osrsbox/osrsbox-db
- RSPSApp community extension: https://github.com/RSPSApp/osrsreboxed-db

Source URLs and SHA-256 hashes are recorded by the downloader. Upstream field shapes can change; inspect reports and validate outputs after every refresh.

## Repository layout

```
.github/workflows/validate.yml
schemas/
scripts/
sources/raw/
dist/
reports/
tests/
```

## Safety boundaries

- This repository does not deploy the website.
- It does not connect to Cloudflare, Workers, or D1.
- It does not modify Discord integration.
- It does not contain live GE price data.
- A passing structural validation does not prove a game mechanic is accurate.

## Next expansion

1. Review source coverage and conflicts after the first download.
2. Add explicit schemas for item, equipment, weapon, and monster fields.
3. Add source adapters for quests, spells, prayers, recipes, NPCs, and drop tables.
4. Build combat formulas as separately tested code, with citations and test fixtures for verified mechanics.
