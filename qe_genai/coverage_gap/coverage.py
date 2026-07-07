"""Build a coverage-gap-analysis prompt from a test inventory and a spec.
See README.md in this folder for the use case.
"""

from __future__ import annotations

_INSTRUCTIONS = """\
You are reviewing test coverage for the feature specified below. The test
inventory lists every automated test that currently exists (by name/title).

Identify what is NOT covered. Group gaps into:

1. Happy-path variants (covered flows with uncovered input/state variations)
2. Negative paths (invalid input, declined/failed operations, error handling)
3. Boundary conditions (limits, empty/zero/max, off-by-one)
4. Roles & permissions (who else can/can't perform these actions)
5. Cross-feature interactions and state transitions
6. Non-functional concerns worth an automated check (performance budget,
   accessibility, localization) -- only where the spec implies them

For each gap output: a one-line proposed test title (in the same naming style
as the inventory), the spec sentence/criterion it traces to, and a priority
(must-have / should-have / nice-to-have). If a spec criterion appears fully
covered, do not pad the list -- say which criteria look well covered in one
closing paragraph.
"""


def build_prompt(inventory_text: str, spec_text: str) -> str:
    return "\n\n".join(
        [
            _INSTRUCTIONS,
            "## Feature spec / acceptance criteria\n\n" + spec_text.strip(),
            "## Current test inventory\n\n```\n" + inventory_text.strip() + "\n```",
        ]
    )
