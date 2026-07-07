---
description: 'De-flake the selected test: condition-based waits, strengthened assertions, no swallowed failures.'
---

Rewrite the selected test to remove flakiness risks:

- Replace every sleep/fixed timeout with a condition-based wait for the
  specific state the next step needs (Playwright: auto-waiting + web-first
  assertions; Selenium: `WebDriverWait` + expected conditions).
- Strengthen weak assertions: element-exists becomes
  element-has-expected-content wherever content is what actually matters.
- Remove try/except blocks that swallow assertion failures.
- Eliminate nondeterministic inputs (`now()`, `random`) reaching assertions;
  pin or inject them.

Keep the test's behavior and intent identical otherwise. After the code,
list each change and the flakiness risk it removes.
