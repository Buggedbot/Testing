from self_healing_locator import copilot_assist
from self_healing_locator.cli import main
from self_healing_locator.store import HealEvent, LocatorSpec, LocatorStore, PendingHeal


def test_init_creates_store(tmp_path, capsys):
    path = tmp_path / "locators.yaml"
    main(["init", str(path)])
    assert path.exists()
    assert "Created" in capsys.readouterr().out


def test_list_shows_registered_locators(tmp_path, capsys):
    path = tmp_path / "locators.yaml"
    store = LocatorStore(path)
    store.put(LocatorSpec(name="save_btn", selector="#save", fingerprint={}))

    main(["list", str(path)])
    out = capsys.readouterr().out
    assert "save_btn" in out
    assert "#save" in out


def test_report_shows_heal_events(tmp_path, capsys):
    path = tmp_path / "locators.yaml"
    store = LocatorStore(path)
    store.put(LocatorSpec(name="save_btn", selector="#save", fingerprint={}))
    store.log_heal_event(HealEvent(name="save_btn", old_selector="#save", new_selector="#save2", score=0.8))

    main(["report", str(path)])
    out = capsys.readouterr().out
    assert "save_btn" in out
    assert "#save -> #save2" in out


def test_review_and_approve_flow(tmp_path, capsys):
    path = tmp_path / "locators.yaml"
    store = LocatorStore(path)
    store.put(LocatorSpec(name="cancel_btn", selector="#cancel", fingerprint={}))
    store.add_pending(
        PendingHeal(
            name="cancel_btn",
            old_selector="#cancel",
            new_selector="#discard",
            frame_selector=None,
            fingerprint={"text": "Discard Changes"},
            score=0.6,
            reason="matched risk deny-list",
        )
    )

    main(["review", str(path)])
    assert "cancel_btn" in capsys.readouterr().out

    main(["approve", "cancel_btn", str(path)])
    assert "Approved" in capsys.readouterr().out

    reloaded = LocatorStore(path)
    assert reloaded.get("cancel_btn").selector == "#discard"
    assert reloaded.list_pending() == []


def test_review_and_reject_flow(tmp_path, capsys):
    path = tmp_path / "locators.yaml"
    store = LocatorStore(path)
    store.put(LocatorSpec(name="cancel_btn", selector="#cancel", fingerprint={}))
    store.add_pending(
        PendingHeal(
            name="cancel_btn",
            old_selector="#cancel",
            new_selector="#discard",
            frame_selector=None,
            fingerprint={"text": "Discard Changes"},
            score=0.6,
            reason="matched risk deny-list",
        )
    )

    main(["reject", "cancel_btn", str(path)])
    assert "Rejected" in capsys.readouterr().out

    reloaded = LocatorStore(path)
    assert reloaded.get("cancel_btn").selector == "#cancel"  # unchanged
    assert reloaded.list_pending() == []


def test_assist_lists_pending_copilot_chat_prompts(tmp_path, capsys):
    path = tmp_path / "locators.yaml"
    copilot_assist.record_assist(
        path, "login_button", "#login-btn", {"tag": "button", "text": "Log In"}, [], reason="no confident match"
    )

    main(["assist", str(path)])
    out = capsys.readouterr().out
    assert "login_button" in out
    assert "assist.md" in out


def test_assist_apply_sets_selector_and_clears_entry(tmp_path, capsys):
    path = tmp_path / "locators.yaml"
    store = LocatorStore(path)
    store.put(LocatorSpec(name="login_button", selector="#login-btn", fingerprint={"tag": "button"}))
    copilot_assist.record_assist(
        path, "login_button", "#login-btn", {"tag": "button", "text": "Log In"}, [], reason="no confident match"
    )

    main(["assist-apply", "login_button", "#new-login-btn", str(path)])
    out = capsys.readouterr().out
    assert "Applied" in out
    assert "source=copilot_chat" in out

    reloaded = LocatorStore(path)
    assert reloaded.get("login_button").selector == "#new-login-btn"
    assert copilot_assist.pending_assist_names(path) == []

    events = reloaded.heal_events()
    assert events[-1]["source"] == "copilot_chat"
