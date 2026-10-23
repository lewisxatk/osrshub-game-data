- [x] Add an account-aware upgrade planner that treats current gear as owned, compares bounded candidates to baseline DPS, and reports changed slots, upgrade cost, DPS gain and gain per GP with schema-backed tests. This remains a limited baseline melee estimate.\n# OSRS Hub Game Data Roadmap

This roadmap covers only the standalone `osrshub-game-data` repository. It does not authorize changes to the OSRS Hub website, Discord integration, Cloudflare Worker, D1 database, or live Grand Exchange feed.

## Principles

- Keep source URL, retrieval metadata, and SHA-256 provenance for downloaded snapshots.
- Preserve unknown values as unknown; do not guess game stats or mechanics.
- Treat source records as evidence, not automatic proof of correctness.
- Separate imported facts from derived calculations and formulas.
- Generate reproducible datasets and reports in GitHub Actions artifacts; avoid committing bulky generated JSON.
- Use focused tests and report what has actually passed. A green structural validation is not proof of complete or game-accurate coverage.

## V1 delivery focus: Combat Studio

V1 is the complete account-aware combat planning experience: imported account stats and quest progress, GP budget, combat style/target, best valid loadout, reasoned exclusions, manual candidate/exclusion controls, and a staged upgrade path. The broader encyclopaedia domains already collected are retained for later V2 work, but new work should prioritize combat V1 exit criteria.

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
- [x] Add a conservative profile-to-item eligibility evaluator that applies manual exclusions and known skill requirements while keeping quest/unlock eligibility unknown.
- [x] Prevent the budgeted multi-slot stat shortlist from equipping the same item ID in multiple slots.\n- [ ] Add quest/unlock relationships once verified quest facts are supplied by a maintained source.
- [x] Require exactly one internally consistent item-to-quest record with a non-placeholder HTTPS source before the planner can treat unlock status as known; unknown, duplicate, contradictory, and fixture-only records are excluded from recommendation candidates.
- [ ] Add recipe/ingredient relationships and item transformation records.
- [ ] Add shops and item sources where data is available and traceable.
- [x] Inventory nested field-path coverage and source-key/provenance integrity across all 11 extended source domains without inventing cross-domain joins.\n- [x] Extend the bounded query interface to all 11 extended source domains with exact source-key lookup and expanded identity-field filtering.
- [ ] Track provenance and conflicts for every imported category.

### Stage 4 — Build the OSRS encyclopaedia
- [x] Add a schema-backed quest import scaffold with requirement/reward fields, skill-level normalization, source hash reporting, and tests; source snapshot and factual coverage still need to be supplied/verified.
- [x] Build schema-validated quest prerequisite/reverse-dependent links, with unresolved/ambiguous requirement reporting, cycle detection, and separate started-versus-completed prerequisite stages; actual coverage depends on a real quest source snapshot.
- [x] Quests: maintained OSRS Wiki category catalogue with page IDs, URLs, pagination, hash reporting, and tests (catalogue only).\n- [ ] Quests: verified requirements, prerequisites, rewards, unlocks, and a maintained fact-extraction adapter.
- [x] Generate a field-level quest evidence worklist that prioritizes unknown facts, missing field-level sources, ambiguous evidence joins, known-empty claims and raw prerequisite candidates without promoting them automatically.\n- [x] Add a conservative quest-readiness report measuring source, prerequisite, skill, and reward coverage; keep empty/incomplete datasets explicitly unsafe for assuming account unlocks.
- [ ] NPCs and monsters: names, IDs, locations, stats, and variants.
- [ ] Drop tables: item IDs, quantities, rates, and source references, preserving unknown rates.
- [ ] Skills and activities: requirements, methods, rewards, and dependencies.
- [ ] Achievement diaries: task requirements and rewards.
- [ ] Spells and prayers: requirements, effects, costs, and relevant relationships.
- [ ] Recipes: ingredients, outputs, skill requirements, and processing steps.

Each category must have a source adapter, a documented schema, validation, coverage reporting, and a small regression test set before it is considered usable.

- [x] Add schema-backed eligibility report and regression tests for missing stats, unknown requirements, and manual exclusions.\n\n### Stage 5 — Verified combat reference layer
- [x] Add a first account-aware, budget-constrained multi-slot Combat Studio planner with an item eligibility audit, quest-unlock evidence input, manual exclusions, candidate-add flags, current-gear zero-cost handling, upgrade path, schema validation, and regression tests. It ranks a summed stat objective only; it is not a full DPS optimizer.
- [x] Add a bounded account-aware melee loadout search using the existing scoped baseline DPS calculation, explicit eligibility audit, budget cap, candidate/node limits, top-loadout output, schema validation, and regression fixtures. This is not boss-verified DPS.
- [x] Define a documented schema and registry for combat mechanics and target-specific behaviour, with separate implementation/verification states and validation guardrails.
- [ ] Separate raw source facts from formulas and derived results.
- [ ] Add sourced test cases for attack rolls, max hits, attack speed, prayers, potions, special attacks, and monster defence.
- [ ] Record source references and verification status for each mechanic.
- [x] Explicitly mark unsupported mechanics instead of silently approximating them; CI rejects contradictory status claims.

