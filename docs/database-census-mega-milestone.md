# Database Census and Release Readiness

This milestone adds five generated reports to make database size, structural quality, source freshness and domain gaps visible in every CI run.

## Run locally

```bash
python scripts/build_database_census.py
python scripts/audit_database_record_quality.py
python scripts/report_source_snapshot_freshness.py
python scripts/build_domain_coverage_matrix.py
python scripts/report_database_release_gates.py
```

## Report meanings

- `database-census.json`: inventory of every generated `dist/*.json` file, byte size, SHA-256, record count, field coverage, configured identity key and duplicate identity indicators.
- `database-record-quality.json`: structural review queue for missing/duplicate identity keys, invalid numeric values, blank names and absent values in source-like fields.
- `source-snapshot-freshness.json`: raw snapshot inventory, local hashes and available manifest URL/retrieval timestamp metadata.
- `domain-coverage-matrix.json`: groups the census and quality metrics by items, combat, quests, monsters, world and other domains.
- `database-release-gates.json`: concise checklist distinguishing blocking structural failures from gaps that need review.

## Counting rules

The sum of rows across generated files is not a global count of unique OSRS entities. An item may appear in the item catalogue, equipment dataset, weapon dataset, requirements dataset, relationship graph and joined combat profile. Counts are therefore reported by file and domain, with explicit warnings against interpreting sums as globally unique entities.

Field presence does not prove correctness. A source URL is a provenance pointer, not independent verification. Missing quest data is a gap, not evidence that no prerequisite exists. This milestone does not infer drops, stats, requirements or combat formulas and does not alter the website, Cloudflare, live GE, or Discord integration.
