"""End-to-end demonstration: a locator map learned against `login_v1.html`
keeps working against `login_v2.html`, a simulated redesign that renamed every
id and class, because the healer re-identifies elements by tag/type/text/name
instead of by their (now-broken) ids.
"""

from pathlib import Path

import pytest

from self_healing_locator import Healer

FIXTURES = Path(__file__).parent.parent / "demo" / "fixtures"


def test_self_healing_survives_ui_redesign(tmp_path, page):
    store_path = tmp_path / "locators.yaml"
    healer = Healer(store_path, confidence_threshold=0.55)

    # --- Step 1: original UI. Learn locators by their (currently working) selectors.
    page.goto((FIXTURES / "login_v1.html").as_uri())

    username = healer.locate(page, "username_field", selector="#username")
    password = healer.locate(page, "password_field", selector="#password")
    login_button = healer.locate(page, "login_button", selector="#login-btn")

    username.fill("alice")
    password.fill("s3cret")
    assert healer.store.get("login_button").selector == "#login-btn"

    # --- Step 2: simulated redesign. Every id/class changed; a decoy "Cancel"
    # button with the same tag was added, so healing must disambiguate by more
    # than just tag name.
    page.goto((FIXTURES / "login_v2.html").as_uri())

    username = healer.locate(page, "username_field")
    password = healer.locate(page, "password_field")
    login_button = healer.locate(page, "login_button")

    username.fill("alice")
    password.fill("s3cret")

    # The healer must have found the real "Log In" submit button, not "Cancel".
    assert login_button.inner_text() == "Log In"
    login_button.click()

    healed_spec = healer.store.get("login_button")
    assert healed_spec.selector != "#login-btn"
    assert healed_spec.heal_count == 1

    events = healer.store.heal_events()
    healed_names = {e["name"] for e in events}
    assert {"username_field", "password_field", "login_button"} <= healed_names

    login_event = next(e for e in events if e["name"] == "login_button")
    assert login_event["score"] >= 0.55


def test_healing_fails_below_confidence_threshold(tmp_path, page):
    from self_healing_locator.exceptions import HealingFailedError

    store_path = tmp_path / "locators.yaml"
    # Unreasonably strict threshold: even a perfect textual match won't satisfy it.
    healer = Healer(store_path, confidence_threshold=0.999)

    page.goto((FIXTURES / "login_v1.html").as_uri())
    healer.locate(page, "login_button", selector="#login-btn")

    page.goto((FIXTURES / "login_v2.html").as_uri())
    with pytest.raises(HealingFailedError):
        healer.locate(page, "login_button")
