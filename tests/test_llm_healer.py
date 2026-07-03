import json
from unittest.mock import patch

from self_healing_locator.llm_healer import (
    CopilotCliBackend,
    build_prompt,
    parse_response,
    select_candidate,
)


def _fp(**overrides):
    base = {
        "tag": "button",
        "id": "act-3392",
        "classes": ["mui-button"],
        "text": "Log In",
        "attributes": {"type": "submit"},
        "dom_index": 1,
        "parent": {"tag": "form", "id": None, "classes": []},
    }
    base.update(overrides)
    return base


def test_build_prompt_includes_target_and_indexed_candidates():
    prompt = build_prompt("login_button", "#login-btn", _fp(text="Log In"), [_fp(text="Log In"), _fp(text="Cancel")])
    payload = json.loads(prompt[prompt.index("{"):])
    assert payload["locator_name"] == "login_button"
    assert payload["old_selector"] == "#login-btn"
    assert payload["target_element"]["text"] == "Log In"
    assert [c["index"] for c in payload["candidates"]] == [0, 1]
    assert payload["candidates"][1]["text"] == "Cancel"


def test_build_prompt_includes_failed_selectors_when_present():
    prompt = build_prompt(
        "login_button", "#login-btn", _fp(), [_fp()], failed_selectors=["#act-1", "#act-2"]
    )
    payload = json.loads(prompt[prompt.index("{"):])
    assert payload["previously_tried_and_failed"] == ["#act-1", "#act-2"]
    assert "do not suggest" in prompt.lower()


def test_build_prompt_omits_failed_selectors_key_when_empty():
    prompt = build_prompt("login_button", "#login-btn", _fp(), [_fp()])
    payload = json.loads(prompt[prompt.index("{"):])
    assert "previously_tried_and_failed" not in payload


def test_parse_response_valid():
    parsed = parse_response('{"candidate_index": 1, "confidence": 0.8, "reasoning": "text match"}', 3)
    assert parsed == {"candidate_index": 1, "confidence": 0.8, "reasoning": "text match"}


def test_parse_response_allows_negative_one_no_match():
    parsed = parse_response('{"candidate_index": -1, "confidence": 0.1, "reasoning": "nothing close"}', 3)
    assert parsed["candidate_index"] == -1


def test_parse_response_rejects_out_of_range_index():
    assert parse_response('{"candidate_index": 5, "confidence": 0.9, "reasoning": "x"}', 3) is None


def test_parse_response_rejects_bad_json():
    assert parse_response("not json", 3) is None


def test_parse_response_rejects_confidence_out_of_bounds():
    assert parse_response('{"candidate_index": 0, "confidence": 1.5, "reasoning": "x"}', 3) is None


def test_select_candidate_with_fake_backend():
    backend = lambda prompt: json.dumps({"candidate_index": 0, "confidence": 0.9, "reasoning": "text match"})
    result = select_candidate(
        backend,
        name="login_button",
        old_selector="#login-btn",
        target_fp=_fp(),
        candidates=[_fp()],
        min_confidence=0.5,
    )
    assert result == (0, 0.9, "text match")


def test_select_candidate_returns_none_when_backend_returns_nothing():
    result = select_candidate(
        lambda prompt: None,
        name="login_button",
        old_selector="#login-btn",
        target_fp=_fp(),
        candidates=[_fp()],
        min_confidence=0.5,
    )
    assert result is None


def test_select_candidate_returns_none_below_min_confidence():
    backend = lambda prompt: json.dumps({"candidate_index": 0, "confidence": 0.3, "reasoning": "weak"})
    result = select_candidate(
        backend,
        name="login_button",
        old_selector="#login-btn",
        target_fp=_fp(),
        candidates=[_fp()],
        min_confidence=0.5,
    )
    assert result is None


def test_select_candidate_returns_none_with_no_candidates():
    result = select_candidate(
        lambda prompt: "{}",
        name="login_button",
        old_selector="#login-btn",
        target_fp=_fp(),
        candidates=[],
        min_confidence=0.5,
    )
    assert result is None


def test_copilot_cli_backend_returns_none_when_gh_missing():
    backend = CopilotCliBackend(command="definitely-not-a-real-binary-xyz")
    assert backend("some prompt") is None


def test_copilot_cli_backend_extracts_json_from_noisy_output():
    backend = CopilotCliBackend()

    class FakeResult:
        stdout = (
            "Welcome to GitHub Copilot in the CLI!\n"
            'Here is a suggestion: {"candidate_index": 2, "confidence": 0.75, "reasoning": "close enough"}\n'
        )

    with patch("self_healing_locator.llm_healer.shutil.which", return_value="/usr/bin/gh"):
        with patch("self_healing_locator.llm_healer.subprocess.run", return_value=FakeResult()):
            text = backend("prompt")

    assert text is not None
    assert json.loads(text) == {"candidate_index": 2, "confidence": 0.75, "reasoning": "close enough"}


def test_copilot_cli_backend_returns_none_on_timeout():
    import subprocess as sp

    backend = CopilotCliBackend()
    with patch("self_healing_locator.llm_healer.shutil.which", return_value="/usr/bin/gh"):
        with patch(
            "self_healing_locator.llm_healer.subprocess.run",
            side_effect=sp.TimeoutExpired(cmd="gh", timeout=30),
        ):
            assert backend("prompt") is None
