# self-healing-locator

A self-healing locator agent for Playwright (Python). When a UI test's
selector breaks because the page changed (an id got regenerated, a class was
renamed, a component library was swapped), the agent detects the failure,
re-identifies the same element using DOM-similarity heuristics, and updates
your test's locators so the *next* run just works — no LLM calls, no flaky
retries on the wrong element.

## How it works

1. **Learn**: the first time a named locator is used, the agent snapshots an
   *element fingerprint* — tag, stable attributes (`name`, `type`,
   `aria-label`, `placeholder`, `role`, `data-testid`, ...), visible text,
   class list, bounding box, and parent context — and saves it alongside the
   selector in `locators.yaml`.
2. **Detect**: on every later run, the agent tries the stored selector first.
   If it resolves, nothing else happens — this is the common case and it's as
   fast as calling Playwright directly.
3. **Heal**: if the selector doesn't attach within the timeout, the agent
   scans the page for elements of the same tag, scores each one against the
   stored fingerprint (`self_healing_locator/scoring.py`), and — if the best
   match clears a confidence threshold — builds a new, robust selector for it
   (`self_healing_locator/selector_builder.py`, preferring `data-testid` > a
   non-generated `id` > `name` > other stable attributes > a structural
   fallback).
4. **Persist**: `locators.yaml` is rewritten with the healed selector and
   fingerprint, and a heal event (old selector, new selector, confidence
   score, timestamp) is appended to `locators.report.json`. Tests that
   reference elements by name never need a code change.

No network or LLM calls are made — healing is pure structural/textual
similarity over the DOM, so it's fast, deterministic, and free to run in CI.

## Install

```bash
pip install -e ".[dev]"
playwright install chromium   # skip if Chromium is already provisioned
```

## Usage

### Locator-map mode (recommended)

Reference elements by name; the agent resolves the selector (and heals it
transparently) against the shared store.

```python
from self_healing_locator import Healer

healer = Healer("locators.yaml")

def test_login(page):
    page.goto("https://example.com/login")

    # First run: `selector=` learns and persists the fingerprint.
    username = healer.locate(page, "username_field", selector="#username")
    login_button = healer.locate(page, "login_button", selector="#login-btn")

    # Later runs: no selector needed -- resolved (and healed if broken) from the store.
    username = healer.locate(page, "username_field")
    login_button = healer.locate(page, "login_button")

    username.fill("alice")
    login_button.click()
```

### Inline mode

For scripts that don't want a separate locator map, pass the selector
directly; on healing, the agent rewrites the literal selector string at the
call site in your test file.

```python
button = healer.locate_inline(page, "#login-btn")
```

### CLI

```bash
shl init locators.yaml     # create an empty store
shl list locators.yaml     # show registered locators and heal counts
shl report locators.yaml   # show the healing event history
```

## Demo

`demo/fixtures/login_v1.html` and `login_v2.html` simulate a UI redesign:
every id and class is regenerated between versions, and a decoy "Cancel"
button is added next to the real "Log In" button to prove the healer
disambiguates by more than just tag name.

```bash
python demo/run_demo.py
```

This learns locators against `login_v1.html`, "deploys" `login_v2.html`, and
prints the detected break, the healed selectors, and the resulting
`locators.yaml` / healing report.

## Project layout

```
self_healing_locator/
  fingerprint.py       # JS snippets that capture an element's fingerprint
  scoring.py            # weighted DOM-similarity scoring
  selector_builder.py   # turns a healed fingerprint back into a CSS selector
  store.py               # locators.yaml + healing report persistence
  patcher.py              # rewrites inline selector literals in test source
  healer.py               # Healer: locate() / locate_inline() / heal orchestration
  cli.py                  # `shl` command-line tool
demo/                      # UI-redesign fixtures + narrated demo script
tests/                      # unit tests (scoring/selector/store/patcher) + end-to-end demo test
```

## Tests

```bash
pytest
```

`tests/test_demo_healing.py` runs the full flow against a real (headless)
Chromium browser via Playwright; the rest are pure-Python unit tests.
