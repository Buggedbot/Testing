# Coverage Gap Analysis

**What it does:** takes your existing test inventory (names/titles of every
automated test) plus a feature spec or user story, and asks Copilot Chat
what is **not** covered — missing negative paths, boundary conditions, role/
permission variants, and cross-feature interactions.

## Use case

The inverse of test-case generation (which you already have an agent for).
Generation answers "write me tests for X"; this answers "what did we forget?"
Run it as part of feature sign-off: paste the Azure DevOps user story's
acceptance criteria and the current test list, and get a gap list to either
accept as known risk or turn into new cases (feed the gaps straight into your
test-case-creation agent).

## How to run

```bash
# Get the inventory from your framework:
#   pytest --collect-only -q > inventory.txt          (Selenium/pytest)
#   npx playwright test --list > inventory.txt        (Playwright)

qe coverage \
  --inventory inventory.txt \
  --spec user_story_1234.md \
  --out qe_prompts/
```

`--spec` can be the ADO user story description + acceptance criteria copied
into a file, a PRD section, or an API contract.

## What you get

`qe_prompts/coverage_gap.prompt.md`. The prompt asks for gaps grouped by
category (happy-path variants / negative / boundary / permissions / non-
functional), each with a suggested test title and a priority.

## Limitations

- It reasons from test *names* — misleadingly-named tests produce misleading
  gap reports. (This is also a decent incentive to name tests honestly.)
- It can only find gaps relative to the spec you provide; unstated
  requirements stay unstated.
