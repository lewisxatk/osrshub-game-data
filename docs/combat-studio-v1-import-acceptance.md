# Combat Studio V1 import acceptance sequence

1. Run the database CI and retain the exact generated `dist/*.json` artifact bundle.
2. Review `combat-studio-v1-import-contract.json` and `combat-studio-v1-bundle-manifest.json`; resolve blockers and explain warnings.
3. Record the artifact SHA-256 values alongside the test run so the website test can be reproduced against the same bundle.
4. Import into a non-production/test Combat Studio environment first.
5. Check the consumer handles unknown/additive fields, absent evidence, duplicate identifiers, and empty quest data without inventing defaults.
6. Run reference DPS fixtures and account eligibility cases (quest incomplete/complete/unknown; requirement met/not met/unknown).
7. Test budgeted loadout and upgrade paths, including costs and stable tie-breaks.
8. Run the website build and tests. Only then consider the data bundle accepted for V1.

A green database workflow is necessary but does not replace the consumer-side test.
