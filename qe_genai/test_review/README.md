# Test Review Buddy

**What it does:** wraps a test file (or a test-only diff) in a review prompt
focused on the failure modes that matter for UI automation: flakiness risks
(sleeps, race-prone waits, order dependence), weak or missing assertions,
brittle locators, and shared-state leaks between tests.

## Use case

A cheap second reviewer before a test PR merges. Human reviewers of test code
tend to check "does it test the feature" and skim the mechanics; the
mechanics (an implicit wait here, an over-broad `try/except` there) are
exactly what turns into next month's flaky-test argument. Run this on the
changed test file, paste, and attach anything real to the PR review.

Works for both your Selenium and Playwright code — the prompt tells the model
which framework it's looking at so the advice is idiomatic (e.g. Playwright
auto-waiting vs Selenium explicit waits).

## How to run

```bash
qe review --file tests/checkout/test_discount.py --framework playwright --out qe_prompts/

# or review only what changed in the PR:
git diff origin/main...HEAD -- 'tests/**' > tests.diff
qe review --file tests.diff --diff --framework selenium --out qe_prompts/
```

## What you get

`qe_prompts/test_review.prompt.md`. The prompt asks for findings ranked by
severity, each with the offending line quoted and a concrete rewrite — plus
an explicit instruction to say "no significant issues" rather than inventing
nitpicks when the code is fine.

## Limitations

- A style/robustness review, not a correctness proof — it can't run the test.
- Feed it one file or one diff at a time; whole-suite pastes dilute quality.
