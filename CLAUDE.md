# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

This repository is currently an empty scaffold. The only tracked file is `README.md`, which
contains just the project title. There is no source code, build system, package manifest, test
suite, or CI configuration yet.

```
Testing/
├── README.md
└── CLAUDE.md
```

## Working in this repo

- There are no established conventions, frameworks, or tooling choices yet — if you are the first
  to add real code, pick sensible defaults for the stated purpose of the project and note the
  choice (language, package manager, test runner) in this file so future sessions stay consistent.
- Keep this file up to date as the project grows: once a build system, test command, or lint
  command exists, document the exact commands here (e.g. install, build, test, lint) so they don't
  need to be rediscovered.
- There is no `main`-branch history to reverse-engineer conventions from beyond the initial commit,
  so don't assume undocumented structure — check the actual files before relying on any assumed
  layout.
