#!/usr/bin/env python3
"""
IDEF0 ICOM consistency checker.

Reads an .excalidraw JSON file, extracts ICOM on the parent
diagram's block side and the child diagram's Frame side, and
compares the two sets to detect lost or invented arrows.

Usage:
    python icom_consistency_check.py <file.excalidraw> \\
        --parent-block <block_id> \\
        --child-frame <frame_id> \\
        [--tunneled "I1,I2" --tunneled-role input]

If --parent-block and --child-frame are omitted, the script
prints all detected blocks and frames so you can pick.

Exit code:
    0 - no errors
    1 - missing parent block or child frame
    2 - consistency errors found
"""

import argparse
import json
import sys
from pathlib import Path


def load_diagram(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "elements" not in data:
        raise ValueError("Not a valid .excalidraw file (no elements)")
    return data


def find_block_by_id(elements, block_id):
    for el in elements:
        if el.get("id") == block_id and el.get("type") == "rectangle":
            return el
    return None


def find_frame_by_id(elements, frame_id):
    for el in elements:
        if el.get("id") == frame_id and el.get("type") == "frame":
            return el
    return None


def find_frame_by_name(elements, level_code):
    for el in elements:
        if el.get("type") != "frame":
            continue
        name = el.get("name", "")
        if name.startswith(level_code + " ") or name.startswith(level_code + "\t"):
            return el
    return None


def find_arrows(elements):
    return [el for el in elements if el.get("type") == "arrow"]


def arrow_binds_to(arrow, element_id):
    sb = arrow.get("startBinding")
    eb = arrow.get("endBinding")
    sb_id = sb.get("elementId") if isinstance(sb, dict) else None
    eb_id = eb.get("elementId") if isinstance(eb, dict) else None
    return element_id in (sb_id, eb_id)


def arrow_attached_side(arrow, block):
    sb = arrow.get("startBinding")
    eb = arrow.get("endBinding")
    sb_id = sb.get("elementId") if isinstance(sb, dict) else None
    eb_id = eb.get("elementId") if isinstance(eb, dict) else None
    points = arrow.get("points", [[0, 0], [0, 0]])

    if sb_id == block["id"]:
        sx = arrow["x"] + points[0][0]
        sy = arrow["y"] + points[0][1]
    elif eb_id == block["id"]:
        end = points[-1]
        sx = arrow["x"] + end[0]
        sy = arrow["y"] + end[1]
    else:
        return None

    bx = block["x"]
    by = block["y"]
    bw = block["width"]
    bh = block["height"]
    right = bx + bw
    bottom = by + bh

    distances = {
        "top": abs(sy - by),
        "right": abs(sx - right),
        "bottom": abs(sy - bottom),
        "left": abs(sx - bx),
    }
    side = min(distances, key=distances.get)
    if distances[side] > 20:
        return None
    return side


SIDE_TO_ROLE = {
    "top": "control",
    "right": "output",
    "bottom": "mechanism",
    "left": "input",
}


def extract_parent_icom(block, arrows):
    icom = {"input": [], "control": [],
            "output": [], "mechanism": []}
    for arrow in arrows:
        if not arrow_binds_to(arrow, block["id"]):
            continue
        side = arrow_attached_side(arrow, block)
        if side is None:
            continue
        role = SIDE_TO_ROLE[side]
        name = arrow.get("text") or arrow.get("id")
        icom[role].append(name)
    return icom


def arrow_free_end(arrow):
    sb = arrow.get("startBinding")
    eb = arrow.get("endBinding")
    sb_id = sb.get("elementId") if isinstance(sb, dict) else None
    eb_id = eb.get("elementId") if isinstance(eb, dict) else None
    points = arrow.get("points", [[0, 0], [0, 0]])

    if sb_id is None and eb_id is not None:
        end = points[0]
        return (arrow["x"] + end[0], arrow["y"] + end[1])
    if eb_id is None and sb_id is not None:
        end = points[-1]
        return (arrow["x"] + end[0], arrow["y"] + end[1])
    return None


def nearest_frame_edge(point, frame, tol=20):
    px, py = point
    fx = frame["x"]
    fy = frame["y"]
    fw = frame["width"]
    fh = frame["height"]
    left = fx
    right = fx + fw
    top = fy
    bottom = fy + fh
    distances = {
        "left": abs(px - left),
        "right": abs(px - right),
        "top": abs(py - top),
        "bottom": abs(py - bottom),
    }
    edge = min(distances, key=distances.get)
    if distances[edge] > tol:
        return None
    return edge


def extract_child_icom(frame, arrows):
    icom = {"input": [], "control": [],
            "output": [], "mechanism": []}
    for arrow in arrows:
        free = arrow_free_end(arrow)
        if free is None:
            continue
        edge = nearest_frame_edge(free, frame)
        if edge is None:
            continue
        role = {"left": "input", "top": "control",
                "right": "output",
                "bottom": "mechanism"}[edge]
        name = arrow.get("text") or arrow.get("id")
        icom[role].append(name)
    return icom


def parse_tunneled(spec):
    """`I1,I2,C1` -> {"input": {"I1", "I2"}, "control": {"C1"},
                       "output": set(), "mechanism": set()}"""
    if not spec:
        return {"input": set(), "control": set(),
                "output": set(), "mechanism": set()}
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    name_to_role = {"I": "input", "C": "control",
                    "O": "output", "M": "mechanism"}
    result = {"input": set(), "control": set(),
              "output": set(), "mechanism": set()}
    for p in parts:
        m = p
        if p[:1] in name_to_role and len(p) > 1 and p[1].isdigit():
            role = name_to_role[p[:1]]
            result[role].add(p)
        else:
            result["input"].add(p)
    return result


def check_consistency(parent_icom, child_icom, tunnels):
    errors = []
    for role in ["input", "control", "output", "mechanism"]:
        p = set(parent_icom[role])
        c = set(child_icom[role])
        for name in p - c:
            is_tunnel = name in tunnels[role]
            errors.append({
                "severity": "info" if is_tunnel else "high",
                "role": role,
                "name": name,
                "problem": ("tunneled but missing on child boundary"
                            if is_tunnel else
                            "lost during decomposition")
            })
        for name in c - p:
            errors.append({
                "severity": "high",
                "role": role,
                "name": name,
                "problem": "appears on child but not on parent"
            })
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--parent-block", default=None)
    ap.add_argument("--child-frame", default=None)
    ap.add_argument("--list", action="store_true",
                    help="List detected blocks and frames")
    ap.add_argument("--tunneled", action="append", default=[],
                    help="Comma-separated list of tunneled arrow names")
    args = ap.parse_args()

    diagram = load_diagram(args.file)
    elements = diagram["elements"]
    arrows = find_arrows(elements)

    if args.list:
        print("=== Blocks (rectangles) ===")
        for el in elements:
            if el.get("type") == "rectangle":
                print(f"  {el['id']}: x={el['x']} y={el['y']} "
                      f"w={el['width']} h={el['height']}")
        print("\n=== Frames ===")
        for el in elements:
            if el.get("type") == "frame":
                print(f"  {el['id']}: name='{el.get('name','')}'")
        return 0

    if not args.parent_block:
        print("ERROR: --parent-block required (use --list to see ids)",
              file=sys.stderr)
        return 1
    if not args.child_frame:
        print("ERROR: --child-frame required (use --list to see ids)",
              file=sys.stderr)
        return 1

    block = find_block_by_id(elements, args.parent_block)
    frame = find_frame_by_id(elements, args.child_frame)
    if block is None:
        print(f"ERROR: parent block '{args.parent_block}' not found",
              file=sys.stderr)
        return 1
    if frame is None:
        print(f"ERROR: child frame '{args.child_frame}' not found",
              file=sys.stderr)
        return 1

    parent_icom = extract_parent_icom(block, arrows)
    child_icom = extract_child_icom(frame, arrows)

    tunnels = {"input": set(), "control": set(),
               "output": set(), "mechanism": set()}
    for spec in args.tunneled:
        parsed = parse_tunneled(spec)
        for r in tunnels:
            tunnels[r] |= parsed[r]

    print(f"Parent block {args.parent_block} ICOM:")
    for role in ["input", "control", "output", "mechanism"]:
        print(f"  {role:10s}: {sorted(parent_icom[role])}")
    print()
    print(f"Child frame {args.child_frame} ICOM (boundary arrows):")
    for role in ["input", "control", "output", "mechanism"]:
        print(f"  {role:10s}: {sorted(child_icom[role])}")
    print()

    errors = check_consistency(parent_icom, child_icom, tunnels)
    if not errors:
        print("OK: ICOM consistent.")
        return 0

    print(f"Found {len(errors)} discrepancies:")
    for e in errors:
        marker = "!!!" if e["severity"] == "high" else "i"
        print(f"  [{marker}] role={e['role']} name={e['name']!r}: "
              f"{e['problem']}")
    return 2


if __name__ == "__main__":
    sys.exit(main())