# VS Code Copilot Agents for QE

GitHub Copilot in VS Code supports team-shareable customization that turns
plain chat into purpose-built **QE agents** — no API key, no extension
development, just files checked into the repo. Three mechanisms:

| Mechanism | File location | What it gives you |
|---|---|---|
| **Custom chat modes** ("agents") | `.github/chatmodes/*.chatmode.md` | A named mode in the chat dropdown (next to Ask/Edit/Agent) with its own persona, rules, and tool access. Pick "QE Test Reviewer" and every message in that conversation is a test review. |
| **Prompt files** (slash commands) | `.github/prompts/*.prompt.md` | Reusable prompts the whole team runs as `/harden-test`, `/convert-manual` etc. in chat — the shareable version of `../copilot_prompts/`. |
| **Repo instructions** | `.github/copilot-instructions.md` | Standing conventions Copilot applies to *every* chat and completion in this repo (your locator policy, wait policy, page-object pattern). |

**Install:** copy the contents of [`github_assets/`](github_assets/) into the
`.github/` directory of your test-automation repo, commit, and reload VS
Code. Everyone with a Copilot seat gets the agents automatically — this is
how you distribute QE-AI practices across the team (and to other teams on
other stacks: the files are plain Markdown, easily adapted).

## What's included

- `chatmodes/qe-test-reviewer.chatmode.md` — review-only agent: flakiness,
  assertions, locators, isolation; refuses to drift into feature discussion.
- `chatmodes/qe-triage.chatmode.md` — failure-triage agent: paste a log/stack
  trace, get product-bug/test-bug/environment/flaky verdicts with evidence.
  (The `qe triage` CLI builds richer input files for it.)
- `chatmodes/qe-test-generator.chatmode.md` — test-writing agent bound to
  your conventions; uses workspace context to match your page objects.
- `prompts/harden-test.prompt.md` — `/harden-test`: de-flake the selected test.
- `prompts/convert-manual.prompt.md` — `/convert-manual`: manual steps →
  automation skeleton.
- `prompts/edge-data.prompt.md` — `/edge-data`: adversarial fixture records.
- `copilot-instructions.md` — template repo conventions; **edit the marked
  sections** to match your suite before committing.

## Agent mode + these files

VS Code's built-in **Agent mode** (autonomous multi-file edits) also obeys
`copilot-instructions.md`. That combination is the closest thing to an
autonomous QE agent available without any API access: e.g. select Agent mode
and ask *"migrate every test in tests/legacy/ from Selenium waits to the
conventions in this repo"* — it will edit across files while following your
committed rules. Keep the human review on the diff; that's the safety gate.

## Relationship to the `qe` CLI

The CLI tools (`qe triage`, `qe flaky`, …) gather context chat can't see —
CI artifacts, JUnit history, git diffs — into prompt files. These agents make
the *chat side* better. They compose: run `qe triage`, open the generated
prompt file in VS Code, and send it in the **QE Triage** chat mode.
