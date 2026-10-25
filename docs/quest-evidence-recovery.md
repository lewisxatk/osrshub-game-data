# Quest Evidence Recovery and Reconciliation

## Why this exists

The OSRS Wiki quest-requirement page can expose rows in more than one table layout. An ordinal column can precede the quest title and requirement text. Treating the ordinal as the title loses valid matches and makes evidence coverage misleading.

## What changed

- The downloader recognizes both two-column quest/requirements rows and three-column ordinal/quest/requirements rows.
- Title matching normalizes Unicode apostrophes, non-breaking spaces, underscores, and whitespace. It does not fuzzy-match.
- Duplicate normalized titles are collapsed deterministically, preferring catalogue matches and richer explicit evidence; duplicate counts and extraction shapes remain visible.
- Numeric ordinal rows are never emitted as quest names.
- A reconciliation audit checks catalogue joins, source host, linked source hosts, row-shape labels, key consistency, duplicate titles, and missing catalogue evidence.
- CI validates the generated audit report against a JSON Schema.

## Safety boundary

This is an evidence-recovery improvement, not automatic quest-fact normalization. Raw text remains review-only. A dash or blank does not prove the quest has no requirements. The pipeline does not infer starting versus completion requirements, boostability, rewards, or membership status. A review_required status is expected while evidence needs manual interpretation; failed means structural or provenance checks found a blocking inconsistency.

## Reports

- reports/quest-requirement-evidence-coverage.json: extraction count, catalogue match coverage, duplicate-row diagnostics, and unmatched titles.
- reports/quest-evidence-reconciliation.json: catalogue/evidence joins, source-link checks, missing titles, and structural errors.

A passing structural audit does not prove the source is current or that the game facts have been independently verified.
