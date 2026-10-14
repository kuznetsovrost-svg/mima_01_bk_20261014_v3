"""
build_report_header.py

Получение Name проекта по ProjectId + серверного времени для шапки отчёта.

Возвращает: dict с полями:
    - project_name:    str
    - project_code:    str
    - project_id:      int
    - server_time:     datetime  # в формате "YYYY-MM-DD HH:MM:SS"
    - server_time_src: str       # 'meta_model' | 'local' — откуда взято
    - server_time_str: str       # уже отформатированная строка
    - server_name:     str       # из serverInfo.name (PMForesight MCP)
    - server_version:  str       # из serverInfo.version
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import requests

# Импорт из mcp_config — централизованные URL, токен, headers, парсер SSE.
from mcp_config import (
    MCP_URL,
    META_TIME_KEYS,
    METAMODEL_ENTITY,
    METAMODEL_KEYS,
    PROJECT_BUDGET_VIEW,
    require_token,
    headers_for_call,
    parse_sse_response,
    McpConnectionError,
    mcp_init as _mcp_init_full,
    mcp_call as _mcp_call_full,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ИСКЛЮЧЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectNameNotFound(Exception):
    """Не удалось получить Name проекта по ProjectId."""
    pass


class ServerTimeUnavailable(Exception):
    """Не удалось получить серверное время ни одним способом."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# НИЗКОУРОВНЕВЫЙ MCP-ДОСТУП
# ═══════════════════════════════════════════════════════════════════════════════

def mcp_init() -> tuple[str, dict]:
    """Инициализация MCP-сессии. Возвращает (session_id, server_info).

    Обёртка над mcp_config.mcp_init с client_name="build_report_header"
    для идентификации в serverInfo.
    """
    return _mcp_init_full(client_name="build_report_header")


def mcp_call(sid: str, tool_name: str, arguments: dict, *, timeout: int = 60) -> Any:
    """Универсальный вызов MCP-инструмента. Обёртка над mcp_config.mcp_call."""
    return _mcp_call_full(sid, tool_name, arguments, timeout=timeout)


# ═══════════════════════════════════════════════════════════════════════════════
# ПОЛУЧЕНИЕ NAME ПРОЕКТА ПО PROJECTID
# ═══════════════════════════════════════════════════════════════════════════════

def get_project_name_by_id(project_id: int, sid: Optional[str] = None) -> dict:
    """
    Возвращает словарь с полями проекта.

    Использует get_entity_data(Project, data_id=project_id).
    """
    own_session = sid is None
    if own_session:
        sid, _ = mcp_init()

    try:
        data = mcp_call(
            sid, "get_entity_data",
            {"entityName": "Project", "data_id": str(project_id)},
        )

        if isinstance(data, dict) and "_error" in data:
            raise ProjectNameNotFound(
                f"get_entity_data(Project, {project_id}) → {data['_error'][:200]}"
            )

        properties = data.get("properties", {})

        name_field = properties.get("Name", {})
        name_value = name_field.get("value") or name_field.get("display")
        if not name_value:
            raise ProjectNameNotFound(
                f"у проекта ProjectId={project_id} нет поля Name"
            )

        code_field = properties.get("Code", {})
        code_value = code_field.get("value") or code_field.get("display")

        return {
            "ProjectId": project_id,
            "Code": code_value,
            "Name": name_value,
            "_raw": properties,
        }

    except requests.RequestException as e:
        raise ProjectNameNotFound(f"сетевая ошибка при запросе проекта: {e}") from e
    finally:
        if own_session:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# ПОЛУЧЕНИЕ СЕРВЕРНОГО ВРЕМЕНИ
# ═══════════════════════════════════════════════════════════════════════════════

