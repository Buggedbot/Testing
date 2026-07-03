import os

import pytest
from playwright.sync_api import sync_playwright

# This sandbox pre-provisions a Chromium build outside Playwright's own
# managed cache; point at it explicitly instead of triggering a download.
_PREINSTALLED_CHROMIUM = "/opt/pw-browsers/chromium"


def _launch_kwargs() -> dict:
    if os.path.exists(_PREINSTALLED_CHROMIUM):
        return {"executable_path": _PREINSTALLED_CHROMIUM}
    return {}


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(**_launch_kwargs())
        pg = browser.new_page()
        yield pg
        browser.close()