**Exit criteria:** each implemented formula has documented assumptions and regression tests against trusted examples.

### Stage 6 — Publish and integrate safely
- [ ] Version generated datasets and publish compact artifacts with release notes.
- [ ] Define stable output contracts and schema versions.
- [ ] Add change reports showing added, removed, and changed records between builds.
- [ ] Document a future read-only consumption path for OSRS Hub.
- [ ] Only integrate with the website after explicit approval and a separate integration plan.

No automatic deployment, Worker changes, D1 migrations/writes, Discord changes, or live-site modifications are included in this roadmap.

- [x] Add an explainable combat-metric comparison to each account-aware upgrade recommendation (rolls, accuracy, max hit, expected damage, attack speed and DPS deltas), with schema and regression tests. This remains scoped baseline arithmetic, not boss-verified DPS.

## Immediate next actions

1. Maintain a source-backed item-to-quest unlock dataset and connect verified coverage to account eligibility decisions; use the new field-level quest worklist to guide manual verification.
2. Expand the optimiser from summed-stat scoring to verified attack-roll, max-hit, accuracy, attack-speed and target-specific DPS scoring, with sourced regression fixtures.
3. Verify each regression fixture against its cited reference and source mapping.
4. Review equipment/weapon normalized provenance discrepancies, then add verified references where trustworthy sources are available.
5. Improve combat-field mapping and coverage based on actual audit gaps; regression fixtures now reject duplicate normalized IDs and invalid source review metadata.
6. Keep V2 encyclopaedia additions secondary until V1 account eligibility, combat scoring, budgeted loadout search, and upgrade-path acceptance tests are met.

## Quest requirement evidence hardening (this update)

- [x] Validate extracted skill candidates against a unique raw quest-evidence record and its exact source URL.
- [x] Require explicit review-only candidate status; never auto-promote raw text matches into planner facts.
- [x] Fail validation for malformed provenance, invalid candidate shapes, mismatched matched quest names, and duplicate evidence/candidate records.
- [x] Keep unmatched catalogue titles and repeated skill matches visible as review queues rather than inventing conclusions.
- [x] Add regression tests for provenance mismatches, duplicate rows, malformed input, and review-only boundaries.

**Acceptance boundary:** this improves the trustworthiness of the candidate pipeline; it does not claim that quest prerequisites or skill requirements are complete or independently verified.

## Current output families

- Items and broad equipment candidates.
- Compact equipment bonuses and requirements where present.
- Weapon attack speeds, types, and stances where present.
- Monster combat fields where present.
- Validation, conflict-priority, coverage, equipment-gap, combat-readiness, source-integrity, pipeline-health, and dataset-diff reports.

Field presence is not the same as correctness, and imported records are not considered verified solely because CI is green.

## Combat arithmetic invariant hardening (next update)

- [x] Add a wider deterministic invariant suite for hit-chance bounds and monotonicity across attack/defence rolls.
- [x] Check linear attack/defence roll scaling, monotonic max-hit behavior, uniform-roll average damage, and DPS scaling with attack interval/tick rate.
- [x] Add regression cases confirming invalid effective-level types, boolean values, and zero attack speed fail closed.
- [ ] Expand reviewed, source-cited reference cases for effective-level derivation, prayers, potions, special attacks, and target-specific rules before implementing those mechanics.

**Acceptance boundary:** these tests catch arithmetic regressions and contract violations; they are not source verification of the full OSRS combat model and do not expand the calculator's supported mechanics.


## Multi-scenario Combat Studio intelligence (this update)

- [x] Compare bounded account-eligible melee candidate sets across 2–10 explicitly sourced scenarios.
- [x] Re-evaluate every retained candidate against every scenario with the same existing scoped baseline evaluator.
- [x] Rank using normalized scenario weights, with worst-case DPS and DPS spread visible as trade-off metrics.
- [x] Report per-scenario rolls, hit chance, max hit, provenance URL, search limits and truncation.
- [x] Add schema validation, illustrative CI fixture, workflow integration and fail-closed tests for duplicate IDs, missing inputs, invalid weights and unsupported source URLs.
- [ ] Expand candidate coverage and add reviewed, source-verified combat mechanics before describing scenario output as boss-accurate DPS.

**Acceptance boundary:** scenario comparison makes the current baseline more useful across multiple caller-supplied contexts. It does not establish source accuracy, complete mechanics, or a globally optimal loadout; each scenario's candidate discovery is bounded.
