"""File-based hand-off for AI assistance that can't be called programmatically.

`llm_healer.py`'s pluggable backends (`"copilot_cli"`, `"anthropic"`, custom
callables) all assume *something* is invocable from Python -- a CLI binary or
an API. That's not true for GitHub Copilot's IDE integration (VS Code /
JetBrains chat): there is no headless entry point a Playwright test process
can call. For that environment, the realistic "self-healing via GenAI" story
is a human in the loop, not a hidden API call.

When healing fails outright (`Healer(copilot_assist=True)`), instead of just
raising, the healer writes the same target/candidate data `llm_healer` would
have sent to an API into a Markdown file next to the locator store. A
developer opens it, pastes the prompt into Copilot Chat, reads the answer,
and applies the suggested selector with `shl assist-apply`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .llm_healer import build_prompt

_HEADER = (
    "# Self-healing: Copilot Chat assist\n\n"
    "Generated because automated healing couldn't confidently resolve these "
    "locators on its own. For each one:\n\n"
    "1. Paste the prompt block into GitHub Copilot Chat (or any assistant with "
    "chat access).\n"
    "2. Read its answer and decide on a CSS selector for the matching element.\n"
    "3. Run `shl assist-apply <name> <selector> locators.yaml` "
    "(add `--frame <iframe-selector>` if the element is inside an iframe).\n\n"
    "This file regenerates on every run -- entries clear automatically once a "
    "locator heals successfully (by any means) or is applied via `assist-apply`.\n"
)


def render_entry(
    name: str,
    old_selector: str,
    target_fp: dict[str, Any],
    candidates: list[dict[str, Any]],
    reason: str,
    failed_selectors: Optional[list[str]] = None,
) -> str:
    prompt = build_prompt(name, old_selector, target_fp, candidates, failed_selectors=failed_selectors)
    lines = [
        f"## {name}",
        "",
        f"- Old selector: `{old_selector}`",
        f"- Why it needs help: {reason}",
    ]
    if failed_selectors:
        tried = ", ".join(f"`{s}`" for s in failed_selectors)
        lines.append(f"- Already tried and still broken (don't suggest these again): {tried}")
    lines += ["", "```text", prompt, "```", ""]
    return "\n".join(lines)


def assist_paths(store_path: str | Path) -> tuple[Path, Path]:
    """Returns (json_sidecar_path, markdown_path) for a given locator store path."""
    store_path = Path(store_path)
    return (
        store_path.with_name(store_path.stem + ".assist.json"),
        store_path.with_name(store_path.stem + ".assist.md"),
    )


def pending_assist_names(store_path: str | Path) -> list[str]:
    json_path, _ = assist_paths(store_path)
    return sorted(_load(json_path))


def _load(json_path: Path) -> dict[str, str]:
    if not json_path.exists():
        return {}
    return json.loads(json_path.read_text())


def _save(json_path: Path, md_path: Path, sections: dict[str, str]) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    if not sections:
        json_path.unlink(missing_ok=True)
        md_path.unlink(missing_ok=True)
        return
    json_path.write_text(json.dumps(sections, indent=2))
    body = "\n".join(sections[name] for name in sorted(sections))
    md_path.write_text(_HEADER + "\n" + body)


def record_assist(
    store_path: str | Path,
    name: str,
    old_selector: str,
    target_fp: dict[str, Any],
    candidates: list[dict[str, Any]],
    reason: str,
    failed_selectors: Optional[list[str]] = None,
) -> None:
    json_path, md_path = assist_paths(store_path)
    sections = _load(json_path)
    sections[name] = render_entry(name, old_selector, target_fp, candidates, reason, failed_selectors=failed_selectors)
    _save(json_path, md_path, sections)


def clear_assist(store_path: str | Path, name: str) -> None:
    json_path, md_path = assist_paths(store_path)
    sections = _load(json_path)
    if name in sections:
        del sections[name]
        _save(json_path, md_path, sections)
