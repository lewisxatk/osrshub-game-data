# Combat Studio V1 bundle manifest

Run `python scripts/build_combat_studio_v1_bundle_manifest.py` to produce `reports/combat-studio-v1-bundle-manifest.json`.

The manifest inventories the nine declared V1 JSON artifacts, records file SHA-256 hashes, record counts, identity fields, duplicate/missing identity counts, and blockers or review warnings. CI uploads the generated report and `dist/*.json` artifacts together for a reviewable, hash-pinned snapshot.

Statuses:
- `blocked`: at least one required file is missing or malformed.
- `review_required`: files parse but one or more datasets are empty or identity integrity is questionable.
- `bundle_integrity_passed`: all listed artifacts are structurally non-empty and have unique present IDs.

A passed manifest means integrity checks passed, not that all OSRS facts are verified, combat mechanics are complete, or the website import works. Consumer integration tests remain mandatory.
