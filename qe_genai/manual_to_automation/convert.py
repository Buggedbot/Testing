"""Build a manual-test-to-automation-skeleton prompt.
See README.md in this folder for the use case.
"""

from __future__ import annotations

from typing import Optional

_FRAMEWORK_TARGET = {
    "playwright": "Playwright (Python, sync API, pytest)",
    "playwright-ts": "Playwright (TypeScript, @playwright/test)",
    "selenium": "Selenium WebDriver (Python, pytest, explicit WebDriverWait)",
}

_INSTRUCTIONS = """\
Convert the manual test case(s) below into automated test skeleton(s) for
{target}.

Rules:
- One automated test per scenario; test name derived from the scenario title.
- Every manual step becomes code IN ORDER. Do not merge, reorder, or drop
  steps.
- Every locator you have to guess must be marked with a `# TODO(locator):`
  comment stating what element it should point at -- a human will verify each
  one before the test runs.
- Steps that cannot be automated in-browser (e.g. "verify the email was
  received", "check the printed document") become explicit skipped stubs with
  a comment, never silently dropped.
- Verification steps become real assertions, not comments.
{style_rule}
"""

_STYLE_RULE_WITH_EXAMPLE = (
    "- Match the conventions of the example test provided below exactly: same "
    "page-object/fixture pattern, same import style, same naming."
)
_STYLE_RULE_WITHOUT_EXAMPLE = (
    "- No style example was provided; use clean idiomatic conventions and put "
    "selectors in one obvious place so they're easy to replace."
)


def build_prompt(
    steps_text: str,
    framework: str = "playwright",
    example_test: Optional[str] = None,
) -> str:
    target = _FRAMEWORK_TARGET.get(framework, framework)
    style_rule = _STYLE_RULE_WITH_EXAMPLE if example_test else _STYLE_RULE_WITHOUT_EXAMPLE
    sections = [
        _INSTRUCTIONS.format(target=target, style_rule=style_rule),
        "## Manual test case(s)\n\n" + steps_text.strip(),
    ]
    if example_test:
        sections.append(
            "## Style anchor -- an existing test from this suite\n\n```\n" + example_test.strip() + "\n```"
        )
    return "\n\n".join(sections)
