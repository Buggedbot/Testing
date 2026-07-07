# Runbook / Onboarding Doc Generation

**What it does:** wraps a setup script, pipeline YAML, or gnarly shell
snippet in a prompt that produces a step-by-step runbook a new QE joiner can
follow — what each step does, what "working" looks like, and the common
failure at each step.

## Use case

Test environments accrete: a `setup_env.sh` nobody fully understands, an
Azure DevOps pipeline YAML with tribal-knowledge variables, a wiki page two
reorgs out of date. When a new QE joins, someone burns an afternoon walking
them through it. Point this at the actual script — which, unlike the wiki, is
always current — and get a draft runbook to review and publish. Refresh it
whenever the script changes materially.

## How to run

```bash
qe runbook --file scripts/setup_test_env.sh --title "QA environment setup" --out qe_prompts/
qe runbook --file azure-pipelines.yml --title "Nightly regression pipeline" --out qe_prompts/
```

## What you get

`qe_prompts/runbook.prompt.md`. The prompt asks for: prerequisites, numbered
steps with the *why* alongside the *what*, expected output per step, a
troubleshooting table (symptom → likely cause → fix), and an explicit list of
things the script assumes but doesn't check (the tribal-knowledge section).

## Limitations

- The model documents what the script *does*, which occasionally differs from
  what the team *thinks* it does — treat surprising statements in the draft
  as prompts to check the script, not errors to delete.
