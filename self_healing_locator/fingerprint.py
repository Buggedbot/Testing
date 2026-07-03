"""JS snippets that capture an "element fingerprint": a bundle of tag, attributes,
text, position and parent context that is stable enough to re-identify an element
after its selector (id/class) has changed, but detailed enough to tell it apart
from unrelated elements on the page.

Candidate collection recurses into *open* shadow roots (Playwright's own CSS
engine pierces these too, so healed selectors resolve directly via
`page.locator()`). Closed shadow roots aren't reachable from JS at all -- an
inherent platform limitation, not something this library can work around.

Cross-frame (iframe) coverage is handled at the Python level in healer.py by
running these same scripts once per `page.frame`, since Playwright can
evaluate inside frames regardless of same-origin restrictions.
"""

# Shared extraction logic, nested inside each outer function below -- Playwright's
# evaluate() expects the whole script to be a single expression/function, so the
# helper can't live as a separate top-level statement.
_EXTRACT_FN_BODY = """
    function extract(el) {
        const rect = el.getBoundingClientRect();
        const attrs = {};
        for (const attr of el.attributes) {
            if (attr.name === "id" || attr.name === "class" || attr.name === "style") continue;
            attrs[attr.name] = attr.value;
        }
        const classes = (el.className && typeof el.className === "string")
            ? el.className.split(/\\s+/).filter(Boolean)
            : [];
        const parent = el.parentElement;
        let parentInfo = null;
        let domIndex = 0;
        if (parent) {
            const sameTagSiblings = Array.from(parent.children).filter(c => c.tagName === el.tagName);
            domIndex = sameTagSiblings.indexOf(el);
            const parentClasses = (parent.className && typeof parent.className === "string")
                ? parent.className.split(/\\s+/).filter(Boolean)
                : [];
            parentInfo = { tag: parent.tagName.toLowerCase(), id: parent.id || null, classes: parentClasses };
        }
        return {
            tag: el.tagName.toLowerCase(),
            id: el.id || null,
            classes: classes,
            text: (el.textContent || "").trim().slice(0, 120),
            attributes: attrs,
            bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
            dom_index: domIndex,
            parent: parentInfo,
            in_shadow_dom: el.getRootNode() !== document,
        };
    }
"""

# Recursively collects document + every open shadow root reachable from it.
_COLLECT_ROOTS_FN_BODY = """
    function collectRoots(root, acc) {
        acc.push(root);
        const all = root.querySelectorAll("*");
        for (const el of all) {
            if (el.shadowRoot) collectRoots(el.shadowRoot, acc);
        }
        return acc;
    }
"""

# Used with page.eval_on_selector(selector, SINGLE_ELEMENT_JS) to fingerprint one element.
SINGLE_ELEMENT_JS = f"""
(el) => {{
{_EXTRACT_FN_BODY}
    return extract(el);
}}
"""

# Used with elementHandle.evaluate(ELEMENT_HANDLE_JS) to fingerprint a known ElementHandle.
ELEMENT_HANDLE_JS = SINGLE_ELEMENT_JS

# Elements likely to be targeted by test locators.
CANDIDATE_QUERY = (
    "a, button, input, select, textarea, label, "
    "[role], [onclick], [data-testid], [tabindex]"
)

# Used with frame.evaluate(CANDIDATES_JS, tag) to collect fingerprints of same-tag
# candidate elements across a frame's document *and* every open shadow root in it.
CANDIDATES_JS = f"""
(tag) => {{
{_EXTRACT_FN_BODY}
{_COLLECT_ROOTS_FN_BODY}
    const roots = collectRoots(document, []);
    let nodes = [];
    for (const root of roots) {{
        nodes = nodes.concat(Array.from(root.querySelectorAll("{CANDIDATE_QUERY}")));
    }}
    const filtered = tag ? nodes.filter(n => n.tagName.toLowerCase() === tag) : nodes;
    return filtered.map(extract);
}}
"""
