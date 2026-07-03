from self_healing_locator.selector_builder import build_selector, looks_dynamic


def test_prefers_data_testid():
    fp = {"tag": "button", "id": "act-3392", "attributes": {"data-testid": "login-submit"}}
    assert build_selector(fp) == '[data-testid="login-submit"]'


def test_prefers_stable_id_over_name():
    fp = {"tag": "input", "id": "username", "attributes": {"name": "username"}}
    assert build_selector(fp) == "#username"


def test_skips_dynamic_looking_id():
    fp = {"tag": "button", "id": "act-3392", "attributes": {}, "classes": [], "dom_index": 1, "parent": {"tag": "form"}}
    selector = build_selector(fp)
    assert "act-3392" not in selector


def test_falls_back_to_name_attribute():
    fp = {"tag": "input", "id": None, "attributes": {"name": "password"}}
    assert build_selector(fp) == 'input[name="password"]'


def test_falls_back_to_structural_selector():
    fp = {
        "tag": "button",
        "id": None,
        "attributes": {"type": "submit"},
        "classes": [],
        "dom_index": 1,
        "parent": {"tag": "form", "id": None},
    }
    selector = build_selector(fp)
    assert selector == 'form > button[type="submit"]:nth-of-type(2)'


def test_looks_dynamic():
    assert looks_dynamic("field-123456")
    assert looks_dynamic("a1b2c3d4-e5f6-47a8-9012-abcdef123456")
    assert not looks_dynamic("login-btn")
