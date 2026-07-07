# Direct-Chat Prompt Library

Some QE uses of Copilot need no tooling at all — the context is already open
in the editor. This folder is a copy-paste prompt library for those cases.
Highlight the relevant code in VS Code, open Copilot Chat, and paste.

> For the reusable/automated versions of these (slash-commands and custom
> chat modes inside VS Code), see `../vscode_agents/` — the prompts below are
> the zero-setup fallback.

---

## Assertion & wait hardening

> Rewrite the selected test to remove flakiness risks: replace any sleep or
> fixed timeout with a condition-based wait for the specific state the next
> step needs; strengthen weak assertions (element-exists → element-has-
> expected-content); and remove try/except blocks that swallow assertion
> failures. Keep behavior identical otherwise. List each change and the
> flakiness risk it removes.

## Locator modernization

> Rewrite the selectors in the selected test in this priority order: test-id
> attribute > role/label (user-facing) > stable id > semantic attribute.
> Never use positional XPath or class names that look generated. For each
> selector you can't confidently rewrite, keep it and add a
> `# TODO(locator)` comment saying what attribute the app team should add.

## Page-object extraction

> Extract a page object from the selected test(s): one class per page/screen,
> locators as class attributes, user actions as methods named for intent
> (login, add_to_cart), assertions stay in the test. Match the structure of
> the existing page objects in this workspace. Show the page object and the
> rewritten test.

## Test-PR review checklist

> Review this diff as a senior QE. Only report: flakiness risks (sleeps,
> race-prone waits, order dependence), missing/weak assertions, brittle
> locators, and test-isolation problems (shared state, missing cleanup).
> Severity per finding, offending line quoted, concrete fix. If there are no
> significant issues, say so — do not pad.

## Explain a legacy test

> Explain what the selected test verifies, step by step, in plain language a
> manual QE could execute by hand. Then flag anything suspicious: steps with
> no assertion, assertions that can pass vacuously, or setup the test
> depends on but doesn't create.

## Selenium → Playwright migration (per file)

> Convert the selected Selenium test to Playwright (Python, sync API,
> pytest). Map WebDriverWait/expected conditions to Playwright auto-waiting
> and web-first assertions; map find_element chains to locators (prefer
> get_by_role/get_by_label). Keep test names and assertion intent identical.
> Mark anything without a clean equivalent with `# TODO(migration):`.

---

**Habit worth building:** when a prompt earns its keep more than twice, stop
pasting it — promote it to a `.prompt.md` slash-command or a chat mode in
`../vscode_agents/` so the whole team gets it.
