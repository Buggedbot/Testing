---
description: 'Convert manual test steps (ADO Test Plans / Gherkin / numbered steps) into an automation skeleton matching this repo''s conventions.'
---

Convert the manual test case I provide (pasted below, or in the attached
file) into automated test skeleton(s) matching this repository's conventions
— inspect existing tests and page objects first and copy their style.

Rules:

- One automated test per scenario; every manual step becomes code in order —
  never merge, reorder, or drop steps.
- Every guessed locator gets a `# TODO(locator):` comment stating the target
  element; a human verifies each before the test runs.
- Steps that can't be automated in-browser (email received, printed output)
  become explicitly skipped stubs with a reason.
- Verification steps become real assertions, not comments.

After the code, list which page objects were reused vs would need creating,
and every `TODO(locator)` in one checklist.
