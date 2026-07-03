# self-healing-locator

A self-healing locator agent for Playwright (Python), built for running UI
test suites against client CRM applications (Salesforce Lightning, Dynamics
365, HubSpot, and similar). When a locator breaks because the UI changed (an
id got regenerated, a class was renamed, a component library was swapped),
the agent detects the failure, re-identifies the same element using
DOM-similarity heuristics, and updates your test's locators so the *next*
run just works — no LLM calls required, no flaky retries on the wrong
element. An opt-in GenAI tier (see below) can pick up cases the heuristics
can't confidently resolve on their own.

## How it works

1. **Learn**: the first time a named locator is used, the agent snapshots an
   *element fingerprint* — tag, stable attributes (`name`, `type`,
   `aria-label`, `placeholder`, `role`, `data-testid`, ...), visible text,
   class list, bounding box, and parent context — and saves it alongside the
   selector in `locators.yaml`.
2. **Detect**: on every later run, the agent tries the stored selector first.
   If it resolves, nothing else happens — this is the common case and it's as
   fast as calling Playwright directly.
3. **Scan**: if the selector doesn't attach within the timeout, the agent
   scans every frame on the page — the main document, any *open* shadow
   roots within it (e.g. Salesforce Lightning Web Components), and every
   same- or cross-origin iframe (e.g. a Dynamics embedded record form) — for
   elements of the same tag.
4. **Score**: each candidate is scored against the stored fingerprint
   (`self_healing_locator/scoring.py`) using weighted structural/textual
   similarity — no network or LLM calls, so it's fast, deterministic, and
   free to run in CI.
5. **Guard**: if the best match's text/attributes/classes match a
   configurable risk deny-list ("delete", "remove", "archive", "discard",
   ...), it is **not** auto-applied. A wrong guess must never land on a
   destructive control in a client's live CRM, so the proposed heal is
   queued to `locators.pending.json` and `HealingRequiresReviewError` is
   raised instead — a human reviews it with `shl review` / `shl approve`.
6. **Heal & persist**: otherwise, a new robust selector is built
   (`self_healing_locator/selector_builder.py`, preferring `data-testid` > a
   non-generated `id` > `name` > other stable attributes > a structural
   fallback), `locators.yaml` is rewritten with the healed selector,
   fingerprint, and — if the element moved into/out of an iframe — the
   selector for that iframe. A heal event is appended to
   `locators.report.json`. Tests that reference elements by name never need
   a code change.

> **Note on this repo's fixtures:** the bundled demo pages are synthetic
> test fixtures, not real client data, so their scraped text/attributes are
> written to `locators.yaml`/`*.report.json` as-is. If you point this at a
> real client CRM, treat those generated files as containing real customer
> data (they will include on-screen text such as contact names) — keep them
> out of version control / restrict access accordingly, the same as any
> other test artifact that touches production-like data.

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

Elements inside an open shadow root or an iframe are located exactly the
same way — the agent finds and re-addresses them automatically; no special
API is needed.

### Inline mode

For scripts that don't want a separate locator map, pass the selector
directly; on healing, the agent rewrites the literal selector string at the
call site in your test file.

```python
button = healer.locate_inline(page, "#login-btn")
```

### Multi-client isolation

Running against several clients' CRM instances? Pass `client_id=` instead of
`store_path=` so each client gets its own locator store, heal report, and
pending-review queue, under `<base_dir>/<client_id>/` (default `locators/`):

```python
healer = Healer(client_id="acme-corp")   # -> locators/acme-corp/locators.yaml
```

One client's healed selectors, or its shadow-DOM/iframe fingerprints, can
never leak into or be applied against another client's org.

### Risk gate: destructive heals require human review

If the only confident candidate looks destructive, the agent refuses to
auto-apply it:

```python
from self_healing_locator.exceptions import HealingRequiresReviewError

try:
    healer.locate(page, "cancel_button")
except HealingRequiresReviewError:
    ...  # queued to locators.pending.json; surface this in CI / notify a human
```

Review and resolve it from the CLI:

```bash
shl review locators.yaml            # show what's pending and why
shl approve cancel_button locators.yaml   # apply the proposed heal
shl reject  cancel_button locators.yaml   # discard it
```

The deny-list is configurable:

```python
healer = Healer(
    "locators.yaml",
    risk_keywords=["delete", "remove", "archive", "void", "unenroll"],
    require_review_for_risky=True,  # default
)
```

### CLI

```bash
shl init    locators.yaml               # create an empty store
shl list    locators.yaml               # show registered locators, frames, heal counts
shl report  locators.yaml               # show the healing event history
shl review  locators.yaml               # show heals withheld for looking destructive
shl approve <name> locators.yaml        # apply a pending heal
shl reject  <name> locators.yaml        # discard a pending heal
```

### Optional GenAI fallback tier

