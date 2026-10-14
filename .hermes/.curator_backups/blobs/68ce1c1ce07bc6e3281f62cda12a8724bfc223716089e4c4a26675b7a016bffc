#!/usr/bin/env python3
"""Validate a DrawIO file produced by bpmn2drawio (or any BPMN converter).

Catches the three classes of post-conversion problems documented in the
diagram-format-conversion skill:

1. Duplicate mxCell IDs (causes "Duplicate ID '1'" error on open)
2. IDs < 2 (collide with the reserved root skeleton)
3. Unnamed artifact vertices (lane-header labels and task-type glyphs
   that bpmn2drawio emits without proper parent binding)

Usage:
    python3 verify_drawio.py /path/to/diagram.drawio
    python3 verify_drawio.py /root/diagram_1_v2.drawio
Exit code 0 on clean file, 1 on any FAIL-class problem found.
"""
import sys
import xml.etree.ElementTree as ET
import re


def main(path: str) -> int:
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"FAIL: malformed XML - {e}")
        return 1

    root = tree.getroot()
    cells = root.findall('.//mxCell')
    if not cells:
        print("FAIL: no <mxCell> elements found")
        return 1

    ids = [c.get('id') for c in cells]
    vertices = [c for c in cells if c.get('vertex') == '1']
    edges = [c for c in cells if c.get('edge') == '1']

    problems = []

    # 1. Duplicate IDs
    counts = {}
    for i in ids:
        counts[i] = counts.get(i, 0) + 1
    dupes = sorted([i for i, n in counts.items() if n > 1], key=lambda x: int(x) if x.isdigit() else 0)
    if dupes:
        problems.append(f"DUPLICATE IDs ({len(dupes)}): {dupes[:10]}{'...' if len(dupes) > 10 else ''}")

    # 2. User cells with reserved root IDs (0 or 1)
    user_cells_with_root_id = []
    for c in cells:
        cid = c.get('id')
        if cid in ('0', '1') and (c.get('vertex') == '1' or c.get('edge') == '1'):
            user_cells_with_root_id.append((cid, c.get('value', '')))
    if user_cells_with_root_id:
        problems.append(f"USER CELLS with reserved root IDs: {user_cells_with_root_id}")

    # 3. Unnamed artifact vertices (lane labels, task-type glyphs)
    artifacts = []
    for c in vertices:
        val = c.get('value', '') or ''
        if not val.strip():
            geom = c.find('mxGeometry')
            x = y = w = h = '?'
            if geom is not None:
                x = geom.get('x', '?')
                y = geom.get('y', '?')
                w = geom.get('width', '?')
                h = geom.get('height', '?')
            artifacts.append((c.get('id'), f"({x},{y}) {w}x{h}"))
    if artifacts:
        sev = 'WARN' if len(artifacts) <= 50 else 'FAIL'
        problems.append(
            f"{sev}: {len(artifacts)} unnamed artifact vertices "
            f"(bpmn2drawio lane labels / task glyphs without parent binding). "
            f"Sample: {artifacts[:3]}"
        )

    # Report
    print(f"=== {path} ===")
    print(f"  cells={len(cells)}  vertices={len(vertices)}  edges={len(edges)}  unique_ids={len(set(ids))}")
    if problems:
        print("  Problems:")
        for p in problems:
            print(f"    - {p}")
        any_fail = any(p.startswith('FAIL') or p.startswith('DUPLICATE') or p.startswith('USER') for p in problems)
        return 1 if any_fail else 0
    else:
        print("  OK - no problems detected")
        return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: verify_drawio.py <path/to/file.drawio>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))