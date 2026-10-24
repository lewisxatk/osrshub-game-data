# Monster Atlas test matrix

The unit suite covers:

- empty datasets, malformed input roots, zero-valued fields and null values;
- reproducible random fact selection with a seed;
- per-band coverage denominators and all combat-level boundaries;
- DPS arithmetic, seconds-to-ticks conversion and theoretical kills/hour;
- unknown monster IDs refusing to fall back to supplied HP;
- missing monster hitpoints remaining unresolved;
- invalid, non-finite, boolean, zero and negative DPS rejection;
- duplicate IDs and case-insensitive duplicate-name candidates;
- numeric integrity checks for negative and boolean values;
- explicit numeric drop joins, unresolved rows and orphaned IDs.

Fixtures in this suite are synthetic regression data, not claims about actual OSRS
monsters. The pipeline also runs the tools against the generated source snapshots
and validates their output schemas. A green run proves these checks passed, not
that every source value or every combat mechanic is correct.
