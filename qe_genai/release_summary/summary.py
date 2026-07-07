"""Build a run/release summary prompt from JUnit reports, in technical or
stakeholder voice. See README.md in this folder for the use case.
"""

from __future__ import annotations

from typing import Optional

from ..common import TestResult, format_failures, summarize_results

_AUDIENCE = {
    "technical": """\
Write a summary for the QE/engineering channel. Include: failures grouped by
suspected common cause (use failure-message similarity), anything that
changed vs earlier runs if multiple runs are shown, and a short ordered
fix-first list. Terse, technical, links-to-nothing (names only).""",
    "stakeholder": """\
Write a summary for product managers and leadership. Plain language, no stack
traces, no test names unless a feature name works better. Structure: one-
sentence overall quality statement; what's working well; risk areas in terms
of user-facing features; and a clear recommendation input for the release
decision (ready / ready-with-known-issues / not-ready) with the reason.
State explicitly that this reflects only what the automated suite covers.""",
}

_INSTRUCTIONS = """\
Summarize the automated test results below.

{audience_instructions}

The pass/fail counts were computed mechanically and are correct -- do not
recount or contradict them. Base everything else only on the failure details
provided; if the evidence doesn't support a claim, leave it out.
"""


def _counts_table(runs: dict[str, list[TestResult]]) -> str:
    lines = ["| run | total | passed | failed | error | skipped |", "|---|---|---|---|---|---|"]
    for run_name, results in runs.items():
        c = summarize_results(results)
        lines.append(
            f"| {run_name} | {c['total']} | {c['passed']} | {c['failed']} | {c['error']} | {c['skipped']} |"
        )
    return "\n".join(lines)


def build_prompt(
    runs: dict[str, list[TestResult]],
    audience: str = "technical",
    context: Optional[str] = None,
) -> str:
    audience_instructions = _AUDIENCE.get(audience, _AUDIENCE["technical"])
    latest = list(runs.values())[-1] if runs else []
    sections = [
        _INSTRUCTIONS.format(audience_instructions=audience_instructions),
        "## Results\n\n" + _counts_table(runs),
        "## Failure details (latest run)\n\n" + format_failures(latest, limit=30),
    ]
    if context:
        sections.insert(1, "## Release context\n\n" + context.strip())
    return "\n\n".join(sections)
