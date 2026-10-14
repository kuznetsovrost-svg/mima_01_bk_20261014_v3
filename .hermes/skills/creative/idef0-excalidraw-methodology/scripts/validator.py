#!/usr/bin/env python3
"""
IDEF0 Excalidraw validator CLI.

Thin wrapper that runs common analyses against an .excalidraw
file. Each subcommand is independent; failures in one do not
block the others.

Usage:
    python validator.py summary <file>
    python validator.py validate <file>
    python validator.py tunnels <file>
    python validator.py icom <file> --parent-block <id> --child-frame <id>
    python validator.py catalogue <file> [--frame-id <id>]
    python validator.py description <file>
"""

import argparse
import json
import sys
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_blocks(elements):
    return [el for el in elements if el.get("type") == "rectangle"]


def find_frames(elements):
    return [el for el in elements if el.get("type") == "frame"]


def find_arrows(elements):
    return [el for el in elements if el.get("type") == "arrow"]


def find_texts(elements):
    return [el for el in elements if el.get("type") == "text"]


def cmd_summary(args):
    diagram = load(args.file)
    elements = diagram["elements"]
    print(f"File: {args.file}")
    print(f"  rectangles: {len(find_blocks(elements))}")
    print(f"  texts:      {len(find_texts(elements))}")
    print(f"  arrows:     {len(find_arrows(elements))}")
    print(f"  frames:     {len(find_frames(elements))}")
    print()
    print("Frames:")
    for fr in find_frames(elements):
        print(f"  {fr.get('id')}: {fr.get('name', '')}")
    return 0


def cmd_validate(args):
    diagram = load(args.file)
    elements = diagram["elements"]
    errors = []
    warnings = []

    for blk in find_blocks(elements):
        gid = blk.get("groupIds", [])
        if not gid:
            errors.append(f"block {blk['id']} has no groupIds")
            continue
        shared = [t for t in find_texts(elements)
                  if set(gid) & set(t.get("groupIds", []))]
        has_name = any(t.get("text", "").strip() for t in shared)
        if not has_name:
            errors.append(f"block {blk['id']} has no function-name text")

    for arr in find_arrows(elements):
        sb = arr.get("startBinding")
        eb = arr.get("endBinding")
        if not sb and not eb:
            warnings.append(
                f"arrow {arr['id']} has neither startBinding nor endBinding")

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("OK: no structural errors.")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    return 1 if errors else 0


def cmd_tunnels(args):
    from tunnel_detector import find_tunnels, explain_tunnel
    diagram = load(args.file)
    tunnels = find_tunnels(diagram["elements"])
    if not tunnels:
        print("No tunneled arrows found.")
        return 0
    print(f"Found {len(tunnels)} tunneled arrows:")
    for t in tunnels:
        print(f"  - {explain_tunnel(t)}")
    return 0


def cmd_icom(args):
    from icom_consistency_check import (
        find_block_by_id, find_frame_by_id, find_arrows,
        extract_parent_icom, extract_child_icom,
    )
    diagram = load(args.file)
    elements = diagram["elements"]
    block = find_block_by_id(elements, args.parent_block)
    frame = find_frame_by_id(elements, args.child_frame)
    if not block:
        print(f"parent block '{args.parent_block}' not found",
              file=sys.stderr)
        return 1
    if not frame:
        print(f"child frame '{args.child_frame}' not found",
              file=sys.stderr)
        return 1
    arrows = find_arrows(elements)
    parent_icom = extract_parent_icom(block, arrows)
    child_icom = extract_child_icom(frame, arrows)
    print(f"Parent block {args.parent_block}:")
    for role in ("input", "control", "output", "mechanism"):
        print(f"  {role:10s} {sorted(parent_icom[role])}")
    print(f"Child frame {args.child_frame}:")
    for role in ("input", "control", "output", "mechanism"):
        print(f"  {role:10s} {sorted(child_icom[role])}")
    return 0


def cmd_catalogue(args):
    """Print arrow catalogue summary for the given diagram (or frame)."""
    diagram = load(args.file)
    elements = diagram["elements"]
    arrows = find_arrows(elements)

    if args.frame_id:
        elements = [el for el in elements
                    if el.get("frameId") == args.frame_id
                    or el.get("id") == args.frame_id]

    print(f"Frame: {args.frame_id or '(all)'}")
    print(f"  arrows: {len(arrows)}")
    for arr in arrows:
        text = arr.get("text", "") or arr.get("id", "?")
        sb = arr.get("startBinding", {})
        eb = arr.get("endBinding", {})
        sb_id = sb.get("elementId") if isinstance(sb, dict) else None
        eb_id = eb.get("elementId") if isinstance(eb, dict) else None
        print(f"  - {text[:60]}: {sb_id or 'free'} -> {eb_id or 'free'}")
    return 0


def cmd_description(args):
    """Stub: full node description requires side detection per block;
    defer to the conventions reference for the algorithm."""
    print("Node description is generated per-block by walking the four")
    print("sides of each rectangle in clockwise order from top. See")
    print("references/idef0-conventions.md section 5 for the template.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_sum = sub.add_parser("summary", help="Diagram summary")
    p_sum.add_argument("file")

    p_val = sub.add_parser("validate", help="Structural validation")
    p_val.add_argument("file")

    p_tun = sub.add_parser("tunnels", help="List tunneled arrows")
    p_tun.add_argument("file")

    p_icom = sub.add_parser("icom", help="ICOM extraction (no check)")
    p_icom.add_argument("file")
    p_icom.add_argument("--parent-block", required=True)
    p_icom.add_argument("--child-frame", required=True)

    p_cat = sub.add_parser("catalogue", help="Arrow catalogue")
    p_cat.add_argument("file")
    p_cat.add_argument("--frame-id", default=None)

    p_desc = sub.add_parser("description",
                            help="Node description (stub, see references)")
    p_desc.add_argument("file")

    args = ap.parse_args()
    cmds = {
        "summary": cmd_summary,
        "validate": cmd_validate,
        "tunnels": cmd_tunnels,
        "icom": cmd_icom,
        "catalogue": cmd_catalogue,
        "description": cmd_description,
    }
    return cmds[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())