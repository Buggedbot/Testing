# Bug Report Drafting (Azure DevOps)

**What it does:** turns a confirmed test failure into a filled-in **Azure
DevOps Bug work item draft** — Title, Repro Steps (derived from the test's
own steps), Expected vs Actual, System Info, and a suggested Severity — so
the QE reviews and pastes instead of writing from scratch.

## Use case

Triage (see `failure_triage/`) said "product bug." Writing a good ADO bug —
clean repro steps, expected/actual, environment — takes 10+ minutes and the
quality varies by author. This tool assembles the raw material (failure
message, the test's source code, environment details) into a prompt; Copilot
Chat returns a complete draft in ADO's field structure. The QE fixes anything
wrong and pastes it into the New Bug form (or `az boards work-item create`).

## How to run

```bash
qe bugreport \
  --junit artifacts/test-results.xml \
  --test "tests.checkout.CheckoutTests::test_apply_discount" \
  --test-source tests/checkout/test_discount.py \
  --environment "QA env, Chrome 126, build 2024.7.3" \
  --area-path "CRM\\Checkout" \
  --out qe_prompts/
```

`--test-source` matters: the model derives human-readable repro steps from
what the test actually does (navigate → fill → click → assert), which is far
more accurate than guessing from the failure message alone.

## What you get

`qe_prompts/bug_report.prompt.md`. The prompt asks for output structured as
ADO Bug fields (Title / Repro Steps / Expected / Actual / System Info /
suggested Severity + Area Path) in copy-paste-ready Markdown/HTML.

## Limitations

- Never file the draft unread — the model may over-claim certainty about the
  root cause. The draft describes *symptoms* well; verify any *cause* claims.
- Severity is a suggestion; your team's severity policy wins.
