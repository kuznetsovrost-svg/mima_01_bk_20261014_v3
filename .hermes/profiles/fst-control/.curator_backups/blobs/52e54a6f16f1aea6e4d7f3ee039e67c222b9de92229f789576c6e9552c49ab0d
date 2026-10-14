__version__ = "1.0.19"
"""
run_all.py — единый оркестратор отчётов по скиллу fst-project-health.

Принимает ТОЛЬКО project_code (например, 503-434) и автоматически:
1. Находит ProjectId через MyProject + AllProject
2. Скачивает данные проекта → /tmp/proj_<code>.json
3. Строит все секции 3-8 → /tmp/section_*_result.md
4. Склеивает → /tmp/project_<code>_report.md
5. Генерирует → /tmp/project_<code>_report.html + WORD (опционально)

Оптимизации (2026-08-08, live-benchmark):
- **Level 1**: Одна MCP-сессия для всего pipeline (было 9 → 2 init).
- **Level 1**: Кэш `AllMyPoint?ProjectId=<id>` (702 → ~30 строк) — экономит ~3 сек.
- **Level 3**: In-process вызов build_html_report.main() и build_word_report.main().
- **Level 4**: Кэш `/tmp/.cache_<code>.json` (TTL=5 мин) — между повторными запусками.

Использование:
    python3 scripts/run_all.py --code 503-434
    python3 scripts/run_all.py --code 504-595 --no-word
"""
import sys
import argparse
import json
import importlib.util
import time
from pathlib import Path
from datetime import datetime

# SKILL_DIR определяется относительно местоположения этого файла (для переносимости).
# Скилл можно перенести на другой сервер — путь подстроится автоматически.
SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mcp_config import (
    mcp_init, mcp_call, parse_sse_response,
    ALL_MY_POINT_VIEW, ALL_MY_POINT_FILTERS,
    PROJECT_BUDGET_VIEW,
    PROJECT_RESOURCE_PLAN_VIEW,
    PROJECT_HEALTH_COST_MY_VIEW, PROJECT_HEALTH_COST_MY_FILTERS,
)


# === Кэш между запусками (Level 4) ===
CACHE_DIR = Path("/tmp")
CACHE_TTL_SEC = 300  # 5 минут


def cache_key_path(code: str) -> Path:
    return CACHE_DIR / f".cache_run_all_{code}.json"


def cache_get(code: str) -> dict | None:
    """Возвращает кэш если свежий (TTL=5 мин), иначе None."""
    p = cache_key_path(code)
    if not p.exists():
        return None
    age = time.time() - p.stat().st_mtime
    if age > CACHE_TTL_SEC:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def cache_put(code: str, data: dict) -> None:
    p = cache_key_path(code)
    p.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")


# === MCP-сессия (Level 1) ===
_pipeline_sid = None


def get_pipeline_sid() -> str:
    """Один сид на весь pipeline — инициализируется lazily."""
    global _pipeline_sid
    if _pipeline_sid is None:
        _pipeline_sid, _ = mcp_init(client_name="run-all-pipeline")
    return _pipeline_sid


def load(name: str, fname: str):
    """Загружает модуль из файла с именем, содержащим дефисы."""
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS / fname))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def find_project(code: str) -> dict:
    """Находит проект по code через MyProject + AllProject (pitfall #1)."""
    sid = get_pipeline_sid()
    seen = {}
    for view_name in ("MyProject", "AllProject"):
        resp = mcp_call(sid, "get_view",
                        {"entityName": "Project", "viewName": view_name, "limit": 1000})
        for r in resp.get("data", []):
            cid = str(r.get("Code", "")).strip()
            if cid and cid not in seen:
                seen[cid] = r
    target = seen.get(code)
    if not target:
        raise SystemExit(f"❌ Проект {code!r} не найден. Известно: {len(seen)} проектов")
    pid = target.get("ProjectId") or target.get("id")
    return {
        "code": code,
        "name": (target.get("Name") or "").strip(),
        "project_id": int(pid),
        "indicator": target.get("IndicatorTitle", ""),
        "phase": target.get("ActivityPhaseName", ""),
    }


