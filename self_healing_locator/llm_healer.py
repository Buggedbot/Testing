"""Optional GenAI-assisted healing tier.

When heuristic DOM-similarity scoring (scoring.py) can't confidently
re-identify a broken locator -- typically because a redesign changed enough
text/attributes/position that no candidate clears the confidence threshold --
this module asks an LLM to pick the best match from the same candidate pool
the heuristic engine already scored.

This tier is opt-in (`Healer(..., llm_fallback=True)`) and never bypasses the
risk gate in healer.py: an LLM-selected candidate that matches the risk
deny-list is still withheld for human review, exactly like a heuristic one.

A "backend" is any callable `(prompt: str) -> str | None` -- return the raw
response text, or None if the call failed/timed out/produced nothing usable.
`select_candidate()` doesn't care which backend it's talking to, so plugging
in a different LLM is a matter of writing a new backend, not touching the
matching logic. Two backends are provided:

- `CopilotCliBackend` -- shells out to `gh copilot suggest`. This is a
  best-effort scrape: that command is built for suggesting shell/git/gh
  commands, not answering arbitrary structured-JSON questions, so treat a
  `None` result (parse failure, non-zero exit, `gh` not installed) as
  routine, not exceptional -- healing just falls back to heuristic-only.
- `AnthropicBackend` -- calls Claude via the official `anthropic` SDK, for
  environments that do have real LLM API access.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any, Callable, Optional

MODEL_DEFAULT = "claude-opus-4-8"

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_index": {
            "type": "integer",
            "description": "0-based index into the candidates list, or -1 if none plausibly match.",
        },
        "confidence": {
            "type": "number",
            "description": "0.0-1.0 confidence that candidate_index is the same UI element as the target.",
        },
        "reasoning": {"type": "string"},
    },
    "required": ["candidate_index", "confidence", "reasoning"],
    "additionalProperties": False,
}

Backend = Callable[[str], Optional[str]]


def _describe(fp: dict[str, Any]) -> dict[str, Any]:
    return {
        "tag": fp.get("tag"),
        "id": fp.get("id"),
        "classes": fp.get("classes"),
        "text": fp.get("text"),
        "attributes": fp.get("attributes"),
        "dom_index": fp.get("dom_index"),
        "parent": fp.get("parent"),
    }


def build_prompt(
    name: str, old_selector: str, target_fp: dict[str, Any], candidates: list[dict[str, Any]]
) -> str:
    payload = {
        "locator_name": name,
        "old_selector": old_selector,
        "target_element": _describe(target_fp),
        "candidates": [dict(index=i, **_describe(fp)) for i, fp in enumerate(candidates)],
    }
    return (
        "A UI test locator broke because the page changed. `target_element` describes "
        "the element the last time the locator worked. `candidates` are same-tag elements "
        "found on the current page. Pick the candidate that is most likely the same UI "
        "element after a redesign, weighing visible text and semantic attributes (name, "
        "type, role, aria-label) more heavily than id/class (which are expected to have "
        "changed), and DOM position as a tie-breaker. If nothing plausibly matches, return "
        "-1. Respond with ONLY a single-line JSON object containing exactly three keys: "
        "candidate_index (integer), confidence (a number from 0 to 1), and reasoning (a "
        "short string). No markdown fences, no shell command, no other text.\n\n"
        + json.dumps(payload, indent=2)
    )


def parse_response(text: str, num_candidates: int) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    idx = data.get("candidate_index")
    confidence = data.get("confidence")
    if not isinstance(idx, int) or isinstance(idx, bool):
        return None
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return None
    if idx != -1 and not (0 <= idx < num_candidates):
        return None
    if not (0.0 <= confidence <= 1.0):
        return None
    return {"candidate_index": idx, "confidence": float(confidence), "reasoning": data.get("reasoning", "")}


def select_candidate(
    backend: Backend,
    *,
    name: str,
    old_selector: str,
    target_fp: dict[str, Any],
    candidates: list[dict[str, Any]],
    min_confidence: float,
) -> Optional[tuple[int, float, str]]:
    """Ask the backend to pick a candidate. Returns (index, confidence,
    reasoning), or None if the call failed, found no match, or fell below
    `min_confidence`.
    """
    if not candidates:
        return None

    prompt = build_prompt(name, old_selector, target_fp, candidates)
    text = backend(prompt)
    if not text:
        return None

    parsed = parse_response(text, len(candidates))
    if parsed is None or parsed["candidate_index"] < 0:
        return None
    if parsed["confidence"] < min_confidence:
        return None
    return parsed["candidate_index"], parsed["confidence"], parsed["reasoning"]


# -- backends -------------------------------------------------------------

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class CopilotCliBackend:
    """Best-effort backend on top of `gh copilot suggest` (the `gh-copilot`
    CLI extension). Not an officially supported general-purpose completion
    API -- it's a shell-command assistant -- so this asks it to emit a JSON
    object and scrapes the first `{...}` blob out of whatever it prints.
    Returns None (never raises) on any failure: missing `gh`/extension,
    non-zero exit, timeout, or no JSON-looking substring in the output.
    """

    def __init__(self, command: str = "gh", timeout: float = 30.0):
        self.command = command
        self.timeout = timeout

    def __call__(self, prompt: str) -> Optional[str]:
        if shutil.which(self.command) is None:
            return None
        try:
            result = subprocess.run(
                [self.command, "copilot", "suggest", "-t", "shell", prompt],
                input="\n",  # decline any "run this command?" confirmation prompt
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

        match = _JSON_OBJECT_RE.search(result.stdout)
        return match.group(0) if match else None


class AnthropicBackend:
    """Calls Claude via the official `anthropic` SDK. Requires `pip install
    anthropic` and API credentials (`ANTHROPIC_API_KEY` or an `ant auth
    login` profile) -- only usable where the environment actually has LLM
    API access; see `CopilotCliBackend` for environments that don't.
    """

    def __init__(self, client: Any = None, model: str = MODEL_DEFAULT):
        self._client = client
        self.model = model

    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def __call__(self, prompt: str) -> Optional[str]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            thinking={"type": "adaptive"},
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        if getattr(response, "stop_reason", None) == "refusal":
            return None
        return next((block.text for block in response.content if getattr(block, "type", None) == "text"), None)
