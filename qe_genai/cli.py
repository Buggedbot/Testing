"""qe -- generate ready-to-paste Copilot Chat prompts for QE workflows.

Every subcommand gathers context (logs, JUnit reports, diffs, specs) and
writes `<out>/<tool>.prompt.md`. A human pastes that into GitHub Copilot Chat
(ideally in the matching chat mode from `vscode_agents/`) and acts on the
answer. No LLM API calls are made by this tool.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import bug_report, coverage_gap, failure_triage, flaky_analysis
from . import manual_to_automation, release_summary, runbook, test_data, test_review
from .common import parse_junit, parse_junit_many, read_text, write_prompt_file

DEFAULT_OUT = "qe_prompts"


def _emit(out_dir: str, name: str, prompt: str) -> int:
    path = write_prompt_file(out_dir, name, prompt)
    print(f"Wrote {path} -- paste its contents into Copilot Chat.")
    return 0


def _cmd_triage(args: argparse.Namespace) -> int:
    failures = None
    if args.junit:
        failures = [r for r in parse_junit(args.junit) if r.status in ("failed", "error")]
    diff_text = args.diff
    if args.diff_file:
        diff_text = read_text(args.diff_file)
    prompt = failure_triage.build_prompt(read_text(args.log), failures=failures, diff_text=diff_text)
    return _emit(args.out, "failure_triage", prompt)


def _cmd_bugreport(args: argparse.Namespace) -> int:
    results = parse_junit(args.junit)
    match = next((r for r in results if r.full_name == args.test or r.name == args.test), None)
    if match is None:
        failing = [r.full_name for r in results if r.status in ("failed", "error")]
        print(f"Test {args.test!r} not found in {args.junit}. Failing tests: {failing}", file=sys.stderr)
        return 1
    source = read_text(args.test_source) if args.test_source else None
    prompt = bug_report.build_prompt(
        match, test_source=source, environment=args.environment, area_path=args.area_path
    )
    return _emit(args.out, "bug_report", prompt)


def _cmd_flaky(args: argparse.Namespace) -> int:
    xml_files = sorted(Path(args.runs_dir).glob("**/*.xml"))
    if not xml_files:
        print(f"No .xml files found under {args.runs_dir}", file=sys.stderr)
        return 1
    runs = parse_junit_many(xml_files)
    return _emit(args.out, "flaky_analysis", flaky_analysis.build_prompt(runs))


def _cmd_coverage(args: argparse.Namespace) -> int:
    prompt = coverage_gap.build_prompt(read_text(args.inventory), read_text(args.spec))
    return _emit(args.out, "coverage_gap", prompt)


def _cmd_review(args: argparse.Namespace) -> int:
    prompt = test_review.build_prompt(read_text(args.file), framework=args.framework, is_diff=args.diff)
    return _emit(args.out, "test_review", prompt)


def _cmd_convert(args: argparse.Namespace) -> int:
    example = read_text(args.example) if args.example else None
    prompt = manual_to_automation.build_prompt(
        read_text(args.steps), framework=args.framework, example_test=example
    )
    return _emit(args.out, "manual_to_automation", prompt)


def _cmd_testdata(args: argparse.Namespace) -> int:
    schema = read_text(args.schema) if args.schema else None
    prompt = test_data.build_prompt(args.entity, count=args.count, schema_text=schema, focus=args.focus)
    return _emit(args.out, "test_data", prompt)


def _cmd_summary(args: argparse.Namespace) -> int:
    runs = parse_junit_many(args.junit)
    prompt = release_summary.build_prompt(runs, audience=args.audience, context=args.context)
    return _emit(args.out, "release_summary", prompt)


def _cmd_runbook(args: argparse.Namespace) -> int:
    prompt = runbook.build_prompt(read_text(args.file), title=args.title)
    return _emit(args.out, "runbook", prompt)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qe", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("triage", help="Failure triage: product bug vs test bug vs environment vs flaky")
    p.add_argument("--log", required=True, help="failure log / stack trace file")
    p.add_argument("--junit", help="JUnit XML report of the run")
    p.add_argument("--diff", help="diff since last green run, inline")
    p.add_argument("--diff-file", help="diff since last green run, from a file")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_triage)

    p = sub.add_parser("bugreport", help="Draft an Azure DevOps Bug work item from a failure")
    p.add_argument("--junit", required=True)
    p.add_argument("--test", required=True, help="full test name (classname::name) or bare name")
    p.add_argument("--test-source", help="path to the failing test's source file")
    p.add_argument("--environment", help='e.g. "QA env, Chrome 126, build 2024.7.3"')
    p.add_argument("--area-path", help='ADO area path, e.g. "CRM\\Checkout"')
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_bugreport)

    p = sub.add_parser("flaky", help="Flakiness analysis over multiple runs' JUnit reports")
    p.add_argument("--runs-dir", required=True, help="directory of JUnit XML files, one per run")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_flaky)

    p = sub.add_parser("coverage", help="Coverage-gap analysis: inventory + spec -> what's missing")
    p.add_argument("--inventory", required=True, help="test listing (pytest --collect-only -q output)")
    p.add_argument("--spec", required=True, help="feature spec / acceptance criteria file")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_coverage)

    p = sub.add_parser("review", help="Review a test file or test-only diff for flakiness/assertion issues")
    p.add_argument("--file", required=True)
    p.add_argument("--framework", choices=["playwright", "selenium", "generic"], default="generic")
    p.add_argument("--diff", action="store_true", help="treat the file as a diff")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_review)

    p = sub.add_parser("convert", help="Manual test case / Gherkin -> automation skeleton")
    p.add_argument("--steps", required=True, help="file with the manual steps or Gherkin")
    p.add_argument("--framework", choices=["playwright", "playwright-ts", "selenium"], default="playwright")
    p.add_argument("--example", help="an existing test file to use as the style anchor")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_convert)

    p = sub.add_parser("testdata", help="Adversarial edge-case fixture records as JSON")
    p.add_argument("--entity", required=True, help='e.g. "CRM contact"')
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--schema", help="JSON example record or JSON Schema file")
    p.add_argument("--focus", help="extra emphasis, e.g. 'unicode names, boundary dates'")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_testdata)

    p = sub.add_parser("summary", help="Run/release summary (technical or stakeholder voice)")
    p.add_argument("--junit", required=True, nargs="+", help="one or more JUnit XML files")
    p.add_argument("--audience", choices=["technical", "stakeholder"], default="technical")
    p.add_argument("--context", help="release context, e.g. 'release cut Thursday'")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_summary)

    p = sub.add_parser("runbook", help="Setup script / pipeline YAML -> onboarding runbook")
    p.add_argument("--file", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.set_defaults(func=_cmd_runbook)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
