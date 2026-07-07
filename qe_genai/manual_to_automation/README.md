# Manual Test → Automation Skeleton

**What it does:** converts manual test cases (Azure DevOps Test Plans steps,
Gherkin scenarios, or plain numbered steps) into an automation skeleton in
your target framework — **Playwright or Selenium** — matching your team's
conventions via a style-anchor example you provide.

## Use case

Every QE team has a backlog of manual test cases that "we'll automate
eventually." The blocker is rarely difficulty — it's the tedium of the first
80%: boilerplate, page-object wiring, step-by-step translation. This tool
packages the manual steps plus one existing test from your suite (the style
anchor) so Copilot Chat produces a skeleton that looks like *your* code, not
generic tutorial code. The QE then fills in real locators and data — the 20%
that actually needs a human.

Pairs with your test-case-creation agent: cases it writes as Gherkin/steps
can be piped through this to become runnable skeletons.

## How to run

```bash
# Export the manual case from ADO Test Plans (or write steps in a file):
qe convert \
  --steps manual_cases/verify_lead_conversion.md \
  --framework playwright \
  --example tests/leads/test_create_lead.py \
  --out qe_prompts/
```

`--example` is strongly recommended: without it you get generic code; with it
you get your page-object pattern, your fixture style, your naming.

## What you get

`qe_prompts/manual_to_automation.prompt.md`. The prompt instructs the model
to produce one test per scenario, mark every guessed locator with
`# TODO(locator)`, and keep unautomatable steps (e.g. "verify email
received") as explicitly-skipped stubs rather than silently dropping them.

## Limitations

- Locators in the output are guesses until a human verifies them — that's
  what the `TODO(locator)` markers are for.
- One manual case (or a few closely related ones) per prompt; bulk conversion
  degrades quality fast.
