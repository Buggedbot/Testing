---
description: 'Generate adversarial edge-case fixture records (unicode, RTL, boundary values, near-duplicates) as JSON matching a schema you provide.'
---

Generate 20 realistic but deliberately adversarial test records for the
entity I name (with the schema/example record I paste or attach).

Requirements:

- Output a single valid JSON array and nothing else.
- Every record matches the provided schema exactly, plus one extra field
  `_edge_case` naming the specific trap it carries (e.g. "apostrophe in
  surname", "RTL name", "max-length email", "leap-day date",
  "near-duplicate of record 3"). No two records share a trap.
- Cover a spread across: unicode & diacritics, RTL scripts,
  quote/apostrophe/whitespace traps, international phone & postal formats,
  boundary dates, min/max-length values, casing collisions, near-duplicates.
- Records must be plausible enough that a reviewer believes each could be a
  real customer. Fictional people and companies only.
