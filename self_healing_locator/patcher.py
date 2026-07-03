"""Patch a literal selector string at a known file:line back into a test script.

Used for the "inline" usage style (`healer.locate_inline(page, "#login-btn")`),
where the selector lives directly in test source rather than in the locator map.
The locator-map based flow does not need this -- healing the map file *is* the
patch.
"""

from __future__ import annotations

import re
from pathlib import Path


def patch_source_selector(file_path: str, line_no: int, old_selector: str, new_selector: str) -> bool:
    """Replace the first quoted occurrence of `old_selector` on `line_no` with
    `new_selector`, preserving the original quote style. Returns True if a
    replacement was made.
    """
    path = Path(file_path)
    if not path.exists() or not line_no:
        return False

    lines = path.read_text().splitlines(keepends=True)
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return False

    line = lines[idx]
    pattern = re.compile(r'(["\'])' + re.escape(old_selector) + r'\1')
    new_line, count = pattern.subn(lambda m: m.group(1) + new_selector + m.group(1), line, count=1)
    if count == 0:
        return False

    lines[idx] = new_line
    path.write_text("".join(lines))
    return True
