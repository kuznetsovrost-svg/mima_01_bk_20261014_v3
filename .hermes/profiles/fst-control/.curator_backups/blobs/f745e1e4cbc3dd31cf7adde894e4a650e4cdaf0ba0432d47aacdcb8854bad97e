"""
get_metamodel.py — CLI-утилита для получения значений MetaModel.

Использование:
    python3 scripts/get_metamodel.py --all
    python3 scripts/get_metamodel.py --title
    python3 scripts/get_metamodel.py --version
    python3 scripts/get_metamodel.py --core-version
    python3 scripts/get_metamodel.py --key <Name>

Импортируется также как модуль:
    from get_metamodel import get_metamodel_metadata

✅ После live-проверки 2026-08-07:
   - Использует get_entity_data("metamodel", data_id=<Name>)
   - entityName = "metamodel" (lowercase, не "MetaModel")
   - data_id принимает строковые значения (Title, Version, CoreVersion)
"""
from __future__ import annotations

__version__ = "1.0.19"
import argparse
import json
import sys
from pathlib import Path

# Импорт из mcp_config (централизованные URL, токен, headers, парсер SSE)
from mcp_config import (
    METAMODEL_ENTITY,
    METAMODEL_KEYS,
    mcp_init,
    mcp_call,
)


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def get_metamodel_metadata(sid: str | None = None) -> dict:
    """Достаёт все известные значения MetaModel через get_entity_data.

    Returns:
        dict: {"title": str|None, "version": str|None, "core_version": str|None}.
    """
    own_session = sid is None
    if own_session:
        sid, _ = mcp_init()

    try:
        result = {}
        for alias, key_name in METAMODEL_KEYS.items():
            try:
                data = mcp_call(
                    sid, "get_entity_data",
                    {"entityName": METAMODEL_ENTITY, "data_id": key_name},
                )
                if isinstance(data, dict) and "properties" in data:
                    value = data["properties"].get("Value", {}).get("value")
                    result[alias] = value
                else:
                    result[alias] = None
            except Exception as e:
                result[alias] = None
        return result
    finally:
        if own_session:
            pass  # mcp_init создаёт сессию, явно не закрываем


def get_metamodel_value(key_name: str, sid: str | None = None) -> str | None:
    """Достаёт одно значение MetaModel по key_name (Title/Version/CoreVersion).

    Args:
        key_name: точное имя записи (Title, Version, CoreVersion).
        sid: (опц.) уже открытая MCP-сессия.

    Returns:
        str — значение поля Value, или None если запись не найдена.
    """
    own_session = sid is None
    if own_session:
        sid, _ = mcp_init()

    try:
        data = mcp_call(
            sid, "get_entity_data",
            {"entityName": METAMODEL_ENTITY, "data_id": key_name},
        )
        if isinstance(data, dict) and "properties" in data:
            return data["properties"].get("Value", {}).get("value")
        return None
    finally:
        if own_session:
            pass


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Получить значения MetaModel из PMForesight MCP."
    )
    parser.add_argument("--all", action="store_true", help="Все известные ключи")
    parser.add_argument("--title", action="store_true", help="Title (титул системы)")
    parser.add_argument("--version", action="store_true", help="Version (версия Core)")
    parser.add_argument("--core-version", action="store_true", help="CoreVersion")
    parser.add_argument("--key", type=str, help="Любое произвольное имя записи")
    parser.add_argument("--json", action="store_true", help="Вывод в JSON формате")
    args = parser.parse_args()

    if not any([args.all, args.title, args.version, args.core_version, args.key]):
        parser.print_help()
        return 1

    if args.key:
        value = get_metamodel_value(args.key)
        result = {args.key: value}
    else:
        meta = get_metamodel_metadata()
        if args.title:
            result = {"title": meta.get("title")}
        elif args.version:
            result = {"version": meta.get("version")}
        elif args.core_version:
            result = {"core_version": meta.get("core_version")}
        else:  # --all
            result = meta

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for k, v in result.items():
            status = "✅" if v else "❌"
            print(f"  {status} {k}: {v!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
