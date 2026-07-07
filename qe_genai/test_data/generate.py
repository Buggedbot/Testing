"""Build an edge-case fixture-generation prompt.
See README.md in this folder for the use case.
"""

from __future__ import annotations

from typing import Optional

_INSTRUCTIONS = """\
Generate {count} realistic but deliberately adversarial test records for the
entity: {entity}.

Requirements:
- Output a single valid JSON array and NOTHING else -- no prose, no fences.
- Every record must match the schema/example provided below exactly (same
  fields, same types).
- Every record carries one extra field `_edge_case`: a short string naming
  the specific trap it contains (e.g. "apostrophe in surname", "RTL name",
  "max-length email", "leap-day birthdate", "near-duplicate of record 3").
- No two records may share the same `_edge_case` value.
- Records must be plausible -- a reviewer should believe each could be a real
  customer. Fictional people/companies only.
- Cover a spread across: unicode & diacritics, RTL scripts, whitespace/quote/
  apostrophe traps, international phone & postal formats, boundary dates,
  min/max-length values, casing collisions, and near-duplicates{focus_clause}.
"""


def build_prompt(
    entity: str,
    count: int = 20,
    schema_text: Optional[str] = None,
    focus: Optional[str] = None,
) -> str:
    focus_clause = f" -- with extra emphasis on: {focus}" if focus else ""
    sections = [_INSTRUCTIONS.format(count=count, entity=entity, focus_clause=focus_clause)]
    if schema_text:
        sections.append("## Schema / example record\n\n```json\n" + schema_text.strip() + "\n```")
    else:
        sections.append(
            "## Schema / example record\n\n(none provided -- infer a sensible "
            "field set for this entity and keep it consistent across all records)"
        )
    return "\n\n".join(sections)
