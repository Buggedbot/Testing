"""Regression coverage for the "keeps suggesting/applying the same wrong fix"
failure mode: a wrong pick (from any tier, or a human via `assist-apply`)
must never be re-proposed on a later retry against the same broken page.
"""

import json
from pathlib import Path

import pytest

from self_healing_locator import Healer
from self_healing_locator.exceptions import HealingFailedError

FIXTURES = Path(__file__).parent.parent / "demo" / "fixtures"


def test_previously_failed_selector_is_never_resuggested(tmp_path, page):
    store_path = tmp_path / "locators.yaml"
    healer = Healer(store_path, confidence_threshold=0.5)

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    healed = healer.locate(page, "login_button")
    first_selector = healer.store.get("login_button").selector
    assert healed.inner_text() == "Log In"

    # Simulate the fix turning out to be wrong after the fact (e.g. a human
    # applied a bad selector via `assist-apply` earlier): revert to the
    # original broken selector but keep the record that `first_selector`
    # didn't actually work.
    healer.store.update_selector("login_button", "#login-btn", healer.store.get("login_button").fingerprint)
    healer.store.record_failed_attempt("login_button", first_selector)

    # Healing again must not silently reapply the exact same selector. The
    # only other candidate ("Cancel") won't clear this threshold, so this
    # should fail loudly instead of quietly repeating the known-bad guess.
    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")

    spec = healer.store.get("login_button")
    assert spec.selector == "#login-btn"  # never silently overwritten with the known-bad pick
    assert first_selector in spec.failed_selectors


def test_llm_tier_never_offered_a_previously_failed_candidate(tmp_path, page):
    def backend_that_picks(text: str):
        def backend(prompt: str) -> str:
            payload = json.loads(prompt[prompt.index("{"):])
            idx = next((c["index"] for c in payload["candidates"] if c.get("text") == text), -1)
            return json.dumps({"candidate_index": idx, "confidence": 0.9, "reasoning": "text match"})

        return backend

    store_path = tmp_path / "locators.yaml"
    healer = Healer(
        store_path,
        confidence_threshold=0.9,
        llm_fallback=True,
        llm_backend=backend_that_picks("Log In"),
    )

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    login_button = healer.locate(page, "login_button")
    healed_selector = healer.store.get("login_button").selector
    assert login_button.inner_text() == "Log In"

    # Revert and mark that selector as a known-bad pick, as if it turned out wrong.
    healer.store.update_selector("login_button", "#login-btn", healer.store.get("login_button").fingerprint)
    healer.store.record_failed_attempt("login_button", healed_selector)

    seen_candidate_texts = []

    def recording_backend(prompt: str) -> str:
        payload = json.loads(prompt[prompt.index("{"):])
        seen_candidate_texts.extend(c.get("text") for c in payload["candidates"])
        assert payload.get("previously_tried_and_failed") == [healed_selector]
        return json.dumps({"candidate_index": -1, "confidence": 0.0, "reasoning": "n/a"})

    healer.llm_backend = recording_backend

    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")

    # The "Log In" candidate must be filtered out before it ever reaches the
    # backend -- not just discouraged by prompt text.
    assert "Log In" not in seen_candidate_texts
