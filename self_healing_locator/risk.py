"""Flags healing candidates that look destructive, so the agent never
auto-clicks its way onto something like "Delete" in a client's live CRM.

This is a coarse text/attribute deny-list, not a guarantee -- it's a safety
net on top of confidence scoring, not a replacement for it.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

DEFAULT_RISK_KEYWORDS = (
    "delete",
    "remove",
    "archive",
    "deactivate",
    "disable",
    "discard",
    "unsubscribe",
    "purge",
    "destroy",
    "drop",
    "terminate",
    "revoke",
    "cancel subscription",
    "close account",
    "permanently",
)

_TEXT_FIELDS = ("text",)
_ATTR_FIELDS = ("aria-label", "title", "value", "name", "data-testid", "data-action")


def is_risky(fp: Mapping[str, Any], keywords: Iterable[str] = DEFAULT_RISK_KEYWORDS) -> bool:
    """True if the fingerprint's visible text or common attributes match a
    risk keyword (case-insensitive substring match)."""
    keywords = [k.lower() for k in keywords]
    haystacks = []

    for field in _TEXT_FIELDS:
        value = fp.get(field)
        if value:
            haystacks.append(str(value))

    attrs = fp.get("attributes") or {}
    for field in _ATTR_FIELDS:
        value = attrs.get(field)
        if value:
            haystacks.append(str(value))

    classes = fp.get("classes") or []
    haystacks.extend(classes)

    lowered = " ".join(haystacks).lower()
    return any(keyword in lowered for keyword in keywords)
