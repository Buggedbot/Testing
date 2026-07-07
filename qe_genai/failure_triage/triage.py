"""Build a failure-triage prompt from a log, an optional JUnit report, and an
optional diff-since-last-green. See README.md in this folder for the use case.
"""

from __future__ import annotations

from typing import Optional

from ..common import TestResult, format_failures

_INSTRUCTIONS = """\
You are triaging automated UI test failures (Selenium/Playwright). For EACH
failing test below, classify the failure as exactly one of:

- PRODUCT BUG: the application behaved incorrectly.
- TEST BUG: the test/automation code is wrong (bad locator, stale assumption,
  missing wait, wrong assertion).
- ENVIRONMENT: infrastructure/data issue (timeout to a dependency, missing
  test data, auth/config problem).
- FLAKY: timing/ordering nondeterminism likely to pass on retry.

For each verdict give:
1. Confidence: high / medium / low.
2. The specific evidence (quote the log line or diff hunk).
3. The single next action you recommend (e.g. "file a bug against checkout
   service", "replace sleep with explicit wait in test X", "rerun once").

If a recent code diff is provided, check whether any failure correlates with
a changed file or behavior before blaming timing.
"""


def build_prompt(
    log_text: str,
    failures: Optional[list[TestResult]] = None,
    diff_text: Optional[str] = None,
) -> str:
    sections = [_INSTRUCTIONS]

    if failures is not None:
        sections.append("## Failing tests (from JUnit report)\n\n" + format_failures(failures))

    sections.append("## Failure log\n\n```\n" + log_text.strip() + "\n```")

    if diff_text:
        sections.append("## Code diff since last green run\n\n```diff\n" + diff_text.strip() + "\n```")
    else:
        sections.append("## Code diff since last green run\n\n(not provided)")

    return "\n\n".join(sections)
