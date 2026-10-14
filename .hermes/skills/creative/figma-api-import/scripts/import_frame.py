"""
Импорт фрейма из Figma + рекурсивно все его компоненты с variants.

Usage:
    python3 import_frame.py --file-key=ABC --node-id=1:23 [--output=./out/]
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from figma_client import FigmaClient


def collect_component_ids(node: dict, ids: set):
    """Рекурсивно собирает ID всех компонент-инстансов внутри ноды."""
    if node.get("type") == "INSTANCE" and node.get("componentId"):
        ids.add(node["componentId"])
        # Также у INSTANCES есть componentProperties с вариантами
    if "children" in node:
        for child in node["children"]:
            collect_component_ids(child, ids)


def get_component_variants(client: FigmaClient, file_key: str, component_id: str) -> dict:
    """Получить все варианты компонента через ноду."""
    # Получаем ноду компонента, чтобы увидеть componentPropertyDefinitions и children
    node_data = client.get_nodes(file_key, [component_id])
    node = node_data.get("nodes", {}).get(component_id, {}).get("document")

    if not node:
        return {"id": component_id, "name": "unknown", "variants": []}

    result = {
        "id": component_id,
        "name": node.get("name", "unknown"),
        "type": node.get("type"),
        "componentPropertyDefinitions": node.get("componentPropertyDefinitions", {}),
        "variants": []
    }

    # Для COMPONENT_SET (главный компонент с variants) — дети это конкретные варианты
    if node.get("type") == "COMPONENT_SET" and "children" in node:
        for variant in node["children"]:
            variant_info = {
                "id": variant.get("id"),
                "name": variant.get("name"),
                "componentProperties": variant.get("componentProperties", {}),
                "size": variant.get("size"),
                "fills": variant.get("fills"),
                "strokes": variant.get("strokes"),
                "characters": variant.get("characters"),
            }
            result["variants"].append(variant_info)

    # Для COMPONENT (одиночный) — сам и есть "вариант"
    elif node.get("type") == "COMPONENT":
        result["variants"].append({
            "id": node.get("id"),
            "name": node.get("name"),
            "componentProperties": node.get("componentProperties", {}),
            "size": node.get("size"),
            "fills": node.get("fills"),
            "strokes": node.get("strokes"),
            "characters": node.get("characters"),
        })

    return result


def import_frame(file_key: str, node_id: str, output_dir: str = "./figma-import") -> dict:
    """
    Импортирует фрейм и рекурсивно все его компоненты.
    Возвращает summary.
    """
    client = FigmaClient()
    node_id_decoded = node_id.replace(":", "-")  # Figma API формат

    print(f"[1/4] Загружаю фрейм {node_id} из файла {file_key}...", file=sys.stderr)
    nodes_data = client.get_nodes(file_key, [node_id_decoded])
    frame = nodes_data.get("nodes", {}).get(node_id_decoded, {}).get("document")

    if not frame:
        raise RuntimeError(f"Frame {node_id} not found in file {file_key}")

    print(f"      Frame: {frame.get('name')}", file=sys.stderr)

    # Создаём структуру вывода
    os.makedirs(output_dir, exist_ok=True)
    components_dir = os.path.join(output_dir, "components")
    os.makedirs(components_dir, exist_ok=True)

    # Сохраняем фрейм
    with open(os.path.join(output_dir, "frame.json"), "w") as f:
        json.dump(frame, f, indent=2, ensure_ascii=False)
    print(f"[2/4] Сохранён frame.json ({len(json.dumps(frame))} chars)", file=sys.stderr)

    # Собираем ID компонентов
    component_ids = set()
    collect_component_ids(frame, component_ids)
    print(f"      Найдено {len(component_ids)} компонент-инстансов", file=sys.stderr)

    # Получаем все компоненты с variants
    components = []
    if component_ids:
        print(f"[3/4] Загружаю компоненты с variants...", file=sys.stderr)
        for i, comp_id in enumerate(component_ids, 1):
            print(f"      [{i}/{len(component_ids)}] {comp_id}...", file=sys.stderr)
            try:
                comp = get_component_variants(client, file_key, comp_id)
                comp["variant_count"] = len(comp["variants"])
                components.append(comp)

                # Сохраняем каждый компонент отдельно
                fname = comp.get("name", comp_id).replace("/", "_").replace(" ", "_")
                with open(os.path.join(components_dir, f"{fname}.json"), "w") as f:
                    json.dump(comp, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"      [WARN] {comp_id}: {e}", file=sys.stderr)

    # Получаем стили
    print(f"[4/4] Загружаю стили...", file=sys.stderr)
    try:
        styles = client.get_styles(file_key)
        with open(os.path.join(output_dir, "styles.json"), "w") as f:
            json.dump(styles, f, indent=2, ensure_ascii=False)
    except Exception as e:
        styles = {"error": str(e)}
        with open(os.path.join(output_dir, "styles.json"), "w") as f:
            json.dump(styles, f, indent=2, ensure_ascii=False)

    # Получаем variables
    try:
        variables = client.get_variables(file_key)
        with open(os.path.join(output_dir, "variables.json"), "w") as f:
            json.dump(variables, f, indent=2, ensure_ascii=False)
    except Exception as e:
        variables = {"error": str(e)}
        with open(os.path.join(output_dir, "variables.json"), "w") as f:
            json.dump(variables, f, indent=2, ensure_ascii=False)

    # Summary
    summary = {
        "file_key": file_key,
        "node_id": node_id,
        "frame_name": frame.get("name"),
        "frame_size": frame.get("size"),
        "components_count": len(components),
        "total_variants": sum(c.get("variant_count", 0) for c in components),
        "components": [
            {
                "id": c["id"],
                "name": c["name"],
                "variants": c.get("variant_count", 0),
            }
            for c in components
        ],
    }

    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Markdown summary
    md = [f"# Figma Import Summary\n"]
    md.append(f"- **File**: `{file_key}`")
    md.append(f"- **Frame**: `{frame.get('name')}` ({node_id})")
    md.append(f"- **Frame size**: {frame.get('size', {}).get('x', '?')} x {frame.get('size', {}).get('y', '?')}")
    md.append(f"- **Components**: {len(components)}")
    md.append(f"- **Total variants**: {summary['total_variants']}\n")

    md.append("## Components\n")
    for c in components:
        md.append(f"### {c['name']}")
        md.append(f"- ID: `{c['id']}`")
        md.append(f"- Variants: {c.get('variant_count', 0)}")
        if c.get("componentPropertyDefinitions"):
            md.append(f"- Properties:")
            for prop_name, prop_def in c["componentPropertyDefinitions"].items():
                if prop_def.get("type") == "VARIANT":
                    md.append(f"  - `{prop_name}`: {prop_def.get('variantOptions', [])}")
        md.append("")

    with open(os.path.join(output_dir, "summary.md"), "w") as f:
        f.write("\n".join(md))

    return summary


def main():
    parser = argparse.ArgumentParser(description="Import Figma frame + components")
    parser.add_argument("--file-key", required=True, help="Figma file key")
    parser.add_argument("--node-id", required=True, help="Figma node ID (e.g., 1:23)")
    parser.add_argument("--output", default="./figma-import", help="Output directory")
    args = parser.parse_args()

    try:
        summary = import_frame(args.file_key, args.node_id, args.output)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
