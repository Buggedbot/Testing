"""Self-healing locator agent for Playwright (Python, sync API).

Usage (locator-map mode -- recommended):

    healer = Healer("locators.yaml")
    button = healer.locate(page, "login_button", selector="#login-btn")  # first run: learns
    button = healer.locate(page, "login_button")                         # later runs: resolves
    button.click()

If the stored selector fails to attach within `timeout`, the healer snapshots
candidate elements on the page, scores them against the last-known-good
fingerprint, and -- if a confident match is found -- rewrites the locator
store with the new selector and returns a working Locator for the *current*
page. No LLM/network calls are involved; healing is pure DOM heuristics.

Inline mode is also available for scripts that don't want a locator map:

    el = healer.locate_inline(page, "#login-btn")

On healing, this rewrites the literal selector string at the call site in the
test source file.
"""

from __future__ import annotations

import inspect
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from . import fingerprint as fp
from .exceptions import HealingFailedError, LocatorNotFoundError
from .patcher import patch_source_selector
from .scoring import similarity
from .selector_builder import build_selector
from .store import HealEvent, LocatorSpec, LocatorStore


class Healer:
    def __init__(
        self,
        store_path: str | Path = "locators.yaml",
        *,
        confidence_threshold: float = 0.6,
        timeout: float = 5000,
        auto_patch_source: bool = True,
    ):
        self.store = LocatorStore(store_path)
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        self.auto_patch_source = auto_patch_source

    # -- public API ---------------------------------------------------

    def locate(
        self,
        page: Page,
        name: str,
        *,
        selector: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Locator:
        """Resolve a named locator, healing it against the current page if it's broken.

        If `name` isn't in the store yet, `selector` is required and is used to
        learn (and persist) an initial fingerprint.
        """
        timeout = timeout if timeout is not None else self.timeout
        spec = self.store.get(name)

        if spec is None:
            if selector is None:
                raise LocatorNotFoundError(
                    f"No locator registered for '{name}'; pass selector= to learn it"
                )
            spec = self._learn(page, name, selector)

        locator = page.locator(spec.selector)
        try:
            locator.wait_for(state="attached", timeout=timeout)
            return locator
        except PlaywrightTimeoutError:
            return self._heal(page, name, spec, timeout)

    def locate_inline(
        self,
        page: Page,
        selector: str,
        *,
        name: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Locator:
        """Like `locate`, but the selector lives in the caller's source rather
        than being looked up by name. Learns/heals under a name derived from
        the selector, and patches the call site's source line on healing.
        """
        caller = inspect.stack()[1]
        name = name or f"inline::{selector}"
        timeout = timeout if timeout is not None else self.timeout

        spec = self.store.get(name)
        if spec is None:
            spec = self._learn(page, name, selector, source_file=caller.filename, source_line=caller.lineno)

        locator = page.locator(spec.selector)
        try:
            locator.wait_for(state="attached", timeout=timeout)
            return locator
        except PlaywrightTimeoutError:
            return self._heal(page, name, spec, timeout)

    # -- internals ------------------------------------------------------

    def _learn(
        self,
        page: Page,
        name: str,
        selector: str,
        *,
        source_file: Optional[str] = None,
        source_line: Optional[int] = None,
    ) -> LocatorSpec:
        element_fp = page.eval_on_selector(selector, fp.SINGLE_ELEMENT_JS)
        spec = LocatorSpec(
            name=name,
            selector=selector,
            fingerprint=element_fp,
            source_file=source_file,
            source_line=source_line,
        )
        self.store.put(spec)
        return spec

    def _collect_candidates(self, page: Page, tag: str) -> list[dict]:
        return page.evaluate(fp.CANDIDATES_JS, tag)

    def _heal(self, page: Page, name: str, spec: LocatorSpec, timeout: float) -> Locator:
        candidates = self._collect_candidates(page, spec.fingerprint.get("tag", ""))
        scored = sorted(
            ((similarity(spec.fingerprint, c), c) for c in candidates),
            key=lambda pair: pair[0],
            reverse=True,
        )

        best_score, best_fp = scored[0] if scored else (0.0, None)
        if best_fp is None or best_score < self.confidence_threshold:
            raise HealingFailedError(name, spec.selector, best_score, self.confidence_threshold)

        new_selector = build_selector(best_fp)
        old_selector = spec.selector

        self.store.update_selector(name, new_selector, best_fp)
        self.store.log_heal_event(
            HealEvent(name=name, old_selector=old_selector, new_selector=new_selector, score=best_score)
        )

        if self.auto_patch_source and spec.source_file:
            patch_source_selector(spec.source_file, spec.source_line, old_selector, new_selector)

        locator = page.locator(new_selector)
        locator.wait_for(state="attached", timeout=timeout)
        return locator