def _try_metamodel_time(sid: str) -> Optional[datetime]:
    """Пытается достать системное время Форсайт через MetaModel.

    ⚠️ DEPRECATED 2026-08-07: В MetaModel нет серверного времени.
    Все ключи в META_TIME_KEYS возвращают "Запись не найдена".
    Оставлено для fallback'а если сервер изменится.

    Использует find_entity (старый API), но MetaModel по факту
    не индексируется в find_entity. Возвращает None.
    """
    for key in META_TIME_KEYS:
        try:
            data = mcp_call(
                sid, "find_entity",
                {"entityName": "MetaModel", "query": key, "limit": 1},
            )
        except requests.RequestException:
            continue

        if isinstance(data, dict) and "_error" in data:
            logger.debug("MetaModel[%s] isError: %s", key, data["_error"][:100])
            continue

        records = data.get("data") if isinstance(data, dict) else None
        if not records:
            continue

        value = records[0].get("Value") or records[0].get("value")
        if not value:
            continue

        try:
            iso_str = value.replace("Z", "+00:00") if isinstance(value, str) else value
            return datetime.fromisoformat(iso_str)
        except (ValueError, AttributeError) as e:
            logger.debug("не удалось распарсить MetaModel[%s]=%r: %s", key, value, e)
            continue

    return None


def _get_metamodel_value(sid: str, key_alias: str) -> Optional[str]:
    """Достаёт значение из MetaModel по алиасу (title/version/core_version).

    Использует рабочий API — get_entity_data(METAMODEL_ENTITY, data_id=<Key>).
    После live-проверки 2026-08-07 это единственный надёжный путь к MetaModel:
      - entityName = "metamodel" (lowercase, НЕ "MetaModel")
      - data_id принимает строку (например, "Title")
      - Ответ: properties.Value.value — нужное значение

    Args:
        sid: mcp-session-id из mcp_init().
        key_alias: одно из "title", "version", "core_version"
                  (разрешается через METAMODEL_KEYS).

    Returns:
        str — значение поля Value, или None если запись не найдена.
    """
    pk = METAMODEL_KEYS.get(key_alias)
    if not pk:
        logger.warning("Unknown metamodel key alias: %s", key_alias)
        return None

    try:
        data = mcp_call(
            sid, "get_entity_data",
            {"entityName": METAMODEL_ENTITY, "data_id": pk},
        )
    except requests.RequestException as e:
        logger.warning("network error getting metamodel[%s]: %s", pk, e)
        return None

    if isinstance(data, dict) and "_error" in data:
        logger.debug("metamodel[%s] error: %s", pk, data["_error"][:100])
        return None

    properties = data.get("properties", {}) if isinstance(data, dict) else {}
    value_field = properties.get("Value", {})
    return value_field.get("value") or value_field.get("display")


def get_project_budget_summary(project_id: int, sid: Optional[str] = None) -> dict:
    """Финансовая сводка по проекту через ProjectBudgetCompleteBusiness.

    Использует открытый view ProjectBudgetCompleteBusiness, который содержит
    ВСЕ: budgetsum, акты (план/факт/прогноз), оплаты (план/факт/прогноз),
    привязку к контракту, КТ и датам. Решает проблемы 1.3, 1.5, 1.7 из
    "Вопросы по MCP 2026_08_07.md".

    Args:
        project_id: ProjectId (= ActivityId в view).
        sid: (опц.) уже открытая MCP-сессия.

    Returns:
        dict: сводка с полями budgetsum/actplansum/factsum/forecastsum,
        payplansum/factsum/forecastsum, contract_ids, row_count, balance.
        Все поля — None если view недоступен или проекта нет.
    """
    own_session = sid is None
    if own_session:
        sid, _ = mcp_init()

    try:
        data = mcp_call(
            sid, "get_view",
            {
                "entityName": "Project",
                "viewName": PROJECT_BUDGET_VIEW,
                "limit": 2000,
            },
        )
        if not isinstance(data, dict) or "data" not in data:
            return {"available": False}

        rows = [r for r in data["data"] if r.get("ActivityId") == project_id]
        if not rows:
            return {"available": True, "rows_count": 0}

        def _sum(key):
            return sum(float(r.get(key) or 0) for r in rows)

        contract_ids = sorted({
            int(r["contractid"]) for r in rows
            if r.get("contractid")
        })

        return {
            "available": True,
            "rows_count": len(rows),
            "budgetsum": _sum("budgetsum"),
            "actplansum": _sum("actplansum"),
            "actforecastsum": _sum("actforecastsum"),
            "actfactsum": _sum("actfactsum"),
            "payplansum": _sum("payplansum"),
            "payforecastsum": _sum("payforecastsum"),
            "payfactsum": _sum("payfactsum"),
            "contract_ids": contract_ids,
            "contract_count": len(contract_ids),
        }
    except Exception as e:
        logger.debug("get_project_budget_summary failed: %s", e)
        return {"available": False, "error": str(e)}
    finally:
        if own_session:
            pass


