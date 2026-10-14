"""
Извлекает главные компоненты с variants в формате, удобном для HTML-шаблонов.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from figma_client import FigmaClient


def extract_components(file_key: str, output_dir: str = "./figma-variants") -> dict:
    """Получить все главные компоненты с variants."""
    client = FigmaClient()
    os.makedirs(output_dir, exist_ok=True)

    # 1. Получаем все компоненты
    print("[1/2] Загружаю список компонентов...", file=sys.stderr)
    components_meta = client.get_components(file_key)
    meta = components_meta.get("meta", {})

    component_keys = []
    for c in meta.get("components", []):
        # Нас интересуют только COMPONENT_SET (главные с variants)
        if c.get("containing_component"):  # Значит это sub-component
            continue
        component_keys.append(c.get("key"))

    print(f"      Найдено {len(component_keys)} главных компонентов", file=sys.stderr)

    # 2. Получаем children file (там есть componentPropertyDefinitions)
    print("[2/2] Получаю structure с variants...", file=sys.stderr)
    file_data = client.get_file(file_key)
    document = file_data.get("document", {})

    # Ищем COMPONENT_SET ноды
    def find_component_sets(node, sets):
        if node.get("type") == "COMPONENT_SET":
            sets.append(node)
        if "children" in node:
            for child in node["children"]:
                find_component_sets(child, sets)

    component_sets = []
    find_component_sets(document, component_sets)

    print(f"      Найдено {len(component_sets)} COMPONENT_SET нод", file=sys.stderr)

    # 3. Сохраняем
    result = []
    for cs in component_sets:
        comp_info = {
            "id": cs.get("id"),
            "name": cs.get("name"),
            "description": cs.get("description"),
            "componentPropertyDefinitions": cs.get("componentPropertyDefinitions", {}),
            "variant_count": len(cs.get("children", [])),
            "variants": []
        }

        for variant in cs.get("children", []):
            comp_info["variants"].append({
                "id": variant.get("id"),
                "name": variant.get("name"),
                "componentProperties": variant.get("componentProperties", {}),
                "size": variant.get("size"),
                "fills": variant.get("fills"),
                "strokes": variant.get("strokes"),
                "strokeWeight": variant.get("strokeWeight"),
                "cornerRadius": variant.get("cornerRadius"),
                "characters": variant.get("characters"),
                "style": variant.get("style"),
            })

        result.append(comp_info)

        # Сохраняем каждый компонент отдельно
        fname = cs.get("name", cs.get("id")).replace("/", "_").replace(" ", "_")
        with open(os.path.join(output_dir, f"{fname}.json"), "w") as f:
            json.dump(comp_info, f, indent=2, ensure_ascii=False)

    # Сохраняем общий список
    with open(os.path.join(output_dir, "_all_components.json"), "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Генерируем summary
    md = [f"# Variants Inventory\n"]
    md.append(f"**File**: `{file_key}`")
    md.append(f"**Total main components**: {len(result)}")
    md.append(f"**Total variants**: {sum(c['variant_count'] for c in result)}\n")

    md.append("## Components with Variants\n")
    for c in result:
        md.append(f"### {c['name']}")
        md.append(f"- Variants: {c['variant_count']}")
        if c.get("componentPropertyDefinitions"):
            for prop_name, prop_def in c["componentPropertyDefinitions"].items():
                if prop_def.get("type") == "VARIANT":
                    md.append(f"  - `{prop_name}`: {prop_def.get('variantOptions', [])}")
        md.append("")

    with open(os.path.join(output_dir, "README.md"), "w") as f:
        f.write("\n".join(md))

    return {
        "components_count": len(result),
        "variants_count": sum(c['variant_count'] for c in result),
        "components": [{"name": c["name"], "variants": c["variant_count"]} for c in result]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file-key", required=True)
    parser.add_argument("--output", default="./figma-variants")
    args = parser.parse_args()

    try:
        result = extract_components(args.file_key, args.output)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
