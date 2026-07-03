"""Standalone, narrated demo (no pytest) of the self-healing locator agent.

Run with:  python demo/run_demo.py

Simulates a UI redesign between two page versions and shows the healer
detecting the break, re-identifying the element, and rewriting locators.yaml.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from self_healing_locator import Healer  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
STORE_PATH = Path(__file__).parent / "locators.yaml"

# This sandbox pre-provisions a Chromium build outside Playwright's own cache.
_PREINSTALLED_CHROMIUM = "/opt/pw-browsers/chromium"


def main() -> None:
    if STORE_PATH.exists():
        STORE_PATH.unlink()
    report_path = STORE_PATH.with_name(STORE_PATH.stem + ".report.json")
    if report_path.exists():
        report_path.unlink()

    healer = Healer(STORE_PATH, confidence_threshold=0.55)

    launch_kwargs = {"executable_path": _PREINSTALLED_CHROMIUM} if os.path.exists(_PREINSTALLED_CHROMIUM) else {}
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page()

        print("== Step 1: original UI (login_v1.html) ==")
        page.goto((FIXTURES / "login_v1.html").as_uri())
        healer.locate(page, "username_field", selector="#username")
        healer.locate(page, "password_field", selector="#password")
        healer.locate(page, "login_button", selector="#login-btn")
        print("Learned locators:")
        for name, spec in healer.store.all().items():
            print(f"  {name:16s} -> {spec.selector}")

        print("\n== Step 2: UI redesign deployed (login_v2.html) ==")
        print("  ids/classes were regenerated, e.g. #login-btn -> #act-3392")
        page.goto((FIXTURES / "login_v2.html").as_uri())

        username = healer.locate(page, "username_field")
        password = healer.locate(page, "password_field")
        login_button = healer.locate(page, "login_button")
        username.fill("alice")
        password.fill("s3cret")
        print(f"  Resolved login_button element text: {login_button.inner_text()!r}")
        login_button.click()

        print("\n== Healed locators.yaml ==")
        for name, spec in healer.store.all().items():
            print(f"  {name:16s} -> {spec.selector}  (heal_count={spec.heal_count})")

        print("\n== Healing report ==")
        print(json.dumps(healer.store.heal_events(), indent=2))

        browser.close()


if __name__ == "__main__":
    main()
