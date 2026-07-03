"""Persistent locator map: friendly element name -> selector + fingerprint,
plus an append-only healing report log.

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


class LocatorStore:
    """YAML-backed map of name -> LocatorSpec, loaded/saved lazily."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.report_path = self.path.with_name(self.path.stem + ".report.json")
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

    def update_selector(self, name: str, selector: str, fingerprint: dict[str, Any]) -> LocatorSpec:
        spec = self._specs[name]
        spec.selector = selector
        spec.fingerprint = fingerprint
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
