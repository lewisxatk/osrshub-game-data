# Cross-domain graph health

The graph-health report measures explicit ID joins among the item, equipment, weapon, requirements, combat-profile, item-relationship, monster and quest datasets. It reports source coverage, orphan target records, duplicate/missing IDs, and a small prioritised gap queue.

Run:

```bash
python scripts/build_domain_graph_health.py --output reports/domain-graph-health.json
python -m unittest discover -s tests -p 'test_domain_graph_health.py' -v
```

This is structural linkage, not proof that two records are factually correct or that an item is quest-unlocked. It deliberately does not guess links from names, and it reports unavailable datasets as not assessed rather than zero coverage. The configured edges are a bounded contract and must not be interpreted as complete OSRS knowledge-graph coverage.
