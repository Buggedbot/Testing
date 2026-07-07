"""Build a flakiness-analysis prompt from multiple JUnit reports (one per CI
run). See README.md in this folder for the use case.
"""

from __future__ import annotations

from ..common import TestResult

_STATUS_CHAR = {"passed": "P", "failed": "F", "error": "E", "skipped": "S"}

_INSTRUCTIONS = """\
Below is a per-test outcome history across consecutive CI runs (oldest run
first). P=passed, F=failed, E=error, S=skipped, .=not in that run.

Classify every test that is not consistently passing as exactly one of:

- FLAKY: intermittent failures with no stable pattern (e.g. F scattered among
  P with no clean cut-over point). Recommend quarantine + a likely mechanism
  (timing, ordering, shared state, external dependency).
- REGRESSION: passed consistently, then fails consistently from some run
  onward (a clean cut-over). Name the run where it flipped.
- NEEDS-DATA: too few runs or too ambiguous to call -- say what additional
  evidence would settle it.

Then output a prioritized action list: which tests to quarantine, which to
investigate as regressions first, and which single fix would likely stabilize
the most tests (look for shared failure messages across tests).
"""


def _history_matrix(runs: dict[str, list[TestResult]]) -> str:
    run_names = list(runs.keys())  # already sorted by parse_junit_many
    all_tests: dict[str, dict[str, str]] = {}
    for run_name, results in runs.items():
        for r in results:
            all_tests.setdefault(r.full_name, {})[run_name] = _STATUS_CHAR.get(r.status, "?")

    lines = ["| test | " + " ".join(run_names) + " |", "|---|---|"]
    for test in sorted(all_tests):
        outcomes = " ".join(all_tests[test].get(rn, ".") for rn in run_names)
        lines.append(f"| `{test}` | {outcomes} |")
    return "\n".join(lines)


def _failure_samples(runs: dict[str, list[TestResult]], per_test_limit: int = 1) -> str:
    seen: dict[str, str] = {}
    for results in runs.values():
        for r in results:
            if r.status in ("failed", "error") and r.full_name not in seen and r.message:
                seen[r.full_name] = r.message.splitlines()[0][:200]
    if not seen:
        return "(no failure messages captured)"
    return "\n".join(f"- `{name}`: {msg}" for name, msg in sorted(seen.items()))


def build_prompt(runs: dict[str, list[TestResult]]) -> str:
    note = ""
    if len(runs) < 5:
        note = (
            f"\nNOTE: only {len(runs)} runs of history are available -- state "
            "clearly that classifications are low-confidence at this sample size.\n"
        )
    return "\n\n".join(
        [
            _INSTRUCTIONS + note,
            f"## Outcome history ({len(runs)} runs)\n\n" + _history_matrix(runs),
            "## Sample failure messages (first line, one per test)\n\n" + _failure_samples(runs),
        ]
    )
