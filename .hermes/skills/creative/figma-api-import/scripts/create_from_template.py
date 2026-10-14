"""
Создание нод в Figma файле по JSON-шаблону.

Использует POST /v1/files/{file_key}/nodes для программного наполнения.

Usage:
    python3 create_from_template.py \
      --file-key=ABC123 \
      --template=./template.json \
      [--page=0:1]
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from figma_client import FigmaClient


def hex_to_rgba(color: str) -> dict:
    """Конвертирует #RRGGBB → {r,g,b,a} (0-1)."""
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    r = int(color[0:2], 16) / 255.0
    g = int(color[2:4], 16) / 255.0
    b = int(color[4:6], 16) / 255.0
    return {"r": r, "g": g, "b": b, "a": 1.0}


def convert_node_to_figma(node: dict) -> dict:
    """Конвертирует наш внутренний формат в Figma API формат."""
    figma_node = {
        "name": node.get("name", "Unnamed"),
        "type": node.get("type", "FRAME"),
    }

    # Геометрия
    if "x" in node:
        figma_node["x"] = node["x"]
    if "y" in node:
        figma_node["y"] = node["y"]
    if "width" in node:
        figma_node["width"] = node["width"]
    if "height" in node:
        figma_node["height"] = node["height"]

    # Fills
    if "backgroundColor" in node:
        color = node["backgroundColor"]
        if isinstance(color, str):
            color = hex_to_rgba(color)
        figma_node["fills"] = [{"type": "SOLID", "color": color}]

    # Strokes
    if "strokeColor" in node:
        color = node["strokeColor"]
        if isinstance(color, str):
            color = hex_to_rgba(color)
        figma_node["strokes"] = [{"type": "SOLID", "color": color}]

    if "strokeWeight" in node:
        figma_node["strokeWeight"] = node["strokeWeight"]

    if "cornerRadius" in node:
        figma_node["cornerRadius"] = node["cornerRadius"]

    # Текст
    if node.get("type") == "TEXT":
        figma_node["characters"] = node.get("characters", "")
        if "fontSize" in node:
            figma_node["fontSize"] = node["fontSize"]
        if "fontWeight" in node:
            figma_node["fontWeight"] = node["fontWeight"]
        if "fontFamily" in node:
            figma_node["fontFamily"] = node["fontFamily"]
        if "textAlignHorizontal" in node:
            figma_node["textAlignHorizontal"] = node["textAlignHorizontal"]

    # Parent (для вложенных)
    if "parent" in node:
        figma_node["parent"] = node["parent"]

    # Children (рекурсивно)
    if "children" in node:
        figma_node["children"] = [
            convert_node_to_figma(child) for child in node["children"]
        ]

    return figma_node


def create_from_template(file_key: str, template: dict, page_id: Optional[str] = None) -> dict:
    """
    Создаёт ноды в Figma файле по JSON-шаблону.

    Структура template:
    {
      "pages": [
        {
          "name": "Page 1",
          "frames": [
            { "name": "Hero", "type": "FRAME", "x": 0, "y": 0, ... },
            { "name": "Title", "type": "TEXT", "characters": "...", ... }
          ]
        }
      ]
    }
    """
    client = FigmaClient()

    # 1. Получаем файл для определения page_id если не указан
    if not page_id:
        file_data = client.get_file(file_key)
        pages = file_data.get("document", {}).get("children", [])
        if not pages:
            raise RuntimeError(f"No pages found in file {file_key}")
        page_id = pages[0]["id"]
        print(f"Using page_id: {page_id} ({pages[0].get('name')})", file=sys.stderr)

    # 2. Конвертируем template → Figma API формат
    pages = template.get("pages", [])
    if not pages:
        raise RuntimeError("Template must have 'pages' array")

    all_nodes = []
    for page_spec in pages:
        for frame_spec in page_spec.get("frames", []):
            frame_spec["parent"] = page_id
            figma_node = convert_node_to_figma(frame_spec)
            all_nodes.append(figma_node)

    if not all_nodes:
        raise RuntimeError("No nodes to create")

    # 3. Создаём ноды через API
    print(f"Creating {len(all_nodes)} top-level nodes in {file_key}...", file=sys.stderr)

    # Figma API принимает массив nodes
    # POST /v1/files/{file_key}/nodes
    result = client._request(
        f"files/{file_key}/nodes",
        method_override="POST",
        json_body={"nodes": all_nodes}
    )

    return {
        "status": "ok",
        "file_key": file_key,
        "page_id": page_id,
        "nodes_created": len(all_nodes),
        "result": result
    }


def main():
    parser = argparse.ArgumentParser(description="Create Figma nodes from JSON template")
    parser.add_argument("--file-key", required=True, help="Target Figma file key")
    parser.add_argument("--template", required=True, help="Path to JSON template")
    parser.add_argument("--page", help="Target page node ID (default: first page)")
    args = parser.parse_args()

    if not os.path.exists(args.template):
        print(f"Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)

    with open(args.template) as f:
        template = json.load(f)

    try:
        result = create_from_template(args.file_key, template, args.page)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
