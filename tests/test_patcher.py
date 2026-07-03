from self_healing_locator.patcher import patch_source_selector


def test_patches_matching_quoted_selector(tmp_path):
    src = tmp_path / "test_login.py"
    src.write_text(
        'def test_login(page):\n'
        '    btn = healer.locate_inline(page, "#login-btn")\n'
        '    btn.click()\n'
    )

    ok = patch_source_selector(str(src), 2, "#login-btn", "#act-3392")

    assert ok is True
    assert '"#act-3392"' in src.read_text()
    assert "#login-btn" not in src.read_text()


def test_preserves_single_quote_style(tmp_path):
    src = tmp_path / "test_login.py"
    src.write_text("btn = healer.locate_inline(page, '#login-btn')\n")

    patch_source_selector(str(src), 1, "#login-btn", "#act-3392")

    assert "'#act-3392'" in src.read_text()


def test_returns_false_when_selector_not_found_on_line(tmp_path):
    src = tmp_path / "test_login.py"
    src.write_text('btn = healer.locate_inline(page, "#something-else")\n')

    ok = patch_source_selector(str(src), 1, "#login-btn", "#act-3392")

    assert ok is False


def test_returns_false_for_missing_file(tmp_path):
    ok = patch_source_selector(str(tmp_path / "nope.py"), 1, "#a", "#b")
    assert ok is False
