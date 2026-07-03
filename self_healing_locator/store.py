"""Persistent locator map: friendly element name -> selector + fingerprint,
plus an append-only healing report log and a pending-review queue for heals
that looked destructive enough to require a human before they take effect.

The store is the "test script" that gets auto-patched: tests reference elements
by name (`healer.locate(page, "login_button")`), and healing rewrites this file
in place, so the next run picks up the new selector without any code change.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class LocatorSpec:
    name: str
    selector: str
    fingerprint: dict[str, Any] = field(default_factory=dict)
    # CSS selector for the <iframe> containing `selector`, or None if it lives
    # in the main frame (including inside open shadow DOM, which Playwright's
    # own CSS engine pierces automatically).
    frame_selector: Optional[str] = None
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    updated_at: float = field(default_factory=time.time)
    heal_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "LocatorSpec":
        return cls(
            name=name,
            selector=data["selector"],
            fingerprint=data.get("fingerprint") or {},
            frame_selector=data.get("frame_selector"),
            source_file=data.get("source_file"),
            source_line=data.get("source_line"),
            updated_at=data.get("updated_at", time.time()),
            heal_count=data.get("heal_count", 0),
        )


@dataclass
class HealEvent:
    name: str
    old_selector: str
    new_selector: str
    score: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PendingHeal:
    """A proposed heal that was withheld from auto-apply because the best
    candidate matched the risk deny-list (e.g. looked like a "Delete" button)."""

    name: str
    old_selector: str
    new_selector: str
    frame_selector: Optional[str]
    fingerprint: dict[str, Any]
    score: float
    reason: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PendingHeal":
        return cls(**data)


class LocatorStore:
    """YAML-backed map of name -> LocatorSpec, loaded/saved lazily."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.report_path = self.path.with_name(self.path.stem + ".report.json")
        self.pending_path = self.path.with_name(self.path.stem + ".pending.json")
        self._specs: dict[str, LocatorSpec] = {}
        if self.path.exists():
            self.load()

    def load(self) -> None:
        raw = yaml.safe_load(self.path.read_text()) or {}
        self._specs = {name: LocatorSpec.from_dict(name, data) for name, data in raw.items()}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: spec.to_dict() for name, spec in self._specs.items()}
        for spec_dict in data.values():
            spec_dict.pop("name", None)
        self.path.write_text(yaml.safe_dump(data, sort_keys=True))

    def get(self, name: str) -> Optional[LocatorSpec]:
        return self._specs.get(name)

    def all(self) -> dict[str, LocatorSpec]:
        return dict(self._specs)

    def put(self, spec: LocatorSpec) -> None:
        self._specs[spec.name] = spec
        self.save()

    def update_selector(
        self,
        name: str,
        selector: str,
        fingerprint: dict[str, Any],
        frame_selector: Optional[str] = None,
    ) -> LocatorSpec:
        spec = self._specs[name]
        spec.selector = selector
        spec.fingerprint = fingerprint
        spec.frame_selector = frame_selector
        spec.updated_at = time.time()
        spec.heal_count += 1
        self.save()
        return spec

    def log_heal_event(self, event: HealEvent) -> None:
        events = []
        if self.report_path.exists():
            events = json.loads(self.report_path.read_text())
        events.append(event.to_dict())
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(events, indent=2))

    def heal_events(self) -> list[dict[str, Any]]:
        if not self.report_path.exists():
            return []
        return json.loads(self.report_path.read_text())

    # -- pending review queue -----------------------------------------

    def _load_pending(self) -> list[dict[str, Any]]:
        if not self.pending_path.exists():
            return []
        return json.loads(self.pending_path.read_text())

    def _save_pending(self, items: list[dict[str, Any]]) -> None:
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_path.write_text(json.dumps(items, indent=2))

    def add_pending(self, pending: PendingHeal) -> None:
        items = [p for p in self._load_pending() if p["name"] != pending.name]
        items.append(pending.to_dict())
        self._save_pending(items)

    def list_pending(self) -> list[PendingHeal]:
        return [PendingHeal.from_dict(p) for p in self._load_pending()]

    def pop_pending(self, name: str) -> Optional[PendingHeal]:
        items = self._load_pending()
        remaining = [p for p in items if p["name"] != name]
        if len(remaining) == len(items):
            return None
        self._save_pending(remaining)
        return PendingHeal.from_dict(next(p for p in items if p["name"] == name))