Heuristic scoring is the default and only requires local DOM comparison — no
network calls. When it *can't* clear `confidence_threshold` on its own (a
redesign changed enough that nothing scores confidently), you can opt into an
LLM tier that gets the same scored candidates and picks from them:

```python
healer = Healer("locators.yaml", llm_fallback=True)   # llm_backend="copilot_cli" by default
```

`llm_backend` selects what actually answers the prompt:

| `llm_backend=` | What it calls | Needs |
| --- | --- | --- |
| `"copilot_cli"` (default) | Shells out to `gh copilot suggest` | `gh` CLI + the `gh-copilot` extension, logged in |
| `"anthropic"` | Claude via the `anthropic` SDK | `pip install -e ".[llm]"` + API credentials |
| any `(prompt: str) -> str \| None` callable | your own backend | whatever it needs |

**Be aware of what `"copilot_cli"` actually is.** `gh copilot suggest` is
built to suggest *shell/git/gh commands*, not to answer arbitrary
structured-JSON questions — there's no official "ask Copilot anything, get
JSON back" API. This backend asks it for a JSON object anyway and scrapes the
first `{...}`-looking blob out of whatever it prints
(`self_healing_locator/llm_healer.py::CopilotCliBackend`). It works often
enough to be worth having as a fallback, but expect it to come back empty
more often than a real completion API would — and that's fine: `select_candidate`
treats "no usable response" as just another way for the LLM tier to defer,
same as if `llm_fallback` were off, and healing falls through to
`HealingFailedError`. If your environment does have real LLM API access,
`llm_backend="anthropic"` is a much more reliable choice.

**The risk gate applies regardless of source.** An LLM-selected candidate
that matches the deny-list is queued to `locators.pending.json` exactly like
a heuristic one — the GenAI tier can widen what gets *found*, but it never
widens what gets auto-applied without review. Every heal event records which
tier produced it (`source: "heuristic"` or `"llm"`), visible via
`shl report`.

## Demos

Two narrated end-to-end scenarios, run against a real headless Chromium via
Playwright:

```bash
python demo/run_demo.py       # plain UI redesign: ids/classes regenerated
```

`demo/fixtures/login_v1.html` / `login_v2.html` simulate a redesign where
every id and class is regenerated, with a decoy "Cancel" button next to the
real "Log In" button, proving the healer disambiguates by more than tag name.

The CRM-shaped scenario lives in the test suite (`tests/test_crm_healing.py`)
using `demo/fixtures/crm_v1.html` / `crm_v2.html` (+ `crm_notes_v1/v2.html`
for the iframe), which model:
- a Lightning-style "Save" button hidden inside an **open shadow root**,
- a Dynamics-style **iframe**'d notes form with its own "Save Note" button,
- a "Cancel" button relabeled **"Discard Changes"** on redesign — a case the
  risk gate must catch and defer to human review rather than auto-heal onto.

## Project layout

```
self_healing_locator/
  fingerprint.py       # JS snippets that capture an element's fingerprint (+ shadow-root walk)
  scoring.py            # weighted DOM-similarity scoring
  selector_builder.py   # turns a healed fingerprint back into a CSS selector (element + iframe)
  risk.py                 # destructive-candidate deny-list
  llm_healer.py            # opt-in GenAI fallback tier (pluggable backend: Copilot CLI / Claude / custom)
  store.py               # locators.yaml + healing report + pending-review persistence
  patcher.py              # rewrites inline selector literals in test source
  healer.py               # Healer: locate() / locate_inline() / multi-frame heal orchestration
  cli.py                  # `shl` command-line tool
demo/                      # UI-redesign + CRM-shaped fixtures, narrated demo script
tests/                      # unit tests + end-to-end tests (real browser via Playwright)
```

## Limitations

- **Closed shadow roots** aren't reachable from JavaScript at all (a browser
  platform restriction, not something this library can work around) — the
  agent only sees *open* shadow roots.
- Frame re-addressing recomputes the iframe's selector fresh from its
  *current* attributes each time (not similarity-scored), so if the target
  iframe itself has no stable `name`/`id`/`title`/`src`, healing inside it
  may fail even if the element itself would otherwise match.
- The risk deny-list is a coarse text/attribute filter, not semantic
  understanding — tune `risk_keywords=` for your client's terminology.
- The default `llm_backend="copilot_cli"` is a best-effort scrape of a tool
  (`gh copilot suggest`) that isn't designed for this — see § Optional GenAI
  fallback tier. It's a bonus tier, not a dependency: heuristic-only mode
  (`llm_fallback=False`, the default) is fully local and works with zero AI
  tooling installed.

## Tests

```bash
pytest
```

All browser-driven tests (`test_demo_healing.py`, `test_crm_healing.py`) run
against a real headless Chromium via Playwright; the rest are pure-Python
unit tests (scoring, selector building, risk detection, store persistence,
CLI, multi-tenant isolation).
