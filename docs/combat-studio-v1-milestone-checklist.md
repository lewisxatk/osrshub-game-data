# Combat Studio V1 milestone checklist

This checklist distinguishes database readiness from the complete website feature.

## Data contract
- [ ] Required JSON artifacts are generated and schema-validated.
- [ ] Identity fields are present and unique where expected.
- [ ] Equipment stats, weapon metadata and monster combat fields have measured coverage.
- [ ] Unknown values remain explicit; no invented defaults.
- [ ] Item skill requirements and quest evidence are linked and reviewable.
- [ ] Provenance is available for high-impact combat fields.
- [ ] Combat mechanics are tested against known reference fixtures.
- [ ] Import contract report is clean enough for consumer integration testing.

## Consumer integration
- [ ] Combat Studio imports the generated artifact set.
- [ ] Field names/types match the website consumer.
- [ ] Account stats, quest completions and budget are applied correctly.
- [ ] Ineligible gear is excluded only when evidence supports exclusion; unknown eligibility is surfaced.
- [ ] DPS output is checked against known scenarios.
- [ ] Upgrade paths report costs, deltas and assumptions.
- [ ] Mobile UX and website build remain healthy.

## Release rule
A green database CI is necessary but not sufficient for V1. The frontend must be exercised against the exact generated artifact bundle, and calculations must pass reference tests. Do not advertise V1 as complete until both database and consumer checks pass.
