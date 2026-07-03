"""Heuristic DOM-similarity scoring: given the fingerprint of a previously known-good
element and a candidate fingerprint found on the page after a UI change, produce a
confidence score in [0, 1] that they are "the same" element.

No network/LLM calls -- pure structural + textual similarity, weighted so that
stable signals (data-testid, name, role, text) count for more than volatile ones
(generated ids, exact pixel position).
"""

from __future__ import annotations

import math
from difflib import SequenceMatcher
from typing import Any, Mapping

# Feature weights, tuned so that text/attributes/classes (which usually survive a
# redesign) dominate over id and position (which usually don't).
WEIGHTS = {
    "data_testid": 0.20,
    "name_attr": 0.15,
    "text": 0.20,
    "classes": 0.12,
    "attributes": 0.13,
    "id": 0.08,
    "position": 0.07,
    "dom_index": 0.05,
    "parent": 0.10,
}
# Note: weights intentionally sum to slightly more than 1.0 across mutually-partial
# signals; the final score is normalized by the sum of weights actually applied.

_STABLE_ATTRS = ("type", "placeholder", "aria-label", "role", "href", "value")


def _text_ratio(a: str | None, b: str | None) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _attr_similarity(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    keys = [k for k in _STABLE_ATTRS if k in (a or {}) or k in (b or {})]
    if not keys:
        return 1.0
    matches = 0.0
    for k in keys:
        va, vb = (a or {}).get(k), (b or {}).get(k)
        if va is None and vb is None:
            matches += 1.0
        elif va is None or vb is None:
            continue
        elif va == vb:
            matches += 1.0
        else:
            matches += _text_ratio(str(va), str(vb)) * 0.5
    return matches / len(keys)


def _position_similarity(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    bbox_a, bbox_b = a.get("bbox"), b.get("bbox")
    if not bbox_a or not bbox_b:
        return 0.5
    dx = bbox_a.get("x", 0) - bbox_b.get("x", 0)
    dy = bbox_a.get("y", 0) - bbox_b.get("y", 0)
    dist = math.hypot(dx, dy)
    # Decay: full score at 0px, ~0.5 at 150px, near 0 past 500px.
    return math.exp(-dist / 200.0)


def _parent_similarity(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    pa, pb = a.get("parent"), b.get("parent")
    if not pa and not pb:
        return 1.0
    if not pa or not pb:
        return 0.0
    score = 0.0
    total = 0.0
    total += 1.0
    score += 1.0 if pa.get("tag") == pb.get("tag") else 0.0
    total += 1.0
    score += _jaccard(pa.get("classes", []), pb.get("classes", []))
    return score / total


def similarity(target: Mapping[str, Any], candidate: Mapping[str, Any]) -> float:
    """Score how likely `candidate` is a re-identification of `target`.

    Both are fingerprint dicts as produced by fingerprint.SINGLE_ELEMENT_JS /
    CANDIDATES_JS. Returns a value in [0, 1].
    """
    if target.get("tag") != candidate.get("tag"):
        return 0.0

    score = 0.0
    weight_used = 0.0

    testid_a = (target.get("attributes") or {}).get("data-testid")
    testid_b = (candidate.get("attributes") or {}).get("data-testid")
    if testid_a or testid_b:
        w = WEIGHTS["data_testid"]
        score += w * (1.0 if testid_a and testid_a == testid_b else 0.0)
        weight_used += w

    name_a = (target.get("attributes") or {}).get("name")
    name_b = (candidate.get("attributes") or {}).get("name")
    if name_a or name_b:
        w = WEIGHTS["name_attr"]
        score += w * (1.0 if name_a and name_a == name_b else 0.0)
        weight_used += w

    w = WEIGHTS["text"]
    score += w * _text_ratio(target.get("text"), candidate.get("text"))
    weight_used += w

    w = WEIGHTS["classes"]
    score += w * _jaccard(target.get("classes", []), candidate.get("classes", []))
    weight_used += w

    w = WEIGHTS["attributes"]
    score += w * _attr_similarity(target.get("attributes") or {}, candidate.get("attributes") or {})
    weight_used += w

    w = WEIGHTS["id"]
    score += w * _text_ratio(target.get("id"), candidate.get("id"))
    weight_used += w

    w = WEIGHTS["position"]
    score += w * _position_similarity(target, candidate)
    weight_used += w

    w = WEIGHTS["dom_index"]
    score += w * (1.0 if target.get("dom_index") == candidate.get("dom_index") else 0.0)
    weight_used += w

    w = WEIGHTS["parent"]
    score += w * _parent_similarity(target, candidate)
    weight_used += w

    if weight_used == 0:
        return 0.0
    return max(0.0, min(1.0, score / weight_used))
