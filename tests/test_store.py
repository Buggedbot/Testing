from self_healing_locator.store import HealEvent, LocatorSpec, LocatorStore, PendingHeal


def test_put_get_roundtrip(tmp_path):
    store = LocatorStore(tmp_path / "locators.yaml")
    spec = LocatorSpec(name="login_button", selector="#login-btn", fingerprint={"tag": "button"})
    store.put(spec)

    reloaded = LocatorStore(tmp_path / "locators.yaml")
    got = reloaded.get("login_button")
    assert got is not None
    assert got.selector == "#login-btn"
    assert got.fingerprint == {"tag": "button"}


def test_update_selector_bumps_heal_count(tmp_path):
    store = LocatorStore(tmp_path / "locators.yaml")
    store.put(LocatorSpec(name="btn", selector="#old", fingerprint={}))

    store.update_selector("btn", "#new", {"tag": "button"})

    spec = store.get("btn")
    assert spec.selector == "#new"
    assert spec.heal_count == 1


def test_heal_events_persist_across_instances(tmp_path):
    path = tmp_path / "locators.yaml"
    store = LocatorStore(path)
    store.put(LocatorSpec(name="btn", selector="#old", fingerprint={}))
    store.log_heal_event(HealEvent(name="btn", old_selector="#old", new_selector="#new", score=0.8))

    reloaded = LocatorStore(path)
    events = reloaded.heal_events()
    assert len(events) == 1
    assert events[0]["name"] == "btn"
    assert events[0]["new_selector"] == "#new"


def test_missing_store_file_starts_empty(tmp_path):
    store = LocatorStore(tmp_path / "does_not_exist.yaml")
    assert store.all() == {}
    assert store.heal_events() == []


def test_frame_selector_roundtrips(tmp_path):
    store = LocatorStore(tmp_path / "locators.yaml")
    store.put(LocatorSpec(name="note_btn", selector="#save", fingerprint={}, frame_selector='iframe[title="Notes"]'))

    reloaded = LocatorStore(tmp_path / "locators.yaml")
    assert reloaded.get("note_btn").frame_selector == 'iframe[title="Notes"]'


def test_pending_add_list_pop(tmp_path):
    store = LocatorStore(tmp_path / "locators.yaml")
    pending = PendingHeal(
        name="cancel_button",
        old_selector="#cancel-btn",
        new_selector="#act-5511",
        frame_selector=None,
        fingerprint={"text": "Discard Changes"},
        score=0.7,
        reason="matched risk deny-list",
    )
    store.add_pending(pending)

    listed = store.list_pending()
    assert len(listed) == 1
    assert listed[0].name == "cancel_button"

    popped = store.pop_pending("cancel_button")
    assert popped.new_selector == "#act-5511"
    assert store.list_pending() == []


def test_add_pending_replaces_existing_entry_for_same_name(tmp_path):
    store = LocatorStore(tmp_path / "locators.yaml")
    first = PendingHeal(
        name="btn", old_selector="#a", new_selector="#b", frame_selector=None,
        fingerprint={}, score=0.6, reason="r1",
    )
    second = PendingHeal(
        name="btn", old_selector="#a", new_selector="#c", frame_selector=None,
        fingerprint={}, score=0.8, reason="r2",
    )
    store.add_pending(first)
    store.add_pending(second)

    listed = store.list_pending()
    assert len(listed) == 1
    assert listed[0].new_selector == "#c"


def test_pop_pending_missing_returns_none(tmp_path):
    store = LocatorStore(tmp_path / "locators.yaml")
    assert store.pop_pending("nope") is None


def test_record_failed_attempt_appends_and_dedupes(tmp_path):
    store = LocatorStore(tmp_path / "locators.yaml")
    store.put(LocatorSpec(name="btn", selector="#old", fingerprint={}))

    store.record_failed_attempt("btn", "#tried-1")
    store.record_failed_attempt("btn", "#tried-2")
    store.record_failed_attempt("btn", "#tried-1")  # duplicate, no-op

    assert store.get("btn").failed_selectors == ["#tried-1", "#tried-2"]


def test_failed_selectors_persist_across_instances(tmp_path):
    path = tmp_path / "locators.yaml"
    store = LocatorStore(path)
    store.put(LocatorSpec(name="btn", selector="#old", fingerprint={}))
    store.record_failed_attempt("btn", "#tried-1")

    reloaded = LocatorStore(path)
    assert reloaded.get("btn").failed_selectors == ["#tried-1"]


def test_clear_failed_attempts(tmp_path):
    store = LocatorStore(tmp_path / "locators.yaml")
    store.put(LocatorSpec(name="btn", selector="#old", fingerprint={}))
    store.record_failed_attempt("btn", "#tried-1")

    store.clear_failed_attempts("btn")
    assert store.get("btn").failed_selectors == []
