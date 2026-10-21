# OSRS Hub Game Data

A standalone, reproducible data pipeline for structured Old School RuneScape (OSRS) game data. This repository is intentionally separate from the OSRS Hub website and its Cloudflare Worker/D1 systems.

## Goals

- Import source snapshots with URL, retrieval time, and SHA-256 provenance.
- Merge item and monster records by numeric ID while retaining compact source attribution.
- Report meaningful field disagreements separately from noisy timestamps and presentation-image fields.
- Validate generated JSON, IDs, duplicate IDs, source attribution, expected item examples, and basic combat-field coverage.
- Grow incrementally into equipment, weapon mechanics, NPCs, quests, spells, prayers, recipes, and verified combat rules.

Imported community data is evidence, not a guarantee of correctness or completeness. A passing structural validation does not prove game mechanics are accurate. Live Grand Exchange prices are out of scope; the existing OSRS Hub market feed remains separate.

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
python scripts/report_coverage.py
python scripts/audit_equipment.py
python scripts/normalize_combat_data.py
python -m unittest discover -s tests -v
```

On Windows, run these commands in Command Prompt or PowerShell.

## Outputs

- `sources/raw/`: downloaded upstream snapshots and `manifest.json`
- `dist/items.json`: compact merged item records
- `dist/equipment.json`: broad equipment candidates with available source metadata
- `dist/equipment-stats.json`: compact equipment slots, bonuses, requirements, source names, and Wiki links
- `dist/weapons.json`: compact weapon attack speeds, weapon types, stances, source names, and Wiki links
- `dist/monsters.json`: compact merged monster records
- `dist/manifest.json`: generated counts, source precedence, and input SHA-256 hashes
- `reports/source-conflicts.json`: meaningful field disagreements, skipped source records, and counts of ignored volatile-field differences
- `reports/validation.json`: structural checks and coverage counts
- `reports/coverage.json`: field-presence percentages across items, equipment, and monsters
- `reports/equipment-audit.json`: examples and counts of missing equipment bonuses, weapon metadata, attack speeds, and stances
- `reports/combat-data-summary.json`: counts of normalized equipment and weapon records

Generated data files are build outputs. Do not manually edit them; fix the pipeline or source mapping and rebuild. Raw snapshots are retained separately during the workflow and are available in the downloadable Actions artifact when included by the workflow.

## Conflict handling and provenance

The first source listed for each category in `scripts/build_dataset.py` has precedence for conflicting field values. Each merged record lists its source names. Exact raw snapshots are kept in `sources/raw/`; the download manifest records source URLs, retrieval metadata, and SHA-256 hashes. Large raw source records are no longer duplicated inside each merged record, and long conflict values are truncated in the report.

Timestamp and presentation-image differences are counted but omitted from the meaningful conflict list. Review meaningful conflicts before using disputed fields for game-mechanic calculations.

## Data sources

- OSRSBox database: https://github.com/osrsbox/osrsbox-db
- RSPSApp community extension: https://github.com/RSPSApp/osrsreboxed-db

Upstream field shapes can change; inspect reports and validate outputs after every refresh.

## Safety boundaries

- This repository does not deploy the website.
- It does not connect to Cloudflare, Workers, or D1.
- It does not modify Discord integration.
- It does not contain live GE price data.
- It does not claim that source coverage or combat formulas are complete.

## Next expansion

1. Use `coverage.json` and `equipment-audit.json` to prioritize missing equipment bonuses, weapon attack speeds, and stances.
2. Add source adapters and schemas for quests, spells, prayers, recipes, NPCs, and drop tables.
3. Build combat formulas as separately tested code, with citations and test fixtures for verified mechanics.
