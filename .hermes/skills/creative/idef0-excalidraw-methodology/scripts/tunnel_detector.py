#!/usr/bin/env python3
"""
Tunnel detector for IDEF0 Excalidraw diagrams.

Tunnels are marked by round brackets `( )` at the very start
or end of an arrow's `text` field. Per IDEF0 conventions a
tunneled arrow does not enter any specific block of the
child diagram — its free end lies on the child Frame's edge.

Usage:
    python tunnel_detector.py <file.excalidraw>
    python tunnel_detector.py <file.excalidraw> --json
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


def classify_tunnel(text):
    """Return ('start'|'end'|'both'|None) based on bracket position."""
    if not text:
        return None
    text = text.strip()
    starts = text.startswith("(")
    ends = text.endswith(")")
    if starts and ends:
        return "both"
    if starts:
        return "end"
    if ends:
        return "start"
    return None


def extract_arrow_name(text):
    """Strip tunnel markers and return the ICOM code (first token)."""
    if not text:
        return ""
    cleaned = text.strip().lstrip("(").rstrip(")").strip()
    return cleaned.split()[0] if cleaned.split() else ""


def find_arrows(elements):
    return [el for el in elements if el.get("type") == "arrow"]


def find_tunnels(elements):
    """Yield dicts for every tunneled arrow."""
    tunnels = []
    for arrow in find_arrows(elements):
        text = arrow.get("text", "")
        side = classify_tunnel(text)
        if side is None:
            continue
        tunnels.append({
            "id": arrow.get("id"),
            "name": extract_arrow_name(text),
            "text": text,
            "tunnel_side": side,
            "full_arrow": arrow,
        })
    return tunnels


def explain_tunnel(t):
    side = t["tunnel_side"]
    name = t["name"]
    if side == "end":
        return (f"'{name}': tunneled at block end. "
                f"Free end lies on child Frame boundary.")
    if side == "start":
        return (f"'{name}': tunneled at free end. "
                f"Origin side lies on parent boundary.")
    return f"'{name}': tunneled at both ends (external coupling)."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true",
                    help="Output JSON instead of human text")
    args = ap.parse_args()

    diagram = load_diagram(args.file)
    tunnels = find_tunnels(diagram["elements"])

    if args.json:
        out = []
        for t in tunnels:
            out.append({
                "id": t["id"],
                "name": t["name"],
                "text": t["text"],
                "tunnel_side": t["tunnel_side"],
            })
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    if not tunnels:
        print("No tunneled arrows found.")
        return 0

    print(f"Found {len(tunnels)} tunneled arrows:")
    for t in tunnels:
        print(f"  - {explain_tunnel(t)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())