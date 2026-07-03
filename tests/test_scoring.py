from self_healing_locator.scoring import similarity


def _fp(**overrides):
    base = {
        "tag": "button",
        "id": "login-btn",
        "classes": ["btn", "btn-primary"],
        "text": "Log In",
        "attributes": {"type": "submit"},
        "bbox": {"x": 100, "y": 400, "width": 80, "height": 32},
        "dom_index": 1,
        "parent": {"tag": "form", "id": "login-form", "classes": []},
    }
    base.update(overrides)
    return base


def test_identical_fingerprint_scores_high():
    fp = _fp()
    assert similarity(fp, fp) > 0.95


def test_different_tag_scores_zero():
    target = _fp(tag="button")
    candidate = _fp(tag="input")
    assert similarity(target, candidate) == 0.0


def test_redesigned_button_still_scores_above_threshold():
    target = _fp()
    candidate = _fp(
        id="act-3392",
        classes=["mui-button", "primary-action-2b7"],
        attributes={"type": "submit"},
        bbox={"x": 180, "y": 420, "width": 90, "height": 34},
        dom_index=1,
        parent={"tag": "form", "id": "frm-x92a1", "classes": []},
    )
    score = similarity(target, candidate)
    assert score >= 0.55


def test_decoy_button_scores_lower_than_real_match():
    target = _fp()
    real_match = _fp(
        id="act-3392",
        classes=["mui-button", "primary-action-2b7"],
        attributes={"type": "submit"},
        dom_index=1,
    )
    decoy = _fp(
        id="act-3391",
        text="Cancel",
        classes=["ghost-btn", "secondary-9c1"],
        attributes={"type": "button"},
        dom_index=0,
    )
    assert similarity(target, real_match) > similarity(target, decoy)
