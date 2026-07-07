"""Build an Azure DevOps Bug work item drafting prompt from a test failure.
See README.md in this folder for the use case.
"""

from __future__ import annotations

from typing import Optional

from ..common import TestResult

_INSTRUCTIONS = """\
Draft an Azure DevOps Bug work item from the automated test failure below.
Derive the repro steps from what the test source code actually does (each
user-visible action becomes one numbered step) -- do not invent steps the
test doesn't perform. Describe symptoms confidently; only state a root cause
if the evidence clearly supports it, otherwise write "root cause not yet
determined".

Output EXACTLY these sections, in Markdown, ready to paste into the ADO New
Bug form:

## Title
(one line: <area>: <symptom> -- specific enough to be unique)

## Repro Steps
(numbered, human-executable without reading the test code)

## Expected Result

## Actual Result
(include the assertion/error message verbatim)

## System Info
(environment, browser, build -- from the details provided)

## Suggested Severity
(1-Critical / 2-High / 3-Medium / 4-Low, with a one-line justification)
"""


def build_prompt(
    result: TestResult,
    test_source: Optional[str] = None,
    environment: Optional[str] = None,
    area_path: Optional[str] = None,
) -> str:
    sections = [_INSTRUCTIONS]

    details = [
        f"- Failing test: `{result.full_name}`",
        f"- Status: {result.status} ({result.time:.1f}s)",
    ]
    if environment:
        details.append(f"- Environment: {environment}")
    if area_path:
        details.append(f"- Area Path: {area_path}")
    sections.append("## Failure details\n\n" + "\n".join(details))

    sections.append("## Failure message\n\n```\n" + (result.message or "(no message captured)") + "\n```")

    if test_source:
        sections.append("## Test source code\n\n```python\n" + test_source.strip() + "\n```")
    else:
        sections.append(
            "## Test source code\n\n(not provided -- derive repro steps from the "
            "test name and failure message, and flag them as unverified)"
        )

    return "\n\n".join(sections)
