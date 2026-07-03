"""Turn a healed element fingerprint back into a robust, re-usable CSS selector.

Preference order (most to least stable across future UI changes):
1. data-testid / data-test / data-qa attributes
2. a non-dynamic-looking id
3. a `name` attribute
4. other stable attributes (aria-label, placeholder, role+type)
5. a structural fallback: tag + nth-of-type within its parent
"""

from __future__ import annotations

import re
from typing import Any, Mapping

_TESTID_ATTRS = ("data-testid", "data-test", "data-qa", "data-cy")

# Looks-dynamic heuristics: long digit runs, uuid-like, or long random-looking
# alphanumeric hashes -- these are unlikely to survive the next deploy either.
_DYNAMIC_ID_RE = re.compile(
    r"(\d{4,})|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4})|(:r[0-9a-z]+:)|([a-z0-9]{10,}$)",
    re.IGNORECASE,
)


def _css_escape(value: str) -> str:
    return value.replace('"', '\\"')


def looks_dynamic(id_or_class: str) -> bool:
    return bool(_DYNAMIC_ID_RE.search(id_or_class))


def build_selector(fp: Mapping[str, Any]) -> str:
    tag = fp.get("tag", "*")
    attrs = fp.get("attributes") or {}

    for key in _TESTID_ATTRS:
        if attrs.get(key):
            return f'[{key}="{_css_escape(attrs[key])}"]'

    element_id = fp.get("id")
    if element_id and not looks_dynamic(element_id):
        return f"#{element_id}" if re.match(r"^[A-Za-z][\w-]*$", element_id) else f'[id="{_css_escape(element_id)}"]'

    if attrs.get("name"):
        return f'{tag}[name="{_css_escape(attrs["name"])}"]'

    if attrs.get("aria-label"):
        return f'{tag}[aria-label="{_css_escape(attrs["aria-label"])}"]'

    if attrs.get("placeholder"):
        return f'{tag}[placeholder="{_css_escape(attrs["placeholder"])}"]'

    if attrs.get("type"):
        base = f'{tag}[type="{_css_escape(attrs["type"])}"]'
    else:
        base = tag

    classes = [c for c in (fp.get("classes") or []) if not looks_dynamic(c)]
    if classes:
        base += "." + ".".join(re.escape(c) for c in classes[:2])

    dom_index = fp.get("dom_index")
    parent = fp.get("parent") or {}
    parent_selector = ""
    if parent.get("id") and not looks_dynamic(parent["id"]):
        parent_selector = f'#{parent["id"]} > '
    elif parent.get("tag"):
        parent_selector = f'{parent["tag"]} > '

    if dom_index is not None and dom_index >= 0:
        return f"{parent_selector}{base}:nth-of-type({dom_index + 1})"
    return f"{parent_selector}{base}"
