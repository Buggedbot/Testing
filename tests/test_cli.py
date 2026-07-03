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
