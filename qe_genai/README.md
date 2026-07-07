# QE GenAI Toolkit (GitHub-Copilot-only environments)

GenAI implementations a QE team can actually use when the **only** AI access
is a GitHub Copilot seat in VS Code — no LLM API keys, no external services.
Built for a team on **Azure DevOps** running **Selenium and Playwright**, but
deliberately framework-agnostic: everything that consumes test results reads
**JUnit XML**, which Selenium (pytest/TestNG), Playwright, and ADO's
PublishTestResults task all produce — so other teams on other stacks can use
it unchanged.

## The pattern

Copilot's IDE chat can't be called from a script, so every tool here splits
the work the same way as `self_healing_locator/copilot_assist.py`:

```
script gathers context          human pastes into           human applies
(logs, JUnit, diffs, specs) --> Copilot Chat, reads     --> the answer (file
into a .prompt.md file          the answer                  bug, commit, decide)
```

The scripts do what scripts are good at (collecting artifacts, computing
counts, formatting); the human keeps judgment and the paste step. These save
**thinking and writing** time, not pipeline time — when you later get any
callable LLM API, the same prompt builders can be wired to it directly.

## Tools (one folder each — see each folder's README for the full use case)

| Command | Folder | One-line use case |
|---|---|---|
| `qe triage` | [`failure_triage/`](failure_triage/) | Red pipeline → product-bug / test-bug / environment / flaky verdict per failure, with evidence |
| `qe bugreport` | [`bug_report/`](bug_report/) | Confirmed failure → filled Azure DevOps Bug work item draft (title, repro steps, severity) |
| `qe flaky` | [`flaky_analysis/`](flaky_analysis/) | N runs of JUnit history → quarantine list with FLAKY vs REGRESSION reasoning |
| `qe coverage` | [`coverage_gap/`](coverage_gap/) | Test inventory + user story → what's NOT covered, by category and priority |
| `qe review` | [`test_review/`](test_review/) | Test file/diff → flakiness & assertion review before the PR merges |
| `qe convert` | [`manual_to_automation/`](manual_to_automation/) | ADO Test Plans steps / Gherkin → Playwright or Selenium skeleton in your house style |
| `qe testdata` | [`test_data/`](test_data/) | Entity + schema → adversarial CRM fixture records (unicode, RTL, boundaries) as JSON |
| `qe summary` | [`release_summary/`](release_summary/) | JUnit report(s) → technical channel summary AND plain-language stakeholder readout |
| `qe runbook` | [`runbook/`](runbook/) | Setup script / pipeline YAML → step-by-step onboarding runbook with tribal-knowledge section |
| — | [`copilot_prompts/`](copilot_prompts/) | Zero-setup copy-paste prompt library for in-editor work (hardening, migration, page-object extraction) |
| — | [`vscode_agents/`](vscode_agents/) | **Copilot agents for VS Code**: custom chat modes (QE Reviewer / Triage / Generator), `/slash-command` prompt files, and repo instructions — drop into `.github/` and the whole team gets them |

## Install & run

```bash
pip install -e .          # from the repo root; adds the `qe` command
qe --help
qe triage --log failure.log --junit results.xml
```

Output lands in `./qe_prompts/*.prompt.md` (configurable with `--out`).
Add `qe_prompts/` to your `.gitignore` — prompts are working artifacts and
may embed logs/diffs you don't want in history.

## Azure DevOps integration sketch

- **On failure**: a pipeline step runs `qe triage` (+ `qe bugreport` for
  known-real failures) and publishes `qe_prompts/` as a build artifact — the
  QE downloads one ready-to-paste file instead of spelunking the run.
- **Nightly/weekly**: a job collects the last N runs' JUnit artifacts and
  runs `qe flaky` + `qe summary --audience stakeholder`.
- **Pre-merge**: `git diff origin/main...HEAD -- 'tests/**'` piped through
  `qe review --diff`.

The pipeline generates the prompts; humans with Copilot seats consume them.

## Relationship to the self-healing locator

Same repo, same philosophy, independent code: `self_healing_locator/` heals
broken locators (with its own Copilot handoff in `copilot_assist.py`); this
package covers the rest of the QE workflow. Neither imports the other, so a
Selenium-only team can take `qe_genai/` alone.
