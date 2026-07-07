"""Unit tests for the qe_genai toolkit: JUnit parsing + every prompt builder.
Pure Python -- no browser, no network.
"""

from qe_genai import (
    bug_report,
    coverage_gap,
    failure_triage,
    flaky_analysis,
    manual_to_automation,
    release_summary,
    runbook,
    test_data,
    test_review,
)
from qe_genai.common import (
    TestResult as JUnitResult,  # aliased so pytest doesn't try to collect it
    format_failures,
    parse_junit,
    parse_junit_many,
    summarize_results,
    write_prompt_file,
)

JUNIT_XML = """<?xml version="1.0"?>
<testsuites>
  <testsuite name="checkout" tests="3">
    <testcase classname="tests.checkout" name="test_apply_discount" time="4.2">
      <failure message="AssertionError: expected 90.00, got 100.00">trace here</failure>
    </testcase>
    <testcase classname="tests.checkout" name="test_add_to_cart" time="2.0"/>
    <testcase classname="tests.checkout" name="test_legacy_flow" time="0.1">
      <skipped message="deprecated"/>
    </testcase>
  </testsuite>
</testsuites>
"""


def _write_junit(tmp_path, name="run-1.xml", xml=JUNIT_XML):
    path = tmp_path / name
    path.write_text(xml)
    return path


def _result(**overrides):
    base = dict(
        name="test_apply_discount",
        classname="tests.checkout",
        status="failed",
        time=4.2,
        message="AssertionError: expected 90.00, got 100.00",
    )
    base.update(overrides)
    return JUnitResult(**base)


# -- common ----------------------------------------------------------------


def test_parse_junit_extracts_statuses_and_messages(tmp_path):
    results = parse_junit(_write_junit(tmp_path))
    by_name = {r.name: r for r in results}
    assert by_name["test_apply_discount"].status == "failed"
    assert "expected 90.00" in by_name["test_apply_discount"].message
    assert by_name["test_add_to_cart"].status == "passed"
    assert by_name["test_legacy_flow"].status == "skipped"
    assert by_name["test_apply_discount"].full_name == "tests.checkout::test_apply_discount"


def test_parse_junit_many_keys_by_stem_sorted(tmp_path):
    _write_junit(tmp_path, "run-2.xml")
    _write_junit(tmp_path, "run-1.xml")
    runs = parse_junit_many(tmp_path.glob("*.xml"))
    assert list(runs.keys()) == ["run-1", "run-2"]


def test_summarize_and_format_failures(tmp_path):
    results = parse_junit(_write_junit(tmp_path))
    counts = summarize_results(results)
    assert counts == {"passed": 1, "failed": 1, "error": 0, "skipped": 1, "total": 3}
    text = format_failures(results)
    assert "test_apply_discount" in text
    assert "test_add_to_cart" not in text


def test_write_prompt_file_appends_footer(tmp_path):
    path = write_prompt_file(tmp_path / "out", "demo", "PROMPT BODY")
    assert path.name == "demo.prompt.md"
    content = path.read_text()
    assert content.startswith("PROMPT BODY")
    assert "Paste everything above" in content


# -- prompt builders ---------------------------------------------------------


def test_triage_prompt_includes_all_sections():
    prompt = failure_triage.build_prompt(
        "Traceback: element #login-btn not found",
        failures=[_result()],
        diff_text="- old line\n+ new line",
    )
    assert "PRODUCT BUG" in prompt
    assert "#login-btn" in prompt
    assert "test_apply_discount" in prompt
    assert "+ new line" in prompt


def test_triage_prompt_marks_missing_diff():
    prompt = failure_triage.build_prompt("log")
    assert "(not provided)" in prompt


def test_bug_report_prompt_has_ado_fields_and_source():
    prompt = bug_report.build_prompt(
        _result(),
        test_source="def test_apply_discount(page): ...",
        environment="QA env, Chrome 126",
        area_path="CRM\\Checkout",
    )
    assert "## Title" in prompt and "## Repro Steps" in prompt and "Severity" in prompt
    assert "def test_apply_discount" in prompt
    assert "Chrome 126" in prompt
    assert "CRM\\Checkout" in prompt


def test_flaky_prompt_builds_history_matrix(tmp_path):
    runs = {
        "run-1": [_result(status="passed", message="")],
        "run-2": [_result()],
        "run-3": [_result(status="passed", message="")],
    }
    prompt = flaky_analysis.build_prompt(runs)
    assert "P F P" in prompt
    assert "FLAKY" in prompt and "REGRESSION" in prompt
    assert "low-confidence" in prompt  # only 3 runs -> small-sample note


def test_coverage_prompt_contains_spec_and_inventory():
    prompt = coverage_gap.build_prompt("test_a\ntest_b", "Users can convert a lead to an opportunity")
    assert "test_a" in prompt
    assert "convert a lead" in prompt
    assert "Negative paths" in prompt


def test_review_prompt_framework_notes():
    pw = test_review.build_prompt("await page.click()", framework="playwright")
    se = test_review.build_prompt("driver.find_element(...)", framework="selenium")
    assert "Playwright" in pw and "waitForTimeout" in pw
    assert "WebDriverWait" in se
    diff = test_review.build_prompt("+ added line", framework="generic", is_diff=True)
    assert "```diff" in diff


def test_convert_prompt_with_and_without_style_anchor():
    with_example = manual_to_automation.build_prompt(
        "1. Open login page\n2. Enter credentials", framework="selenium", example_test="def test_x(): ..."
    )
    assert "Selenium WebDriver" in with_example
    assert "Style anchor" in with_example
    without = manual_to_automation.build_prompt("1. Step", framework="playwright")
    assert "No style example was provided" in without
    assert "TODO(locator)" in without


def test_testdata_prompt_embeds_schema_and_focus():
    prompt = test_data.build_prompt(
        "CRM contact", count=5, schema_text='{"name": "x"}', focus="unicode names"
    )
    assert "5 realistic" in prompt
    assert '"name"' in prompt
    assert "unicode names" in prompt
    assert "_edge_case" in prompt


def test_summary_prompt_counts_table_and_audiences():
    runs = {"run-1": [_result(), _result(name="ok", status="passed", message="")]}
    tech = release_summary.build_prompt(runs, audience="technical")
    stake = release_summary.build_prompt(runs, audience="stakeholder", context="release Thursday")
    assert "| run-1 | 2 | 1 | 1 | 0 | 0 |" in tech
    assert "fix-first" in tech
    assert "not-ready" in stake  # go/no-go recommendation scale
    assert "release Thursday" in stake


def test_runbook_prompt_includes_title_and_script():
    prompt = runbook.build_prompt("export FOO=bar\n./setup.sh", title="QA env setup")
    assert "QA env setup" in prompt
    assert "./setup.sh" in prompt
    assert "Hidden assumptions" in prompt
