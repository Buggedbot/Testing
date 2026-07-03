from self_healing_locator import copilot_assist


def _fp(text="Log In"):
    return {"tag": "button", "id": "act-1", "classes": [], "text": text, "attributes": {}}


def test_render_entry_includes_prompt_and_reason():
    entry = copilot_assist.render_entry("login_button", "#login-btn", _fp(), [_fp()], reason="score too low")
    assert "## login_button" in entry
    assert "#login-btn" in entry
    assert "score too low" in entry
    assert "```text" in entry


def test_record_and_clear_assist_writes_and_removes_files(tmp_path):
    store_path = tmp_path / "locators.yaml"
    json_path, md_path = copilot_assist.assist_paths(store_path)

    copilot_assist.record_assist(store_path, "login_button", "#login-btn", _fp(), [_fp()], reason="no match")
    assert json_path.exists()
    assert md_path.exists()
    assert "login_button" in copilot_assist.pending_assist_names(store_path)
    assert "login_button" in md_path.read_text()

    copilot_assist.clear_assist(store_path, "login_button")
    assert not json_path.exists()
    assert not md_path.exists()
    assert copilot_assist.pending_assist_names(store_path) == []


def test_record_assist_preserves_other_entries(tmp_path):
    store_path = tmp_path / "locators.yaml"

    copilot_assist.record_assist(store_path, "a", "#a", _fp(), [_fp()], reason="r1")
    copilot_assist.record_assist(store_path, "b", "#b", _fp(), [_fp()], reason="r2")

    assert copilot_assist.pending_assist_names(store_path) == ["a", "b"]

    copilot_assist.clear_assist(store_path, "a")
    assert copilot_assist.pending_assist_names(store_path) == ["b"]


def test_clear_assist_on_missing_entry_is_a_no_op(tmp_path):
    store_path = tmp_path / "locators.yaml"
    copilot_assist.clear_assist(store_path, "nothing-here")  # must not raise
    assert copilot_assist.pending_assist_names(store_path) == []
