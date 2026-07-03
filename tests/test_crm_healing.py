"""End-to-end coverage for the CRM-shaped concerns: controls hidden inside an
open shadow root (Salesforce-Lightning style), controls embedded in an iframe
(Dynamics-style), and a rename that lands on a destructive-looking label
("Discard Changes"), which must be withheld from auto-apply.
"""

from pathlib import Path

import pytest

from self_healing_locator import Healer
from self_healing_locator.exceptions import HealingRequiresReviewError

FIXTURES = Path(__file__).parent.parent / "demo" / "fixtures"


def _learn_crm_locators(healer, page):
    page.goto((FIXTURES / "crm_v1.html").as_uri())
    healer.locate(page, "save_button", selector="#save-btn")
    healer.locate(page, "cancel_button", selector="#cancel-btn")
    healer.locate(page, "save_note_button", selector="#save-note-btn")


def test_heals_through_shadow_dom(tmp_path, page):
    healer = Healer(tmp_path / "locators.yaml", confidence_threshold=0.5)
    _learn_crm_locators(healer, page)

    page.goto((FIXTURES / "crm_v2.html").as_uri())
    save_button = healer.locate(page, "save_button")

    assert save_button.inner_text() == "Save"
    save_button.click()

    spec = healer.store.get("save_button")
    assert spec.selector != "#save-btn"
    assert spec.frame_selector is None  # shadow DOM is pierced automatically, no frame needed


def test_heals_across_iframe_boundary(tmp_path, page):
    healer = Healer(tmp_path / "locators.yaml", confidence_threshold=0.5)
    _learn_crm_locators(healer, page)

    page.goto((FIXTURES / "crm_v2.html").as_uri())
    save_note_button = healer.locate(page, "save_note_button")

    assert save_note_button.inner_text() == "Save Note"

    spec = healer.store.get("save_note_button")
    assert spec.selector != "#save-note-btn"
    assert spec.frame_selector is not None
    assert "notes-frame" in spec.frame_selector  # re-addressed via the iframe's (new) id/title


def test_risky_rename_requires_review_instead_of_auto_healing(tmp_path, page):
    healer = Healer(tmp_path / "locators.yaml", confidence_threshold=0.5)
    _learn_crm_locators(healer, page)

    page.goto((FIXTURES / "crm_v2.html").as_uri())
    with pytest.raises(HealingRequiresReviewError):
        healer.locate(page, "cancel_button")

    # The store must NOT have been auto-updated to point at "Discard Changes".
    spec = healer.store.get("cancel_button")
    assert spec.selector == "#cancel-btn"

    pending = healer.store.list_pending()
    assert len(pending) == 1
    assert pending[0].name == "cancel_button"
    assert "discard" in pending[0].fingerprint["text"].lower()


def test_approving_a_pending_heal_applies_it(tmp_path, page):
    healer = Healer(tmp_path / "locators.yaml", confidence_threshold=0.5)
    _learn_crm_locators(healer, page)

    page.goto((FIXTURES / "crm_v2.html").as_uri())
    with pytest.raises(HealingRequiresReviewError):
        healer.locate(page, "cancel_button")

    pending = healer.store.pop_pending("cancel_button")
    healer.store.update_selector(
        pending.name, pending.new_selector, pending.fingerprint, frame_selector=pending.frame_selector
    )

    spec = healer.store.get("cancel_button")
    assert spec.selector == pending.new_selector
    assert healer.store.list_pending() == []