def get_metamodel_metadata(sid: Optional[str] = None) -> dict:
    """Собирает метаданные из MetaModel (title, version, core_version).

    Используется для технических строк отчёта (раздел 7 «Тех. данные»).
    Все 3 ключа опциональны — если запись не найдена, поле = None.

    Args:
        sid: (опц.) уже открытая MCP-сессия.

    Returns:
        dict: {"title": str|None, "version": str|None, "core_version": str|None}.
    """
    own_session = sid is None
    if own_session:
        sid, _ = mcp_init()

    try:
        return {
            "title": _get_metamodel_value(sid, "title"),
            "version": _get_metamodel_value(sid, "version"),
            "core_version": _get_metamodel_value(sid, "core_version"),
        }
    finally:
        if own_session:
            pass


def get_server_time(sid: Optional[str] = None, server_info: Optional[dict] = None) -> tuple[datetime, str, str, str]:
    """
    Возвращает серверное время + метаданные.

    Args:
        sid: (опц.) уже открытая MCP-сессия.
        server_info: (опц.) serverInfo из предыдущего handshake, чтобы
                     не делать второй initialize.

    Returns:
        tuple[datetime, str, str, str]:
            - server_time:    datetime с TZ
            - source:         'meta_model' | 'local'
            - server_name:    из MCP serverInfo.name
            - server_version: из MCP serverInfo.version
    """
    own_session = sid is None
    if own_session:
        sid, server_info = mcp_init()
    elif server_info is None:
        try:
            _, server_info = mcp_init()
        except Exception:
            server_info = {}

    server_name = server_info.get("name", "PMForesight MCP")
    server_version = server_info.get("version", "3.2.4")

    try:
        meta_time = _try_metamodel_time(sid)
        if meta_time is not None:
            logger.info("серверное время из MetaModel: %s", meta_time.isoformat())
            return meta_time, "meta_model", server_name, server_version

        local_time = datetime.now(timezone.utc).astimezone()
        logger.warning(
            "серверное время недоступно через MetaModel, "
            "используем локальное: %s", local_time.isoformat()
        )
        return local_time, "local", server_name, server_version

    finally:
        if own_session:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# ФОРМАТИРОВАНИЕ
# ═══════════════════════════════════════════════════════════════════════════════

