"""Coverage for the file-based Copilot Chat hand-off (copilot_assist=True):
the realistic path when the only AI tooling available is an IDE integration
with no callable API, so healing failures get written to a Markdown file for
a human to run through chat by hand.
"""

from pathlib import Path

import pytest

from self_healing_locator import Healer, copilot_assist
from self_healing_locator.exceptions import HealingFailedError

FIXTURES = Path(__file__).parent.parent / "demo" / "fixtures"


def test_failed_heal_writes_assist_entry(tmp_path, page):
    store_path = tmp_path / "locators.yaml"
    healer = Healer(store_path, confidence_threshold=0.9, copilot_assist=True)

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")

    names = copilot_assist.pending_assist_names(store_path)
    assert names == ["login_button"]

    _, md_path = copilot_assist.assist_paths(store_path)
    content = md_path.read_text()
    assert "## login_button" in content
    assert "#login-btn" in content
    assert "Log In" in content  # a real candidate should be listed


def test_successful_heal_clears_prior_assist_entry(tmp_path, page):
    store_path = tmp_path / "locators.yaml"

    strict_healer = Healer(store_path, confidence_threshold=0.9, copilot_assist=True)
    page.goto((FIXTURES / "login_v1.html").as_uri())
    strict_healer.locate(page, "login_button", selector="#login-btn")
    page.goto((FIXTURES / "login_v2.html").as_uri())
    with pytest.raises(HealingFailedError):
        strict_healer.locate(page, "login_button")
    assert copilot_assist.pending_assist_names(store_path) == ["login_button"]

    # A more lenient healer against the same store succeeds heuristically.
    lenient_healer = Healer(store_path, confidence_threshold=0.5, copilot_assist=True)
    login_button = lenient_healer.locate(page, "login_button")
    assert login_button.inner_text() == "Log In"

    assert copilot_assist.pending_assist_names(store_path) == []


def test_assist_not_written_when_disabled(tmp_path, page):
    store_path = tmp_path / "locators.yaml"
    healer = Healer(store_path, confidence_threshold=0.9, copilot_assist=False)

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")

    json_path, md_path = copilot_assist.assist_paths(store_path)
    assert not json_path.exists()
    assert not md_path.exists()


def test_assist_entry_lists_previously_failed_selectors(tmp_path, page):
    store_path = tmp_path / "locators.yaml"
    healer = Healer(store_path, confidence_threshold=0.9, copilot_assist=True)

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")  # first failure: records "#login-btn"

    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")  # second failure: still just "#login-btn" (dedup)

    _, md_path = copilot_assist.assist_paths(store_path)
    content = md_path.read_text()
    assert "Already tried and still broken" in content
    assert "#login-btn" in content
    assert healer.store.get("login_button").failed_selectors == ["#login-btn"]