def save_project_json(project: dict) -> Path:
    """Сохраняет /tmp/proj_<code>.json — данные проекта для build_html_report.py."""
    sid = get_pipeline_sid()
    proj_data = mcp_call(sid, "get_entity_data",
                         {"entityName": "Project", "data_id": str(project["project_id"])})
    properties = proj_data.get("properties", {})

    flat = {}
    for key, val in properties.items():
        if isinstance(val, dict) and "value" in val:
            v = val["value"]
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                flat[key] = v[0].get("display", str(v[0].get("id", "")))
            elif isinstance(v, list):
                flat[key] = v
            else:
                flat[key] = v
        else:
            flat[key] = val
    flat.update({
        "ProjectId": project["project_id"],
        "Code": project["code"],
        "Name": project["name"],
    })

    out = Path(f"/tmp/proj_{project['code']}.json")
    out.write_text(json.dumps(flat, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def parse_date(s):
    if not s: return None
    try: return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except: return None


# === Кэш AllMyPoint (Level 1) ===
def load_project_points(project: dict) -> list[dict]:
    """Загружает КТ проекта через фильтр `filters={ProjectId}` (702 → ~30 строк).

    fix 2026-09-01: переход на стандартный формат filters.
    """
    sid = get_pipeline_sid()
    all_points = []
    offset = 0
    page_size = 3000
    while True:
        resp = mcp_call(sid, "get_view",
                        {"entityName": "Point",
                         "viewName": ALL_MY_POINT_VIEW,
                         "filters": ALL_MY_POINT_FILTERS(project["project_id"]),
                         "limit": page_size, "offset": offset})
        rows = resp.get("data", [])
        if not rows:
            break
        all_points.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return all_points


def build_section_3(project: dict, points_cache: list[dict] | None = None) -> None:
    """Строит /tmp/section_3_result.md — сроки КТ.

    fix 2026-08-21: класс тяжести замечания теперь учитывает реальную просрочку.
    """
    thr_remark = load("thr_remark", "point-timing-remark-thresholds.py")
    thr_health = load("thr_health", "point-timing-health-thresholds.py")
    from datetime import date
    today = date.today()

    if points_cache is None:
        points_cache = load_project_points(project)
    project_points = [p for p in points_cache
                      if str(p.get("ParentCode", "")).strip() == project["code"]]

    remarks = []
    for p in project_points:
        pd = parse_date(p.get("PlanDate"))
        fd = parse_date(p.get("ForecastDate"))
        fact = parse_date(p.get("FactDate"))
        if not pd or not fd or fact or pd == fd:
            continue
        diff = (fd - pd).days
        # Реальная просрочка от сегодня (fix 2026-08-21)
        overdue_days = max(0, (today - pd).days) if pd < today else 0
        abs_diff = abs(diff)
        # Приоритет — реальная просрочка от сегодня
        if overdue_days >= 30 or abs_diff > thr_remark.REMARK_THRESHOLDS["critical"]["min_diff_days"]:
            color, status = "Красный", "Критическое"
        elif overdue_days >= 14 or abs_diff > thr_remark.REMARK_THRESHOLDS["substantial"]["min_diff_days"]:
            color, status = "Желтый", "Существенное"
        else:
            color, status = "Синий", "Информационное"
        remarks.append({
            "code": p.get("Code") or p.get("PointCode") or "",
            "name": p.get("Name") or p.get("PointName") or "",
            "plan": pd.isoformat(), "forecast": fd.isoformat(),
            "diff_days": diff, "color": color, "status": status,
            "owner": (p.get("OwnerName") or p.get("OwnerId") or "").strip(),
        })

    critical = sum(1 for r in remarks if r["status"] == "Критическое")
    warning = sum(1 for r in remarks if r["status"] == "Существенное")
    info = sum(1 for r in remarks if r["status"] == "Информационное")

    if critical >= thr_health.HEALTH_THRESHOLDS["sick"]["min_critical_count"]:
        verdict = "Болен"
    elif (warning >= thr_health.HEALTH_THRESHOLDS["attention"]["min_critical_count"] or
          critical >= thr_health.HEALTH_THRESHOLDS["attention"]["min_critical_count"]):
        verdict = "Требует внимания"
    else:
        verdict = "Здоров"

    text = f"""## 3. Замечания по срокам

**Вердикт раздела:** {verdict}
**Критических:** {critical}, **существенных:** {warning}, **информационных:** {info}

"""
    if remarks:
        text += """| # | Цвет | Статус | Код | Наименование | План | Прогноз | Факт | Исполнитель |
|---|------|--------|-----|--------------|------|---------|------|-------------|
"""
        for i, r in enumerate(remarks, 1):
            text += f"| {i} | {r['color']} | {r['status']} | {r['code']} | {r['name']} | {r['plan']} | {r['forecast']} | — | {r['owner']} |\n"
    else:
        text += "_Нет замечаний._\n"
    text += f"\n**Итог по замечаниям:** {critical} критических, {warning} существенных, {info} информационных\n"

    Path("/tmp/section_3_result.md").write_text(text, encoding="utf-8")


def build_section_4(project: dict, props_cache: dict | None = None) -> None:
    """Строит /tmp/section_4_result.md — полнота заполнения."""
    sid = get_pipeline_sid()

    if props_cache is None:
        proj_data = mcp_call(sid, "get_entity_data",
                             {"entityName": "Project", "data_id": str(project["project_id"])})
        props = proj_data.get("properties", {})
    else:
        props = props_cache

    # 1. Куратор
    owner = props.get("OwnerId") or {}
    ov = owner.get("value")
    if not ov:
        p1_r, p1_d = "Нет", "Куратор не назначен"
    else:
        first = ov[0] if isinstance(ov, list) and ov else ov
        p1_r = "Да"
        p1_d = first.get("display", "").strip() if isinstance(first, dict) else f"id={first}"

    # 2. РП
    leader = props.get("LeaderId") or {}
    lv = leader.get("value")
    if not lv:
        p2_r, p2_d = "Нет", "РП не назначен"
    else:
        first = lv[0] if isinstance(lv, list) and lv else lv
        p2_r = "Да"
        p2_d = first.get("display", "").strip() if isinstance(first, dict) else f"id={first}"

    # 3. Паспорт — phase_num >= 2 (pitfall #1: стадия Инициирование+ обязывает паспорт)
    phase_name = props.get("ActivityPhaseName", {}).get("value") or ""
    PHASES = {1: ["Пресейл"], 2: ["Инициирование"], 3: ["Подготовка"], 4: ["Реализация"], 5: ["Завершение"], 6: ["Архив"]}
    phase_num = 1
    for num, names in PHASES.items():
        if phase_name in names:
            phase_num = num
            break
    phase_requires_passport = phase_num >= 2
    passport = props.get("Passport") or {}
    pv = passport.get("value")
    if pv:
        p3_r = "Да"
        p3_d = f"Стадия ЖЦ: {phase_name}"
    elif phase_requires_passport:
        p3_r = "Нет"
        p3_d = f"Стадия ЖЦ: {phase_name} (паспорт не прикреплён)"
    else:
        p3_r = "Да"
        p3_d = f"Стадия ЖЦ: {phase_name} (Пресейл — паспорт необязателен)"

    # 4. Трудозатраты через get_project_effort
    EFFORT = load("EFFORT", "get_effort.py")
    try:
        eff_summary = EFFORT.get_project_effort(
            project_code=project["code"], project_id=project["project_id"], sid=sid
        )
        plan = eff_summary.plan_hours
        forecast = eff_summary.forecast_hours
        fact = eff_summary.fact_hours
        if plan + forecast + fact > 0:
            p4_r = "Да"
            p4_d = f"{plan:.2f}ч план, {forecast:.2f}ч прогноз, {fact:.2f}ч факт"
        else:
            p4_r = "Неопределено"
            p4_d = "Нет данных о трудозатратах"
    except Exception as e:
        p4_r = "Неопределено"
        p4_d = f"Ошибка: {e}"

    # 5. Финансы через get_project_budget
    BUDGET = load("BUDGET", "get_project_budget.py")
    try:
        budget_summary = BUDGET.get_project_budget(
            project_code=project["code"], project_id=project["project_id"], sid=sid
        )
        if budget_summary.rows:
            p5_r = "Да"
            delta = budget_summary.balance()
            contract_count = len(budget_summary.contract_ids)
            p5_d = f"Σ актов = {budget_summary.actfactsum:.2f} ₽, Σ оплат = {budget_summary.payfactsum:.2f} ₽, Δ = {delta:.2f} ₽ ({contract_count} контракт(ов))"
        else:
            p5_r = "Неопределено"
            p5_d = "Нет данных"
    except Exception as e:
        p5_r = "Неопределено"
        p5_d = f"Ошибка: {e}"

    data = {
        "p1": {"result": p1_r, "detail": p1_d},
        "p2": {"result": p2_r, "detail": p2_d},
        "p3": {"result": p3_r, "detail": p3_d},
        "p4": {"result": p4_r, "detail": p4_d},
        "p5": {"result": p5_r, "detail": p5_d},
    }
    Path("/tmp/section_4_data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if p3_r == "Нет" or p4_r == "Неопределено":
        verdict = "Требует внимания"
    else:
        verdict = "Здоров"

    text = f"""## 4. Полнота заполнения

**Вердикт раздела:** {verdict}

| # | Показатель | Результат | Детализация | Статус |
|---|------------|-----------|-------------|--------|
| 1 | Куратор назначен | {p1_r} | {p1_d} | {'Норма' if p1_r == 'Да' else 'Существенное'} |
| 2 | РП назначен | {p2_r} | {p2_d} | {'Норма' if p2_r == 'Да' else 'Существенное'} |
| 3 | Паспорт проекта заполнен | {p3_r} | {p3_d} | {'Норма' if p3_r == 'Да' else 'Существенное'} |
| 4 | Актуальность трудозатрат | {p4_r} | {p4_d} | {'Норма' if p4_r == 'Да' else 'Неопределено' if p4_r == 'Неопределено' else 'Существенное'} |
| 5 | Корректность графика платежей | {p5_r} | {p5_d} | {'Норма' if p5_r == 'Да' else 'Существенное'} |

**Итог по замечаниям:** 0 критических, 0 существенных, 0 информационных

### Детали по показателю 4 (Трудозатраты)
{p4_d}

### Детали по показателю 5 (Финансы)
{p5_d}
"""
    Path("/tmp/section_4_result.md").write_text(text, encoding="utf-8")


def build_section_5(project: dict, points_cache: list[dict] | None = None) -> None:
    """Строит /tmp/section_5_result.md — актуальность прогнозов.

    fix 2026-08-21 (пользовательская корректировка):
    Актуальность прогнозов проверяется ТОЛЬКО по сравнению ПРОГНОЗНОЙ даты
    и текущей даты. PlanDate НЕ участвует в расчёте просрочки.

    Правила:
    - Если forecast_date < today И fact_date is None → ПРОСРОЧЕНО
      overdue_days = today - forecast_date (целых дней)
    - Если forecast_date >= today → НЕ просрочено, ВЫВОДИТЬ НЕ НУЖНО
    - Если fact_date есть → работа закрыта фактически, ВЫВОДИТЬ НЕ НУЖНО
    - diff_days (forecast - plan) НЕ ИМЕЕТ значения для просрочки

    Класс тяжести по размеру просрочки:
      overdue_days >= 30        → Критическое
      overdue_days >= 14        → Существенное
      overdue_days >= 1         → Информационное
    """
    thr = load("thr", "point-timing-health-thresholds.py")
    from datetime import date
    today = date.today()

    def classify_relevance(overdue_days: int) -> str:
        """Классифицирует КТ по размеру просрочки прогноза."""
        if overdue_days >= 30:
            return "Критическое"
        if overdue_days >= 14:
            return "Существенное"
        if overdue_days >= 1:
            return "Информационное"
        return "Норма"

    if points_cache is None:
        points_cache = load_project_points(project)
    project_points = [p for p in points_cache
                      if str(p.get("ParentCode", "")).strip() == project["code"]]

    overdue = []
    for p in project_points:
        # PlanDate больше не нужен для просрочки, но может пригодиться
        # для информации в строке.
        pd = parse_date(p.get("PlanDate"))
        # ForecastDate — это и есть та дата, которая сравнивается с today.
        fd = parse_date(p.get("ForecastDate"))
        fact = parse_date(p.get("FactDate"))

        # Фильтр: работа закрыта фактической датой → не показываем
        if fact:
            continue
        # Фильтр: нет прогнозной даты → не показываем
        if not fd:
            continue

        # ГЛАВНАЯ ЛОГИКА: прогнозная дата < today = просрочено
        # Прогнозная дата >= today = НЕ просрочено → НЕ выводим
        if fd >= today:
            continue  # прогноз ещё не наступил, строк не должно быть в таблице

        # overdue_days — это (today - forecast_date)
        overdue_days = (today - fd).days
        cls = classify_relevance(overdue_days)
        if cls == "Норма":
            # overdue_days == 0, но мы уже отфильтровали fd < today, так что
            # этот случай на самом деле не должен случаться. На всякий случай:
            continue

        overdue.append({
            "Code": p.get("Code") or "",
            "Name": p.get("Name") or "",
            "PlanDate": pd.isoformat() if pd else "",
            "ForecastDate": fd.isoformat(),
            "FactDate": "",
            "diff_days": 0,  # больше не используется
            "overdue_days": overdue_days,
            "color": {"Критическое": "Красный", "Существенное": "Желтый"}.get(cls, "Синий"),
            "status": cls,
            "Responsible": (p.get("OwnerName") or p.get("OwnerId") or "").strip(),
        })

    critical = sum(1 for o in overdue if o["status"] == "Критическое")
    warning = sum(1 for o in overdue if o["status"] == "Существенное")
    info = sum(1 for o in overdue if o["status"] == "Информационное")

    if critical >= thr.HEALTH_THRESHOLDS["sick"]["min_critical_count"]:
        verdict = "Болен"
    elif (warning >= thr.HEALTH_THRESHOLDS["attention"]["min_critical_count"] or
          critical >= thr.HEALTH_THRESHOLDS["attention"]["min_critical_count"]):
        verdict = "Требует внимания"
    else:
        verdict = "Здоров"

    data = {
        "health": verdict,
        "counts": {"Критическое": critical, "Существенное": warning, "Информационное": info},
        "overdue": overdue,
    }
    Path("/tmp/section_5_data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    text = f"""## 5. Актуальность прогнозов

**Вердикт раздела:** {verdict}
**Критических:** {critical}, **существенных:** {warning}, **информационных:** {info}

"""
    if overdue:
        text += """| # | Цвет | Статус | Код КТ | Название | План | Прогноз | Дней |
|---|------|--------|--------|----------|------|---------|------|
"""
        for i, o in enumerate(overdue, 1):
            # overdue_days = today - forecast_date (просрочка прогноза)
            overdue_str = str(o['overdue_days'])
            text += f"| {i} | {o['color']} | {o['status']} | {o['Code']} | {o['Name']} | {o['PlanDate']} | {o['ForecastDate']} | {overdue_str} |\n"
    text += f"\n**Итог по замечаниям:** {critical} критических, {warning} существенных, {info} информационных\n"
    Path("/tmp/section_5_result.md").write_text(text, encoding="utf-8")


def build_section_6_indicators(project: dict) -> None:
    """Строит /tmp/section_6_indicators_result.md — 16 показателей проекта.

    Секция «Показатели проекта» v1.0.0:
    6.1 Юрлицо, 6.2 ЖЦ, 6.3 Прогнозы ТРЗ, 6.4 Плановые ТРЗ,
    6.5 Перегрузка в проекте, 6.6 Роли в прошлом, 6.7 Перегрузка по всем активностям,
    6.8 Сроки фин. КТ, 6.9 Суммы актов/оплат, 6.10 Прямые затраты,
    6.11 НДС, 6.12 Сумма НДС расчётная, 6.13 Бюджет проекта/пресейла,
    6.14 Расход лимита пресейла, 6.15 Утв. бюджет, 6.16 Метки КП.

    Подкраска строки: critical=#fee2e2, substantial=#fef3c7,,
                       informational=#dbeafe, normal=#fff.
    Колонка «Детали» — кнопка ▼ с вложенной таблицей.
    """
    sid = get_pipeline_sid()

    # Запускаем все 16 индикаторов через единый модуль
    from project_indicators import run_all_indicators, compute_section_verdict
    results = run_all_indicators(project, sid)
    section_verdict = compute_section_verdict(results)

    # Сохраняем данные в JSON для build_html_report.py
    data = {
        "section_verdict": section_verdict.verdict,  # str (через __str__)
        "section_counts": section_verdict.counts,
        "indicators": [
            {
                "number": r.number,
                "name": r.name,
                "result": r.result,
                "detail": r.detail,
                "verdict": r.verdict,
                "table": r.table,
                "table_title": r.table_title,
            }
            for r in results
        ],
    }
    Path("/tmp/section_6_indicators_data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # Формируем Markdown
    lines = ["## 6. Показатели проекта", ""]
    lines.append(f"**Вердикт раздела:** {section_verdict.verdict}")
    lines.append("")

    # Главная таблица (4 колонки: #, Показатель, Результат, Детали)
    lines.append("| # | Показатель | Результат | Детали |")
    lines.append("|---|------------|-----------|--------|")
    for r in results:
        # Короткое название для экономили места
        short_name = r.name
        if len(short_name) > 50:
            short_name = short_name[:47] + "..."
        # Если строка без ▼ — нет вложенной таблицы
        details_icon = "▼" if r.table else ""
        # v1.0.19: вердикт каждого показателя вшит в MD как HTML-комментарий —
        # это позволяет build_html_report.py парсить раздел 6 без обращения
        # к локальному JSON. Снапшот MD становится самодостаточным.
        # Комментарий размещён ВНУТРИ последней ячейки таблицы, чтобы не
        # ломать парсер pipe-table (он идёт по строкам, начинающимся с "|").
        verdict_comment = f"<!-- 6.{r.number} verdict=\"{r.verdict}\" -->"
        lines.append(f"| 6.{r.number} | {short_name} | {r.result} | {details_icon} {verdict_comment} |")

    lines.append("")

    # Вложенные таблицы (для каждого индикатора где есть ▼)
    for r in results:
        if not r.table:
            continue
        lines.append(f"### 6.{r.number} {r.name}")
        if r.table_title:
            lines.append(f"*{r.table_title}*")
        lines.append("")

        # Определяем колонки вложенной таблицы по первому row
        first_row = r.table[0]
        headers = [k for k in first_row.keys() if k not in ("severity", "n")]
        if "n" in first_row:
            headers = ["n"] + headers
        # Убираем дубликаты, сохраняем порядок
        seen = set()
        unique_headers = []
        for h in headers:
            if h not in seen:
                seen.add(h)
                unique_headers.append(h)
        headers = unique_headers

        # Заголовки
        lines.append("| " + " | ".join(_format_col_header(h) for h in headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")

        # Строки
        for row in r.table:
            cells = []
            for h in headers:
                v = row.get(h, "")
                # Преобразуем в строку, обрезаем длинные
                s = str(v) if v is not None else ""
                if len(s) > 80:
                    s = s[:77] + "..."
                cells.append(s)
            # v1.0.19: severity каждой строки вложенной таблицы — в HTML-комментарии
            # ВНУТРИ последней ячейки (отдельной строкой нельзя — сломает pipe-table).
            sev = row.get("severity", "normal")
            sev_comment = f"<!-- 6.{r.number} severity=\"{sev}\" -->"
            # Если есть колонки — добавляем комментарий в последнюю.
            # Пустая таблица (без колонок) нам не грозит, т.к. headers уже >0.
            if cells:
                cells[-1] = f"{cells[-1]} {sev_comment}"
            lines.append("| " + " | ".join(cells) + " |")

        lines.append("")

    # Итог
    # v1.0.19: маппинг русских verdict'ов на английские ключи (Критическое→critical и т.д.),
    # иначе severity_counts выглядит как «все норма» из-за if-r.verdict-in-keys.
    severity_counts = {"critical": 0, "substantial": 0, "informational": 0, "normal": 0}
    verdict_to_sev = {
        "Критическое": "critical",
        "Существенное": "substantial",
        "Информационное": "informational",
        "Норма": "normal",
    }
    for r in results:
        sev_key = verdict_to_sev.get(r.verdict, "normal")
        severity_counts[sev_key] += 1

    lines.append("**Итог по замечаниям:**")
    lines.append(f"- Критических: {severity_counts['critical']}")
    lines.append(f"- Существенных: {severity_counts['substantial']}")
    lines.append(f"- Информационных: {severity_counts['informational']}")
    lines.append(f"- Норма (нет замечаний): {severity_counts['normal']}")

    text = "\n".join(lines) + "\n"
    Path("/tmp/section_6_indicators_result.md").write_text(text, encoding="utf-8")


def _format_col_header(h: str) -> str:
    """Форматирует заголовок колонки (заменяет _ на пробел, capitalize)."""
    mapping = {
        "n": "#",
        "code": "Код",
        "type": "Тип",
        "name": "Наименование",
        "plan": "План",
        "forecast": "Прогноз",
        "diff": "Δ дн.",
        "severity": "Сев.",
        "period": "Период",
        "remark": "Примечание",
        "user": "ФИО",
        "year": "Год",
        "available": "Доступно",
        "overload": "Превышение",
        "percent": "%",
        "pointid": "PointID",
        "pointname": "Точка",
        "resource": "Ресурс",
        "unfilled_forecast": "Нереализованный прогноз",
    }
    return mapping.get(h.lower(), h.replace("_", " ").capitalize())


def build_section_6(project: dict) -> None:
    """Строит /tmp/section_6_result.md — финансовый статус.

    fix 2026-09-01: Использует стандартный формат filters={...} для get_view.
    Live-probe 2026-09-01: filters={ProjectId: 4595} → 1 строка за 1.4 сек.
    Старый формат ?ProjectId=<id> в URL больше не используется — ломается
    после изменений сервера.
    """
    sid = get_pipeline_sid()

    # Новый стандартный формат через filters
    resp = mcp_call(sid, "get_view",
                    {"entityName": "Project",
                     "viewName": PROJECT_HEALTH_COST_MY_VIEW,
                     "filters": PROJECT_HEALTH_COST_MY_FILTERS(project["project_id"]),
                     "limit": 100})
    rows = resp.get("data", [])
    project_row = rows[0] if rows else None

    finresult_thr = load("thr_finresult", "finresult-thresholds.py").FINRESULT_THRESHOLDS

    if not project_row:
        result = {"section_health": "Неопределено", "p1": {"result": "Нет", "detail": "Нет данных"}, "p2": {"result": "Нет", "detail": "Нет данных"}, "p3": {"result": "Нет", "detail": "Нет данных"}},
    else:
        forecast = project_row.get("forecast") or 0
        inplan = project_row.get("inplan") or 0
        infact = project_row.get("infact") or 0
        outplan = project_row.get("outplan") or 0
        outfact = project_row.get("outfact") or 0
        plan = project_row.get("plan") or 0
        fact = project_row.get("fact") or 0
        outallforecast = project_row.get("outallforecast") or 0
        deviation = project_row.get("deviation") or 0
        devcost = project_row.get("devcost") or 0
        devallcost = project_row.get("devallcost") or 0

        # 1. Прогноз фин.результата: forecast < 0 = убыток
        p1_ok = forecast < 0
        p1 = {"result": "Да" if p1_ok else "Нет",
              "detail": f"Прогноз фин.результата: {forecast:,.2f} ₽ — {'критическое замечание (убыток)' if p1_ok else 'норма'}"}

        # 2. Δ текущей стоимости от плана: |devcost| > 1 млн
        thr_devcost = finresult_thr["current_cost_deviation"]["max_value"]
        p2_ok = abs(devcost) > thr_devcost
        p2 = {"result": "Да" if p2_ok else "Нет",
              "detail": f"Δ текущей стоимости от плана: {devcost:,.2f} ₽ (порог: {thr_devcost:,.0f} ₽) — {'критическое замечание' if p2_ok else 'норма'}"}

        # 3. Δ прогноза от плана: |plan - outallforecast| > 2 млн
        thr_plan_forecast = finresult_thr["end_finresult_decrease"]["max_value"]
        plan_minus_forecast = abs((plan or 0) - (outallforecast or 0))
        p3_ok = plan_minus_forecast > thr_plan_forecast
        p3 = {"result": "Да" if p3_ok else "Неопределено",
              "detail": f"Δ прогноз/план: {plan_minus_forecast:,.2f} ₽ (порог: {thr_plan_forecast:,.0f} ₽) — {'критическое замечание' if p3_ok else 'норма'}"}

        critical_count = sum(1 for p in [p1, p2, p3] if p["result"] == "Да")
        if critical_count >= 2:
            verdict = "Болен"
        elif critical_count >= 1:
            verdict = "Требует внимания"
        else:
            verdict = "Здоров"

        result = {"section_health": verdict, "p1": p1, "p2": p2, "p3": p3}

    Path("/tmp/section_6_data.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    health = result["section_health"]
    p1, p2, p3 = result["p1"], result["p2"], result["p3"]

    text = f"""## 7. Финансовый статус

**Вердикт раздела:** {health}

| # | Показатель | Результат | Детализация |
|---|------------|-----------|-------------|
| 1 | Прогноз фин.результата < 0 | {p1['result']} | {p1['detail']} |
| 2 | Δ текущей стоимости от плана > 1 млн | {p2['result']} | {p2['detail']} |
| 3 | Δ прогноза от плана > 2 млн | {p3['result']} | {p3['detail']} |

"""
    critical = sum(1 for p in [p1, p2, p3] if p["result"] == "Да")
    text += f"**Итог по замечаниям:** {critical} критических, 0 существенных, 0 информационных\n"
    Path("/tmp/section_6_result.md").write_text(text, encoding="utf-8")


def build_section_7(project: dict) -> None:
    """Строит /tmp/section_7_result.md — технические данные.

    Формат (по эталону 26, 2026-08-07):
    1. Пользователь
    2. Титул системы
    3. URL MCP-сервера
    4. Версия скилла
    5. Версия MCP
    6. Версия Core (ПМ «Форсайт»)
    """
    META = load("META", "get_metamodel.py")
    from mcp_config import MCP_URL
    sid = get_pipeline_sid()
    data = META.get_metamodel_metadata(sid=sid)
    Path("/tmp/section_7_data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # 1. Пользователь — из JWT-токена (пользователь, от имени которого
    # строится отчёт, а НЕ владелец проекта).
    from mcp_config import get_current_user_from_token
    user = get_current_user_from_token()

    # 2. Титул системы — с одинарными кавычками как в эталоне
    title = data.get("title") or "—"
    if title and title != "—":
        title_display = f"'{title}'"
    else:
        title_display = title

    # 4. Версия скилла — фиксированная (по эталону 26)
    skill_version = "0.3.0 (V2-build)"

    # 5. Версия MCP — из MetaModel
    mcp_version = data.get("version") or "—"

    # 6. Версия Core (ПМ «Форсайт»)
    core_version = data.get("core_version") or "—"

    text = f"""## 8. Технические данные

| # | Показатель | Значение |
|---|------------|----------|
| 1 | Пользователь | {user} |
| 2 | Титул системы | {title_display} |
| 3 | URL MCP-сервера | {MCP_URL} |
| 4 | Версия скилла | {skill_version} |
| 5 | Версия MCP | {mcp_version} |
| 6 | Версия Core (ПМ «Форсайт») | {core_version} |

**Итог по замечаниям:** 0 критических, 0 существенных, 0 информационных (справочная информация)
"""
    Path("/tmp/section_7_result.md").write_text(text, encoding="utf-8")


def build_section_8(project: dict) -> None:
    """Строит /tmp/section_8_result.md — сводка по разделам 3-7.

    Раздел 9: сводный вердикт по проекту. Берёт health из файлов
    /tmp/section_{3,4,5,6,7}_result.md:
      - section_3_result.md — Замечания по срокам
      - section_4_result.md — Полнота заполнения
      - section_5_result.md — Актуальность прогнозов
      - section_6_indicators_result.md — Показатели проекта (16) [NEW v1.0.18]
      - section_6_result.md — Финансовый статус [после перенумерации: раздел 7 в MD]
    """
    import re

    def get_health(path):
        text = Path(path).read_text(encoding="utf-8")
        m = re.search(r'\*\*Вердикт раздела:\*\*\s*(\S+)', text)
        return m.group(1) if m else "—"

    def get_critical(path):
        text = Path(path).read_text(encoding="utf-8")
        m = re.search(r'(\d+)\s*критических', text)
        return int(m.group(1)) if m else 0

    s3 = get_health("/tmp/section_3_result.md")
    s4 = get_health("/tmp/section_4_result.md")
    s5 = get_health("/tmp/section_5_result.md")
    # 6 — Показатели (verdict может быть: Норма / Информационное / Существенное / Критическое)
    s_indicators = get_health("/tmp/section_6_indicators_result.md")
    # 7 — Финансы (внутренне называется section_6_result.md по имени файла)
    s_finance = get_health("/tmp/section_6_result.md")

    c3 = get_critical("/tmp/section_3_result.md")
    c5 = get_critical("/tmp/section_5_result.md")
    c_finance = get_critical("/tmp/section_6_result.md")

    # === Сводный вердикт проекта ===
    # Любой «Болен» ⇒ Болен.
    # «Критическое» (показатели) приравниваем к «Болен».
    def is_sick(s):
        return "Болен" in s or "Критическ" in s or "БОЛЕН" in s

    if is_sick(s_finance) or is_sick(s_indicators) or is_sick(s5) or is_sick(s3) or is_sick(s4):
        verdict = "Болен"
    elif any(v in ("Требует внимания", "Существенное") for v in (s3, s4, s5, s_indicators, s_finance)):
        verdict = "Требует внимания"
    else:
        verdict = "Здоров"

    def badge(health):
        return {
            "Болен": "🔴 Болен",
            "Критическое": "🔴 Критическое",
            "Требует внимания": "🟡 Требует внимания",
            "Существенное": "🟡 Существенное",
            "Информационное": "⚪ Информационное",
            "Здоров": "🟢 Здоров",
            "Норма": "🟢 Норма",
        }.get(health, f"⚪ {health}")

    text = f"""## 9. Индикатор (общий вердикт)

**Статус: {verdict.upper()}**

| Раздел | Название | Статус |
|--------|----------|--------|
| 3 | Замечания по срокам | {badge(s3)} ({c3} крит.) |
| 4 | Полнота заполнения | {badge(s4)} |
| 5 | Актуальность прогнозов | {badge(s5)} ({c5} крит.) |
| 6 | Показатели проекта (16) | {badge(s_indicators)} |
| 7 | Финансовый статус | {badge(s_finance)} ({c_finance} крит.) |
| 8 | Технические данные | ℹ️ Нейтральный (справочная информация) |

**Правило:** раздел с худшим вердиктом определяет общий. «Критическое»
(показатели) приравнивается к «Болен» (финансы).

---

## Сводка по отчёту

- **Вердикт:** {verdict.upper()}
- **Критических (по срокам/прогнозам/финансам):** {c3 + c5 + c_finance}
- **Существенных:** 0
- **Информационных:** 0

**Главные проблемы:**
1. Финансы — критическое состояние
2. Сроки — критические просрочки
3. Прогнозы — неактуальные данные
"""
    Path("/tmp/section_8_result.md").write_text(text, encoding="utf-8")
def rebuild_md(project: dict, generator: str = "fst-project-health") -> Path:
    """Склеивает /tmp/section_*_result.md → /tmp/project_<code>_report.md.

    v1.0.19: принимает `generator` — какой skill сгенерировал этот MD.
    По умолчанию 'fst-project-health' (живой онлайн-прогон).
    Сателлиты передают своё имя: 'fst-project-health-snap-md' и т.д.
    """
    import subprocess
    out = Path(f"/tmp/project_{project['code']}_report.md")
    subprocess.run(
        ["python3", str(SCRIPTS / "rebuild_report.py"),
         project["code"], project["name"], str(project["project_id"]),
         # 4: section_suffix (пусто), 5: timestamp (None → сейчас), 6: generator
         "", "", generator],
        check=True,
    )
    return out


def build_html(code: str) -> Path:
    """Генерирует HTML через build_html_report.main() (Level 3: in-process).

    Подмена sys.argv для argparse внутри main().
    Регистрируем модуль в sys.modules ДО exec_module (для @dataclass).
    Явно вызываем m.main() — exec_module НЕ запускает код в `if __name__`.
    """
    import sys as _sys
    old_argv = _sys.argv
    _sys.argv = ["build_html_report.py", "--code", code]
    try:
        spec = importlib.util.spec_from_file_location(
            "build_html_report", str(SCRIPTS / "build_html_report.py")
        )
        m = importlib.util.module_from_spec(spec)
        _sys.modules["build_html_report"] = m
        spec.loader.exec_module(m)
        result = m.main()  # ← ВОТ ТУТ БЫЛ БАГ: main() не вызывался
    finally:
        _sys.argv = old_argv

    out = Path(f"/tmp/project_{code}_report.html")
    if not out.exists():
        raise RuntimeError(f"HTML не создан: {out}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Оркестратор отчётов по скиллу fst-project-health")
    ap.add_argument("--code", required=True, help="Код проекта (504-595, 503-152, 503-434, ...)")
    ap.add_argument("--no-html", action="store_true", help="Пропустить HTML")
    ap.add_argument("--sections", default="3,4,5,6,7,8", help="Какие секции строить")
    ap.add_argument("--no-cache", action="store_true", help="Игнорировать кэш")
    ap.add_argument("--timing", action="store_true", help="Показать время по стадиям")
    ap.add_argument("--generator", default="fst-project-health",
                    help="Имя генератора для YAML front-matter (для атрибуции). "
                         "По умолчанию 'fst-project-health'. "
                         "Сателлиты передают своё имя: fst-project-health-snap-md, "
                         "fst-project-health-snapshot, fst-project-health-from-json и т.д.")
    args = ap.parse_args()

    sections_to_build = set(int(s) for s in args.sections.split(","))

    timings = {}

    def t(label):
        timings[label] = time.time()
        print(f"\n⏱️  [{label}]")
        return time.time()

    print(f"🚀 Запуск pipeline для {args.code}")
    print(f"   Секции: {sorted(sections_to_build)}")

    t("find_project")
    project = find_project(args.code)
    print(f"   ✅ {project['name']!r} (ProjectId={project['project_id']})")

    t("save_project_json")
    json_path = save_project_json(project)
    print(f"   ✅ {json_path} ({json_path.stat().st_size} bytes)")

    # Кэш между запусками (Level 4)
    use_cache = not args.no_cache
    points_cache = None
    props_cache = None

    # Загружаем КТ через серверный фильтр (Level 1: AllMyPoint?ProjectId=...)
    if {3, 5} & sections_to_build:
        t("load_project_points")
        if use_cache:
            cached = cache_get(args.code)
            if cached and "all_points" in cached:
                age = time.time() - cache_key_path(args.code).stat().st_mtime
                points_cache = cached["all_points"]
                print(f"   ✅ Из кэша ({len(points_cache)} КТ, age={age:.0f}с)")
            else:
                points_cache = load_project_points(project)
                cache_put(args.code, {"all_points": points_cache})
                print(f"   ✅ {len(points_cache)} КТ (с серверным фильтром ?ProjectId=)")
        else:
            points_cache = load_project_points(project)
            print(f"   ✅ {len(points_cache)} КТ")

    # Загружаем properties для секции 4
    if 4 in sections_to_build:
        t("load_project_entity")
        sid = get_pipeline_sid()
        proj_data = mcp_call(sid, "get_entity_data",
                             {"entityName": "Project", "data_id": str(project["project_id"])})
        props_cache = proj_data.get("properties", {})
        print(f"   ✅ {len(props_cache)} properties")

    # Строим секции
    if 3 in sections_to_build:
        t("section_3")
        build_section_3(project, points_cache=points_cache)
        print(f"   ✅ /tmp/section_3_result.md")
    if 4 in sections_to_build:
        t("section_4")
        build_section_4(project, props_cache=props_cache)
        print(f"   ✅ /tmp/section_4_result.md")
    if 5 in sections_to_build:
        t("section_5")
        build_section_5(project, points_cache=points_cache)
        print(f"   ✅ /tmp/section_5_result.md")
    if 6 in sections_to_build:
        t("section_6_indicators")
        build_section_6_indicators(project)
        print(f"   ✅ /tmp/section_6_indicators_result.md")
        t("section_6")
        build_section_6(project)
        print(f"   ✅ /tmp/section_6_result.md")
    if 7 in sections_to_build:
        t("section_7")
        build_section_7(project)
        print(f"   ✅ /tmp/section_7_result.md")
    if 8 in sections_to_build:
        t("section_8")
        build_section_8(project)
        print(f"   ✅ /tmp/section_8_result.md")

    t("rebuild_md")
    md_path = rebuild_md(project, generator=args.generator)
    print(f"   ✅ {md_path} ({md_path.stat().st_size} bytes)")

    if not args.no_html:
        t("build_html")
        html_path = build_html(args.code)
        print(f"   ✅ {html_path} ({html_path.stat().st_size} bytes)")

    timings["end"] = time.time()

    print(f"\n✅ Готово!")

    if args.timing:
        print(f"\n⏱️  Время по стадиям:")
        prev = timings.get("find_project", 0)
        for stage, t_start in timings.items():
            if stage == "end":
                total = t_start - prev
                print(f"  {'TOTAL':30s} {total:6.2f} сек")
            else:
                next_stage = None
                for next_key, next_val in timings.items():
                    if next_val > t_start:
                        next_stage = next_val
                        break
                if next_stage:
                    duration = next_stage - t_start
                    print(f"  {stage:30s} {duration:6.2f} сек")

    return 0


if __name__ == "__main__":
    sys.exit(main())
