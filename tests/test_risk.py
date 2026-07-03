from self_healing_locator.risk import is_risky


def test_flags_text_match():
    fp = {"text": "Delete Contact", "attributes": {}}
    assert is_risky(fp)


def test_flags_attribute_match():
    fp = {"text": "OK", "attributes": {"aria-label": "Archive this record"}}
    assert is_risky(fp)


def test_flags_class_match():
    fp = {"text": "Go", "attributes": {}, "classes": ["btn", "btn-destroy-action"]}
    assert is_risky(fp)


def test_does_not_flag_safe_element():
    fp = {"text": "Save", "attributes": {"type": "submit"}, "classes": ["btn", "btn-primary"]}
    assert not is_risky(fp)


def test_custom_keyword_list():
    fp = {"text": "Approve", "attributes": {}}
    assert is_risky(fp, keywords=["approve"])
    assert not is_risky(fp, keywords=["delete"])
