# Failure Triage

**What it does:** bundles everything a QE would manually gather when a test
fails — the failure log/stack trace, the failing tests from the JUnit report,
and the code diff since the last green run — into one structured prompt that
asks Copilot Chat to judge: **product bug, test/automation bug, environment
issue, or timing flakiness — and why.**

## Use case

A nightly Selenium or Playwright run in Azure DevOps goes red with 7
failures. Today someone spends 10–15 minutes per failure reading logs and
recent commits before even knowing who to route it to. With this tool the
pipeline (or the QE, locally) runs one command per failure, and triage
becomes: open the prompt file → paste into Copilot Chat → read a reasoned
verdict → route. The human still makes the call; the log-spelunking and
context-gathering is done for them.

## How to run

```bash
# minimal: just a log file
qe triage --log artifacts/failure.log

# richer context = better triage
qe triage \
  --log artifacts/failure.log \
  --junit artifacts/test-results.xml \
  --diff "$(git diff origin/main...HEAD)" \
  --out qe_prompts/
```

In an Azure DevOps pipeline, add a step on failure that captures
`$(git diff <last-green-sha>..HEAD)` and the published JUnit file, runs
`qe triage`, and publishes `qe_prompts/` as a build artifact — the QE
downloads one file instead of digging through the run.

## What you get

`qe_prompts/failure_triage.prompt.md` — paste it whole into Copilot Chat.
The prompt asks for a verdict per failure with a confidence level and the
specific evidence (log line / diff hunk) supporting it.

## Limitations

- The verdict is a draft: treat "product bug, high confidence" as "look here
  first," not as an automatic bug filing.
- Quality tracks input quality — a bare one-line log gives a bare guess;
  include the JUnit report and diff whenever available.
