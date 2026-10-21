# OSRS Hub Game Data Roadmap

This roadmap covers only the standalone `osrshub-game-data` repository. It does not authorize changes to the OSRS Hub website, Discord integration, Cloudflare Worker, D1 database, or live Grand Exchange feed.

## Principles

- Keep source URL, retrieval metadata, and SHA-256 provenance for downloaded snapshots.
- Preserve unknown values as unknown; do not guess game stats or mechanics.
- Treat source records as evidence, not automatic proof of correctness.
- Separate imported facts from derived calculations and formulas.
- Generate reproducible datasets and reports in GitHub Actions artifacts; avoid committing bulky generated JSON.
- Use focused tests and report what has actually passed. A green structural validation is not proof of complete or game-accurate coverage.

## Roadmap

### Stage 1 — Stabilise the pipeline
- [x] Download source snapshots and record hashes in a manifest.
- [x] Merge item and monster records by numeric ID with source attribution.
- [x] Reduce duplicated raw source data in merged outputs.
- [x] Report meaningful field conflicts separately from volatile image/timestamp differences.
- [x] Validate JSON structure, IDs, duplicate IDs, attribution, and basic coverage.
- [x] Produce item/equipment/monster field-coverage and equipment-gap reports.
- [x] Generate dedicated equipment-stat and weapon datasets from available source fields.
- [x] Add a normalized monster-combat dataset and per-field coverage report.
- [x] Confirm the latest CI run succeeds after all recent commits.
- [ ] Review reports for source-field mapping mistakes and unexpected drops in record counts.
- [x] Add schema validation to CI for the normalized outputs.

### Stage 2 — Improve core combat-data quality
- [x] Add an item identity audit for duplicate IDs, missing names, exact-name collisions, and punctuation/case-normalized name collisions without auto-merging variants.\n- [x] Audit item IDs and names; summarize normalized equipment-slot and weapon-type coverage, including missing categories and duplicate IDs.
- [ ] Audit bonus-field conventions and compare high-value gear against a trusted, versioned source.
- [ ] Compare known high-value gear examples against a trusted, versioned source.
- [ ] Improve weapon stance and attack-speed coverage without inferring missing values.
- [ ] Improve monster combat-stat coverage and identify source disagreements.
- [x] Add an initial sourced regression fixture set for representative equipment and weapon facts.
- [ ] Expand regression fixtures to representative melee, ranged, magic, and boss cases after source review.
- [ ] Document source precedence and field aliases so upstream schema changes are visible.
- [x] Add an initial field-level source-provenance and disagreement report for item and monster source fields.
- [x] Extend monster combat provenance to report selected source names and the exact raw alias used for each normalized field, with capped record examples.
- [x] Add equipment/weapon normalized field provenance with source counts, raw field paths, and capped examples.
- [ ] Add verified source references for each combat-critical normalized field and review mapping discrepancies surfaced by the provenance report.

**Exit criteria:** reproducible compact outputs, clear coverage percentages, tests for mappings, and known examples reviewed against sources. This is not yet a promise of full combat-calculator accuracy.

### Stage 3 — Add OSRS item relationships
- [ ] Identify item IDs and aliases consistently across sources and reconcile alias collisions.
- [x] Add explicit item-ID links to normalized equipment-stat and weapon records, with orphan counts and schema validation.
- [x] Normalize source-backed item skill requirements into an item-ID keyed dataset with schema validation and malformed-value warnings.
- [ ] Add quest/unlock relationships once quest facts are supplied by a maintained source.
- [ ] Add recipe/ingredient relationships and item transformation records.
- [ ] Add shops and item sources where data is available and traceable.
- [ ] Track provenance and conflicts for every imported category.

### Stage 4 — Build the OSRS encyclopaedia
- [x] Add a schema-backed quest import scaffold with requirement/reward fields, skill-level normalization, source hash reporting, and tests; source snapshot and factual coverage still need to be supplied/verified.
- [x] Build schema-validated quest prerequisite/reverse-dependent links, with unresolved/ambiguous requirement reporting and cycle detection; actual coverage depends on a real quest source snapshot.
- [ ] Quests: verified requirements, prerequisites, rewards, unlocks, and a maintained upstream source adapter.\n- [x] Add a conservative quest-readiness report measuring source, prerequisite, skill, and reward coverage; keep empty/incomplete datasets explicitly unsafe for assuming account unlocks.
- [ ] NPCs and monsters: names, IDs, locations, stats, and variants.
- [ ] Drop tables: item IDs, quantities, rates, and source references, preserving unknown rates.
- [ ] Skills and activities: requirements, methods, rewards, and dependencies.
- [ ] Achievement diaries: task requirements and rewards.
- [ ] Spells and prayers: requirements, effects, costs, and relevant relationships.
- [ ] Recipes: ingredients, outputs, skill requirements, and processing steps.

Each category must have a source adapter, a documented schema, validation, coverage reporting, and a small regression test set before it is considered usable.

### Stage 5 — Verified combat reference layer
- [ ] Define a documented schema for combat mechanics and target-specific behaviour.
- [ ] Separate raw source facts from formulas and derived results.
- [ ] Add sourced test cases for attack rolls, max hits, attack speed, prayers, potions, special attacks, and monster defence.
- [ ] Record source references and verification status for each mechanic.
- [ ] Explicitly mark unsupported mechanics instead of silently approximating them.

**Exit criteria:** each implemented formula has documented assumptions and regression tests against trusted examples.

### Stage 6 — Publish and integrate safely
- [ ] Version generated datasets and publish compact artifacts with release notes.
- [ ] Define stable output contracts and schema versions.
- [ ] Add change reports showing added, removed, and changed records between builds.
- [ ] Document a future read-only consumption path for OSRS Hub.
- [ ] Only integrate with the website after explicit approval and a separate integration plan.

No automatic deployment, Worker changes, D1 migrations/writes, Discord changes, or live-site modifications are included in this roadmap.

## Immediate next actions

1. Review generated field-provenance and combat-reference reports.
2. Verify each regression fixture against its cited reference and source mapping.
3. Review equipment/weapon normalized provenance discrepancies, then add verified references where trustworthy sources are available.
4. Improve combat-field mapping and coverage based on actual audit gaps; regression fixtures now reject duplicate normalized IDs and invalid source review metadata.
5. Use measured gaps to choose the next source adapter or data category; item identity diagnostics, item relationships, normalized skill requirements, combat-category coverage, and schema-backed quest relationships are now in the pipeline.

## Current output families

- Items and broad equipment candidates.
- Compact equipment bonuses and requirements where present.
- Weapon attack speeds, types, and stances where present.
- Monster combat fields where present.
- Validation, conflict-priority, coverage, equipment-gap, combat-readiness, source-integrity, pipeline-health, and dataset-diff reports.

Field presence is not the same as correctness, and imported records are not considered verified solely because CI is green.
