# Edge-Case Test Data Generation

**What it does:** generates a prompt asking for realistic, deliberately
adversarial fixture records for a given entity (CRM contact, lead,
opportunity, order, …) as **JSON matching a schema you provide** — unicode
and RTL names, international phone/address formats, boundary dates, max-length
strings, lookalike duplicates.

## Use case

Hand-written fixtures are all `John Smith, john@test.com, 555-1234` — so the
bugs that hit real customers (a name with an apostrophe breaking a query, a
Japanese address overflowing a field, two near-duplicate leads confusing
dedup logic) never appear in test. Regenerate fixtures per entity once, review
the JSON, commit it to the fixtures folder. The records are *realistic*
enough to keep tests meaningful and *hostile* enough to earn their place.

## How to run

```bash
qe testdata \
  --entity "CRM contact" \
  --count 20 \
  --schema fixtures/contact.schema.json \
  --focus "unicode names, international phones, boundary birthdates" \
  --out qe_prompts/
```

`--schema` (a JSON example record or JSON Schema) pins the output shape so
the result drops into your fixture loader unchanged. `--focus` is optional
steering; without it you get a balanced spread of edge categories.

## What you get

`qe_prompts/test_data.prompt.md`. The prompt demands: valid JSON array only,
every record annotated with a `_edge_case` field naming the trap it carries
(so a failing test tells you *which* edge bit you), and no two records
sharing the same trap.

## Limitations

- Review before committing: generated PII-like data is fictional but should
  still never resemble real customer records you know of.
- Field-level validity (does your app accept `+81-90-...` at all?) is your
  schema's job; the generator assumes the schema is the contract.
