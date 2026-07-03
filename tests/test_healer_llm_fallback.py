"""End-to-end coverage for the opt-in GenAI healing tier. Uses a fake backend
callable (no real LLM/network call) to prove the wiring: it only engages when
heuristic confidence is too low, its picks still go through the risk gate,
and it's a no-op unless explicitly enabled.
"""

import json
from pathlib import Path

import pytest

from self_healing_locator import Healer
from self_healing_locator.exceptions import HealingFailedError, HealingRequiresReviewError

FIXTURES = Path(__file__).parent.parent / "demo" / "fixtures"


def _backend_that_picks(text: str, confidence: float = 0.9):
    def backend(prompt: str) -> str:
        payload = json.loads(prompt[prompt.index("{"):])
        idx = next(c["index"] for c in payload["candidates"] if c.get("text") == text)
        return json.dumps({"candidate_index": idx, "confidence": confidence, "reasoning": "text match"})

    return backend


def test_llm_fallback_heals_when_heuristic_confidence_too_low(tmp_path, page):
    healer = Healer(
        tmp_path / "locators.yaml",
        confidence_threshold=0.9,  # heuristic alone (~0.65) won't clear this
        llm_fallback=True,
        llm_backend=_backend_that_picks("Log In"),
    )

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    login_button = healer.locate(page, "login_button")

    assert login_button.inner_text() == "Log In"

    events = healer.store.heal_events()
    assert events[-1]["source"] == "llm"


def test_llm_pick_still_blocked_by_risk_gate(tmp_path, page):
    healer = Healer(
        tmp_path / "locators.yaml",
        confidence_threshold=0.65,  # heuristic score for this pair (~0.53) is below this
        llm_fallback=True,
        llm_backend=_backend_that_picks("Discard Changes"),
    )

    page.goto((FIXTURES / "crm_v1.html").as_uri())
    healer.locate(page, "cancel_button", selector="#cancel-btn")

    page.goto((FIXTURES / "crm_v2.html").as_uri())
    with pytest.raises(HealingRequiresReviewError):
        healer.locate(page, "cancel_button")

    spec = healer.store.get("cancel_button")
    assert spec.selector == "#cancel-btn"  # not auto-applied

    pending = healer.store.list_pending()
    assert len(pending) == 1
    assert pending[0].source == "llm"


def test_llm_fallback_not_used_when_disabled(tmp_path, page):
    healer = Healer(tmp_path / "locators.yaml", confidence_threshold=0.9, llm_fallback=False)

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")


def test_backend_returning_none_falls_back_to_healing_failed(tmp_path, page):
    healer = Healer(
        tmp_path / "locators.yaml",
        confidence_threshold=0.9,
        llm_fallback=True,
        llm_backend=lambda prompt: None,  # simulates gh copilot producing nothing usable
    )

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")