def format_server_time(dt: datetime) -> str:
    """Возвращает время в формате 'YYYY-MM-DD HH:MM:SS'."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ — ЗАГОЛОВОК ОТЧЁТА
# ═══════════════════════════════════════════════════════════════════════════════

def build_report_header(project_id: int) -> dict:
    """
    Собирает шапку отчёта: Name проекта, серверное время, метаданные MCP.
    """
    sid, server_info = mcp_init()

    project = get_project_name_by_id(project_id, sid=sid)
    project_name = project["Name"]
    project_code = project.get("Code")

    server_time, time_source, srv_name, srv_version = get_server_time(
        sid=sid, server_info=server_info
    )

    if not srv_name:
        srv_name = server_info.get("name", "PMForesight MCP")
    if not srv_version:
        srv_version = server_info.get("version", "3.2.4")

    setup = {
        "project_id": project_id,
        "project_code": project_code,
        "project_name": project_name,
        "server_time": server_time,
        "server_time_str": format_server_time(server_time),
        "server_time_src": time_source,
        "server_name": srv_name,
        "server_version": srv_version,
    }

    # Дополнительно — метаданные из MetaModel (титул системы, версия Core).
    # Используются в разделе 7 «Тех. данные» отчёта.
    try:
        meta = get_metamodel_metadata(sid=sid)
        setup["metamodel_title"] = meta.get("title")
        setup["metamodel_version"] = meta.get("version")
        setup["metamodel_core_version"] = meta.get("core_version")
    except Exception as e:
        logger.debug("не удалось собрать metamodel метаданные: %s", e)
        setup["metamodel_title"] = None
        setup["metamodel_version"] = None
        setup["metamodel_core_version"] = None

    # Финансовая сводка через ProjectBudgetCompleteBusiness.
    # Используется в разделе 4 показатель 5 (график платежей) и разделе 6.
    try:
        budget = get_project_budget_summary(project_id, sid=sid)
        # Не перезаписываем уже установленный project_id (он int), только дополняем
        setup["budget"] = budget
    except Exception as e:
        logger.debug("не удалось собрать финансовую сводку: %s", e)
        setup["budget"] = {"available": False}

    return setup


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) != 2:
        print("Использование: python build_report_header.py <ProjectId>")
        print("Пример:        python build_report_header.py 4595")
        sys.exit(1)

    try:
        pid = int(sys.argv[1])
    except ValueError:
        print(f"❌ ProjectId должен быть целым числом, получено '{sys.argv[1]}'")
        sys.exit(2)

    print(f"\nСобираем заголовок отчёта для ProjectId={pid}…\n")

    try:
        header = build_report_header(pid)
    except ProjectNameNotFound as e:
        print(f"❌ Проект не найден: {e}")
        sys.exit(3)
    except ServerTimeUnavailable as e:
        print(f"⚠️  Время сервера недоступно: {e}")
        header = None

    if header:
        print("✅ Заголовок отчёта:")
        print(f"   ProjectId:      {header['project_id']}")
        print(f"   Code:           {header['project_code']}")
        print(f"   Name:           {header['project_name']}")
        print(f"   ServerTime:     {header['server_time_str']}")
        print(f"   ServerTimeSrc:  {header['server_time_src']}")
        print(f"   MCP Server:     {header['server_name']} v{header['server_version']}")
        meta = header.get("metamodel_title") or "—"
        core = header.get("metamodel_core_version") or "—"
        print(f"   MCPSystemTitle: {meta}")
        print(f"   MCPCoreVersion: {core}")

        # Финансовая сводка (если доступна)
        budget = header.get("budget", {})
        if budget.get("available"):
            print(f"   --- Финансы (ProjectBudgetCompleteBusiness) ---")
            print(f"   Rows:          {budget.get('rows_count', 0)}")
            print(f"   Contracts:     {budget.get('contract_count', 0)}")
            print(f"   ActPlan:       {budget.get('actplansum', 0):>15,.2f} ₽")
            print(f"   ActFact:       {budget.get('actfactsum', 0):>15,.2f} ₽")
            print(f"   PayPlan:       {budget.get('payplansum', 0):>15,.2f} ₽")
            print(f"   PayFact:       {budget.get('payfactsum', 0):>15,.2f} ₽")
            ba = budget.get("actfactsum", 0) - budget.get("payfactsum", 0)
            print(f"   Balance:       {ba:>15,.2f} ₽")
        elif budget.get("available") is False:
            print(f"   Budget:        недоступно ({budget.get('error', '?')})")
