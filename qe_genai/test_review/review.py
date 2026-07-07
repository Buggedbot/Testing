"""Build a UI-test review prompt for a test file or test-only diff.
See README.md in this folder for the use case.
"""

from __future__ import annotations

_FRAMEWORK_NOTES = {
    "playwright": (
        "This is Playwright code. Flag: manual sleeps/waitForTimeout (auto-waiting "
        "usually makes them wrong), locators bypassing user-facing attributes when "
        "getByRole/getByLabel/test-ids exist, missing web-first assertions "
        "(expect(locator) over expect(value)), and unawaited async calls."
    ),
    "selenium": (
        "This is Selenium code. Flag: time.sleep instead of WebDriverWait/expected "
        "conditions, implicit+explicit wait mixing, brittle XPath (positional or "
        "styling-coupled), find_element chains without presence checks, and driver/"
        "session state shared across tests."
    ),
    "generic": "Framework unspecified -- apply general UI-automation review criteria.",
}

_INSTRUCTIONS = """\
Review the automated UI test code below. Focus ONLY on:

1. Flakiness risks: sleeps, race-prone waits, dependence on test order or
   leftover state, non-deterministic data (now(), random) in assertions.
2. Assertion quality: missing assertions after actions, assertions that pass
   vacuously, over-broad try/except swallowing failures.
3. Locator robustness: selectors coupled to styling or DOM position when a
   semantic attribute exists.
4. Isolation: shared fixtures/state mutated across tests, cleanup gaps.

For each finding: severity (high/medium/low), quote the offending line(s),
and give the concrete rewritten code. Do NOT comment on formatting, naming
taste, or anything a linter catches. If there are no significant issues, say
"no significant issues" -- do not invent nitpicks to fill space.
"""


def build_prompt(code_text: str, framework: str = "generic", is_diff: bool = False) -> str:
    note = _FRAMEWORK_NOTES.get(framework, _FRAMEWORK_NOTES["generic"])
    body_label = "Test-only diff under review" if is_diff else "Test code under review"
    fence = "diff" if is_diff else "python"
    return "\n\n".join(
        [
            _INSTRUCTIONS,
            "## Framework context\n\n" + note,
            f"## {body_label}\n\n```{fence}\n" + code_text.strip() + "\n```",
        ]
    )
