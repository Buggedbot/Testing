"""End-to-end CLI tests for `qe`: each subcommand writes its prompt file."""

from tests.test_qe_genai import JUNIT_XML

from qe_genai.cli import main


def _junit(tmp_path, name="results.xml"):
    path = tmp_path / name
    path.write_text(JUNIT_XML)
    return path


def test_qe_triage_writes_prompt(tmp_path, capsys):
    log = tmp_path / "failure.log"
    log.write_text("TimeoutError: locator #save-btn")
    junit = _junit(tmp_path)
    out = tmp_path / "prompts"

    assert main(["triage", "--log", str(log), "--junit", str(junit), "--out", str(out)]) == 0
    content = (out / "failure_triage.prompt.md").read_text()
    assert "#save-btn" in content
    assert "test_apply_discount" in content  # failing test pulled from junit
    assert "Wrote" in capsys.readouterr().out


def test_qe_bugreport_writes_prompt(tmp_path):
    junit = _junit(tmp_path)
    src = tmp_path / "test_discount.py"
    src.write_text("def test_apply_discount(page): ...")
    out = tmp_path / "prompts"

    rc = main(
        [
            "bugreport", "--junit", str(junit), "--test", "test_apply_discount",
            "--test-source", str(src), "--environment", "QA, Chrome 126", "--out", str(out),
        ]
    )
    assert rc == 0
    content = (out / "bug_report.prompt.md").read_text()
    assert "## Title" in content and "Chrome 126" in content


def test_qe_bugreport_unknown_test_errors(tmp_path, capsys):
    junit = _junit(tmp_path)
    rc = main(["bugreport", "--junit", str(junit), "--test", "nope", "--out", str(tmp_path)])
    assert rc == 1
    assert "not found" in capsys.readouterr().err


def test_qe_flaky_writes_prompt(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    _junit(runs, "run-1.xml")
    _junit(runs, "run-2.xml")
    out = tmp_path / "prompts"

    assert main(["flaky", "--runs-dir", str(runs), "--out", str(out)]) == 0
    content = (out / "flaky_analysis.prompt.md").read_text()
    assert "run-1" in content and "run-2" in content


def test_qe_flaky_empty_dir_errors(tmp_path, capsys):
    empty = tmp_path / "runs"
    empty.mkdir()
    assert main(["flaky", "--runs-dir", str(empty), "--out", str(tmp_path)]) == 1
    assert "No .xml" in capsys.readouterr().err


def test_qe_coverage_review_convert_testdata_summary_runbook(tmp_path):
    out = tmp_path / "prompts"
    inv = tmp_path / "inventory.txt"; inv.write_text("test_a\ntest_b")
    spec = tmp_path / "spec.md"; spec.write_text("Leads can be converted")
    testfile = tmp_path / "test_x.py"; testfile.write_text("import time; time.sleep(5)")
    steps = tmp_path / "steps.md"; steps.write_text("1. Open app\n2. Click save")
    script = tmp_path / "setup.sh"; script.write_text("./provision.sh")
    junit = _junit(tmp_path)

    assert main(["coverage", "--inventory", str(inv), "--spec", str(spec), "--out", str(out)]) == 0
    assert main(["review", "--file", str(testfile), "--framework", "selenium", "--out", str(out)]) == 0
    assert main(["convert", "--steps", str(steps), "--framework", "playwright", "--out", str(out)]) == 0
    assert main(["testdata", "--entity", "CRM lead", "--count", "3", "--out", str(out)]) == 0
    assert main(["summary", "--junit", str(junit), "--audience", "stakeholder", "--out", str(out)]) == 0
    assert main(["runbook", "--file", str(script), "--title", "Setup", "--out", str(out)]) == 0

    expected = [
        "coverage_gap", "test_review", "manual_to_automation",
        "test_data", "release_summary", "runbook",
    ]
    for name in expected:
        assert (out / f"{name}.prompt.md").exists(), name
