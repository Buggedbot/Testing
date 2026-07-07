# Flaky Test Analysis

**What it does:** collapses N historical JUnit reports (one per CI run) into
a compact per-test pass/fail history table and asks Copilot Chat which tests
show **flakiness signatures** (intermittent, order-dependent, time-of-day
correlated) versus **consistent regressions**, with a proposed quarantine
list and reasoning.

## Use case

Every QE team has the "is it flaky or is it broken?" argument. The raw data
to settle it exists in your Azure DevOps run history, but nobody enjoys
assembling it. Run this monthly (or per sprint): download the last ~20 JUnit
artifacts from your pipeline runs into a folder, run one command, paste, and
get a defensible quarantine/fix-first list to bring to the team — instead of
gut feeling.

Works identically for Selenium and Playwright suites (and any other team's
stack) because it only reads JUnit XML.

## How to run

```bash
# runs/ contains one JUnit xml per pipeline run, e.g. run-101.xml ... run-120.xml
qe flaky --runs-dir runs/ --out qe_prompts/

# Fetching the artifacts from Azure DevOps first (example):
# az pipelines runs list --pipeline-ids <id> --top 20 --query "[].id" -o tsv | while read id; do
#   az pipelines runs artifact download --run-id $id --artifact-name test-results --path runs/$id
# done
```

## What you get

`qe_prompts/flaky_analysis.prompt.md` containing a `test × run` outcome
matrix (`P`/`F`/`E`/`S`) plus failure-message samples, and instructions to
classify each unstable test as FLAKY / REGRESSION / NEEDS-DATA with evidence.

## Limitations

- Needs enough history to mean anything — under ~5 runs the classification
  is guesswork, and the prompt says so to the model.
- A test that's "flaky" here may still be a real product race condition;
  quarantine is a routing decision, not an acquittal.
