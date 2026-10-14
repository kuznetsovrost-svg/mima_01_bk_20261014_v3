"""Bento/Slides deck load/save helpers.

Use these to read and write `.bento.html` decks without hand-writing the
regex surgery every time. The runtime blocks (`bento-rt-css`, `bento-rt`)
are NEVER touched — only the `<bento-doc>` JSON block is replaced.

Example:
    >>> doc = load_doc('MyDeck.bento.html')
    >>> if doc is None:
    ...     doc = new_doc()  # blank skeleton
    >>> doc['slides'].append(new_slide(title='Hello'))
    >>> save_doc('MyDeck.bento.html', doc)
"""

import json
import re
import sys

BENTO_DOC_PATTERN = re.compile(
    r'(<script[^>]*id="bento-doc"[^>]*>)(.*?)(</script>)',
    re.DOTALL,
)


def load_doc(path: str) -> dict | None:
    """Read and parse the `<bento-doc>` block. Returns None if empty."""
    text = open(path).read()
    m = BENTO_DOC_PATTERN.search(text)
    if not m:
        raise ValueError(f"no <script id=\"bento-doc\"> block in {path}")
    raw = m.group(2).strip()
    if not raw:
        return None
    return json.loads(raw)


def save_doc(path: str, doc: dict) -> None:
    """Replace the `<bento-doc>` block in-place. Preserves all runtime."""
    text = open(path).read()
    escaped = json.dumps(doc, ensure_ascii=False).replace('<', '\\u003c')

    new, n = BENTO_DOC_PATTERN.subn(
        lambda m: m.group(1) + '\n' + escaped + '\n' + m.group(3),
        text, count=1,
    )
    if n != 1:
        raise ValueError(
            f"expected exactly one bento-doc block, replaced {n} (path={path})"
        )

    open(path, 'w').write(new)


def new_doc(title: str = 'New deck') -> dict:
    """Blank-but-valid skeleton, ready to append slides to."""
    return {
        'format': 'bento/slides',
        'version': 1,
        'title': title,
        'size': {'width': 1280, 'height': 720},
        'theme': {
            'background': '#101418',
            'color': '#F2F0EA',
            'accent': '#FF9E8A',
            'fontFamily': 'system-ui, sans-serif',
        },
        'slides': [],
    }


def runtime_blocks_intact(path: str) -> bool:
    """Quick sanity check — runtime blocks present and matching IDs."""
    text = open(path).read()
    has_rt = 'id="bento-rt"' in text
    has_rt_css = 'id="bento-rt-css"' in text
    has_doc = 'id="bento-doc"' in text
    return has_rt and has_rt_css and has_doc


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('load', 'save', 'check'):
        print('usage: bento_io.py (load|save|check) path [json-doc]', file=sys.stderr)
        sys.exit(2)

    op, path = sys.argv[1], sys.argv[2]
    if op == 'load':
        doc = load_doc(path)
        print(json.dumps(doc, indent=2, ensure_ascii=False) if doc else '(empty doc)')
    elif op == 'save':
        doc = json.loads(sys.stdin.read())
        save_doc(path, doc)
    elif op == 'check':
        ok = runtime_blocks_intact(path)
        print('OK' if ok else 'BROKEN')
        sys.exit(0 if ok else 1)
