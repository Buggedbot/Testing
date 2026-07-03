"""Self-healing locator agent for Playwright (Python, sync API).

Usage (locator-map mode -- recommended):

    healer = Healer("locators.yaml")
    button = healer.locate(page, "login_button", selector="#login-btn")  # first run: learns
    button = healer.locate(page, "login_button")                         # later runs: resolves
    button.click()

If the stored selector fails to attach within `timeout`, the healer scans
every frame on the page (main document, open shadow roots within it, and
same- or cross-origin iframes) for elements of the same tag, scores each
against the last-known-good fingerprint, and -- if a confident match is
found -- rewrites the locator store with the new selector (and, if the match
lives inside an iframe, the selector for that iframe too) and returns a
working Locator for the *current* page.

If the best match looks destructive (matches the risk deny-list -- "delete",
"remove", "archive", ...), it is **not** auto-applied: it's queued to
`locators.pending.json` and `HealingRequiresReviewError` is raised so a wrong
guess can never auto-click something like "Delete" on a client's live CRM.
Run `shl review` / `shl approve` to inspect and apply it.

By default, healing is pure DOM heuristics -- no LLM/network calls. Pass
`llm_fallback=True` to add an opt-in GenAI tier: only when heuristic scoring
can't clear `confidence_threshold` on its own, the same scored candidates are
handed to an LLM backend to pick from. `llm_backend` selects which one:

- `"copilot_cli"` (default) -- shells out to `gh copilot suggest`. Best-effort:
  that command is a shell-command assistant, not a general JSON-completion
  API, so this scrapes a JSON object out of its output and simply finds
  nothing usable (falls back to heuristic-only) more often than a real
  completion API would. Use this where the only AI tooling available is a
  GitHub Copilot seat and `gh` CLI -- no separate LLM API key needed.
- `"anthropic"` -- calls Claude via the `anthropic` SDK, for environments
  that do have real LLM API access. Requires `pip install anthropic` and
  credentials.
- any callable `(prompt: str) -> str | None` -- for a custom backend or a
  test double.

An LLM-selected candidate still goes through the same risk gate as a
heuristic one before it's ever auto-applied -- the safety guarantee doesn't
change based on which tier found the match, and a backend that can't answer
just means healing falls through to `HealingFailedError` like any other
low-confidence case.

If the only AI tooling available is GitHub Copilot's IDE integration (VS
Code / JetBrains chat), there's no headless entry point at all -- pass
`copilot_assist=True` instead. On a `HealingFailedError`, the healer writes
the target/candidate data to `<store>.assist.md` next to the locator store: a
ready-to-paste Copilot Chat prompt per broken locator. A developer runs it
through chat by hand and applies the answer with `shl assist-apply`.

For multi-client setups, pass `client_id=` instead of `store_path=` to keep
each client's locator store, heal report, and pending queue isolated under
`<base_dir>/<client_id>/`.

Inline mode is also available for scripts that don't want a locator map:

    el = healer.locate_inline(page, "#login-btn")

On healing, this rewrites the literal selector string at the call site in the
test source file.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Iterable, Optional

from playwright.sync_api import Frame, Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from . import copilot_assist, fingerprint as fp
from . import llm_healer
from .exceptions import HealingFailedError, HealingRequiresReviewError, LocatorNotFoundError
from .patcher import patch_source_selector
from .risk import DEFAULT_RISK_KEYWORDS, is_risky
from .scoring import similarity
from .selector_builder import build_frame_selector, build_selector
from .store import HealEvent, LocatorSpec, LocatorStore, PendingHeal


class Healer:
    def __init__(
        self,
        store_path: str | Path | None = None,
        *,
        client_id: Optional[str] = None,
        base_dir: str | Path = "locators",
        confidence_threshold: float = 0.6,
        timeout: float = 5000,
        auto_patch_source: bool = True,
        require_review_for_risky: bool = True,
        risk_keywords: Iterable[str] = DEFAULT_RISK_KEYWORDS,
        llm_fallback: bool = False,
        llm_backend: Any = "copilot_cli",
        llm_model: str = llm_healer.MODEL_DEFAULT,
        llm_min_confidence: float = 0.6,
        llm_max_candidates: int = 15,
        copilot_assist: bool = False,
    ):
        if client_id is not None:
            if store_path is not None:
                raise ValueError("pass either store_path or client_id, not both")
            store_path = Path(base_dir) / client_id / "locators.yaml"
        elif store_path is None:
            store_path = "locators.yaml"

        self.client_id = client_id
        self.store = LocatorStore(store_path)
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        self.auto_patch_source = auto_patch_source
        self.require_review_for_risky = require_review_for_risky
        self.risk_keywords = list(risk_keywords)
        self.llm_fallback = llm_fallback
        self.llm_backend = llm_backend
        self.llm_model = llm_model
        self.llm_min_confidence = llm_min_confidence
        self.llm_max_candidates = llm_max_candidates
        self.copilot_assist = copilot_assist

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

        locator = self._resolve_locator(page, spec)
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

        locator = self._resolve_locator(page, spec)
        try:
            locator.wait_for(state="attached", timeout=timeout)
            return locator
        except PlaywrightTimeoutError:
            return self._heal(page, name, spec, timeout)

    # -- internals ------------------------------------------------------

    def _resolve_locator(self, page: Page, spec: LocatorSpec) -> Locator:
        if spec.frame_selector:
            return page.frame_locator(spec.frame_selector).locator(spec.selector)
        return page.locator(spec.selector)

    def _frame_selector_for(self, frame: Frame) -> Optional[str]:
        try:
            handle = frame.frame_element()
            frame_fp = handle.evaluate(fp.ELEMENT_HANDLE_JS)
            return build_frame_selector(frame_fp)
        except Exception:
            return None

    def _find_frame_for_selector(self, page: Page, selector: str) -> tuple[Frame | Page, Optional[str]]:
        if page.locator(selector).count() > 0:
            return page.main_frame, None
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                if frame.locator(selector).count() == 0:
                    continue
            except Exception:
                continue
            frame_selector = self._frame_selector_for(frame)
            if frame_selector:
                return frame, frame_selector
        raise LocatorNotFoundError(
            f"Selector {selector!r} not found in the main frame or any of "
            f"{max(len(page.frames) - 1, 0)} iframe(s)"
        )

    def _learn(
        self,
        page: Page,
        name: str,
        selector: str,
        *,
        source_file: Optional[str] = None,
        source_line: Optional[int] = None,
    ) -> LocatorSpec:
        owner_frame, frame_selector = self._find_frame_for_selector(page, selector)
        element_fp = owner_frame.eval_on_selector(selector, fp.SINGLE_ELEMENT_JS)
        spec = LocatorSpec(
            name=name,
            selector=selector,
            fingerprint=element_fp,
            frame_selector=frame_selector,
            source_file=source_file,
            source_line=source_line,
        )
        self.store.put(spec)
        return spec

    def _collect_candidates(self, page: Page, tag: str) -> list[tuple[dict, Optional[str]]]:
        results: list[tuple[dict, Optional[str]]] = []
        for frame in page.frames:
            try:
                candidates = frame.evaluate(fp.CANDIDATES_JS, tag)
            except Exception:
                continue
            if not candidates:
                continue

            frame_selector = None
            if frame != page.main_frame:
                frame_selector = self._frame_selector_for(frame)
                if frame_selector is None:
                    continue  # can't build a stable selector back to this frame; skip it

            results.extend((candidate, frame_selector) for candidate in candidates)
        return results

    def _resolve_llm_backend(self) -> llm_healer.Backend:
        if not isinstance(self.llm_backend, str):
            return self.llm_backend  # already a callable/backend instance
        if self.llm_backend == "copilot_cli":
            resolved: llm_healer.Backend = llm_healer.CopilotCliBackend()
        elif self.llm_backend == "anthropic":
            resolved = llm_healer.AnthropicBackend(model=self.llm_model)
        else:
            raise ValueError(f"Unknown llm_backend: {self.llm_backend!r}")
        self.llm_backend = resolved  # memoize
        return resolved

    def _try_llm_heal(
        self, name: str, spec: LocatorSpec, scored: list[tuple[float, dict, Optional[str]]]
    ) -> Optional[tuple[float, dict, Optional[str]]]:
        top = scored[: self.llm_max_candidates]
        if not top:
            return None
        try:
            backend = self._resolve_llm_backend()
            pick = llm_healer.select_candidate(
                backend,
                name=name,
                old_selector=spec.selector,
                target_fp=spec.fingerprint,
                candidates=[candidate_fp for _, candidate_fp, _ in top],
                min_confidence=self.llm_min_confidence,
            )
        except Exception:
            return None
        if pick is None:
            return None
        idx, confidence, _reasoning = pick
        _, candidate_fp, frame_selector = top[idx]
        return confidence, candidate_fp, frame_selector

    def _heal(self, page: Page, name: str, spec: LocatorSpec, timeout: float) -> Locator:
        candidates = self._collect_candidates(page, spec.fingerprint.get("tag", ""))
        scored = sorted(
            ((similarity(spec.fingerprint, c), c, frame_selector) for c, frame_selector in candidates),
            key=lambda triple: triple[0],
            reverse=True,
        )

        best_score, best_fp, best_frame_selector = scored[0] if scored else (0.0, None, None)
        source = "heuristic"

        if self.llm_fallback and (best_fp is None or best_score < self.confidence_threshold):
            llm_pick = self._try_llm_heal(name, spec, scored)
            if llm_pick is not None:
                best_score, best_fp, best_frame_selector = llm_pick
                source = "llm"

        if best_fp is None or best_score < self.confidence_threshold:
            if self.copilot_assist:
                copilot_assist.record_assist(
                    self.store.path,
                    name,
                    spec.selector,
                    spec.fingerprint,
                    [candidate_fp for _, candidate_fp, _ in scored[: self.llm_max_candidates]],
                    reason=(
                        f"best candidate scored {best_score:.2f}, below "
                        f"confidence_threshold {self.confidence_threshold:.2f}"
                    ),
                )
            raise HealingFailedError(name, spec.selector, best_score, self.confidence_threshold)

        new_selector = build_selector(best_fp)
        old_selector = spec.selector

        if self.copilot_assist:
            copilot_assist.clear_assist(self.store.path, name)

        if self.require_review_for_risky and is_risky(best_fp, self.risk_keywords):
            self.store.add_pending(
                PendingHeal(
                    name=name,
                    old_selector=old_selector,
                    new_selector=new_selector,
                    frame_selector=best_frame_selector,
                    fingerprint=best_fp,
                    score=best_score,
                    reason="best candidate matched the risk deny-list",
                    source=source,
                )
            )
            raise HealingRequiresReviewError(name, old_selector, new_selector, best_score)

        self.store.update_selector(name, new_selector, best_fp, frame_selector=best_frame_selector)
        self.store.log_heal_event(
            HealEvent(
                name=name, old_selector=old_selector, new_selector=new_selector, score=best_score, source=source
            )
        )

        if self.auto_patch_source and spec.source_file:
            patch_source_selector(spec.source_file, spec.source_line, old_selector, new_selector)

        healed_spec = self.store.get(name)
        locator = self._resolve_locator(page, healed_spec)
        locator.wait_for(state="attached", timeout=timeout)
        return locator
