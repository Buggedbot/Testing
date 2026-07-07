<!-- Copy to .github/copilot-instructions.md in your automation repo.
     EDIT the sections marked [EDIT] to match your suite before committing. -->

# Repository conventions for AI assistance

This repository contains automated UI tests (Playwright and Selenium,
Python). When generating or modifying code here, follow these rules.

## Waits & timing
- Never use `time.sleep()` or fixed timeouts to "fix" timing. Playwright:
  rely on auto-waiting and web-first assertions. Selenium: use
  `WebDriverWait` with an explicit expected condition for the state the next
  step needs.

## Locators
- Priority order: test-id attribute > role/label (user-facing) > stable id >
  semantic attribute. Never positional XPath, never generated-looking class
  names.
- If no good locator exists, use the best available and add a
  `# TODO(locator):` comment describing the attribute the app team should add.

## Structure
- [EDIT] Page objects live in `pages/`; one class per screen; locators as
  class attributes; actions as intent-named methods; assertions stay in tests.
- [EDIT] Fixtures live in `fixtures/`; tests never create shared state
  outside their own fixtures and always clean up what they create.

## Assertions
- Every user action is followed by an assertion on its observable outcome.
- Never wrap assertions in try/except. Never assert only that an element
  exists when its content is what matters.

## Safety
- Tests must never click controls whose text/attributes match: delete,
  remove, archive, deactivate, purge — unless the test is explicitly about
  that action and cleans up after itself. [EDIT: extend with your domain's
  destructive verbs.]

## Azure DevOps
- [EDIT] Work item references in commit messages use `AB#<id>`.
- Test names must be stable — ADO history/flakiness tracking keys on them;
  prefer adding a new test over renaming an old one.
