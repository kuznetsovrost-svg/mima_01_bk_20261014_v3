"""
rebuild_report.py — склейка финального отчёта из section_*_result.md файлов.

Использование:
    python3 scripts/rebuild_report.py <project_code> <project_name> <project_id> [section_glob]

Пример:
    python3 scripts/rebuild_report.py 504-595 "Космодром Жуковский" 4595
    python3 scripts/rebuild_report.py 503-152 "ФРП - Минпромторг-Развитие 2026" 3152

Что делает:
1. Читает /tmp/section_*_result.md файлы (по умолчанию section_3..8_result.md,
   или section_3..8_<code>_result.md если передан section_glob).
2. Добавляет YAML-front-matter в начало (snapshot_timestamp, generator,
   skill_version, schema_version, source_skill, project_code и т.д.).
3. Включает section_6_indicators_result.md в склейку (16 показателей).
   Это критично для самодостаточности: build_html_report.py собирает HTML
   ТОЛЬКО из MD и JSON, без обращений к MCP.
4. Склеивает секции с заголовком через разделитель "---".
5. Записывает /tmp/project_<code>_report.md.
6. Печатает размер и количество строк.

Этот скрипт — **типовая утилита**, не часть скилла. Каждый раздел должен
быть записан в /tmp/section_N_result.md отдельным скриптом (pitfall #10:
write section result to file immediately, not as inline chat output).
"""
import os
import re
import sys
from pathlib import Path
from datetime import datetime


# Версии скилла и схемы
SKILL_VERSION = "1.0.19"
SCHEMA_VERSION = "1.0.0"
SOURCE_SKILL = "fst-project-health"
SNAPSHOT_GENERATOR = "fst-project-health-snap-md"


def _read_yaml_field(path: Path, key: str, default: str = "") -> str:
    """Читает одно поле из YAML-front-matter файла (если есть). Утилита."""
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.+?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return default
    for line in m.group(1).splitlines():
        mk = re.match(rf"^{key}:\s*(.+?)\s*$", line)
        if mk:
            v = mk.group(1).strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            return v
    return default


def _read_file_id_from_proj_json(code: str) -> str:
    """Достаёт file_id (MCP) из /tmp/proj_<code>.json, если есть."""
    p = Path(f"/tmp/proj_{code}.json")
    if not p.exists():
        return ""
    try:
        import json
        data = json.loads(p.read_text(encoding="utf-8"))
        return str(data.get("FileId", "")) or str(data.get("documentId", "")) or ""
    except Exception:
        return ""


def _detect_snapshot_timestamp(code: str, fallback: str) -> str:
    """Берёт snapshot_timestamp из уже сгенерированного MD (если есть),
    иначе использует текущее время.
    """
    md_path = Path(f"/tmp/project_{code}_report.md")
    if md_path.exists():
        v = _read_yaml_field(md_path, "snapshot_timestamp")
        if v:
            return v
    return fallback


def _build_front_matter(
    code: str,
    name: str,
    project_id: int,
    timestamp: str | None,
    generator: str = SNAPSHOT_GENERATOR,
) -> str:
    """Собирает YAML-front-matter (v1.0.0).

    Args:
        generator: имя генератора (обычно = name of caller skill).
            По умолчанию — `SNAPSHOT_GENERATOR` ("fst-project-health-snap-md"),
            для обратной совместимости со старыми снапшотами. Если вы
            вызываете rebuild_report.py из run_all.py — передавайте
            `generator="fst-project-health"`, чтобы атрибуция в YAML была
            корректной.
        timestamp: время снимка. Для live (generator="fst-project-health")
            передавайте None — поле `snapshot_timestamp` не пишется,
            и в HTML показывается только "Отчёт создан:".

    Returns:
        YAML front-matter как строка.
    """
    file_id = _read_file_id_from_proj_json(code)

    # v1.0.19: snapshot_timestamp пишется только если:
    # 1) timestamp явно передан (не None), И
    # 2) generator — это снепшот-скилл (snap-md / snapshot / from-md-snapshot).
    # Для live-режима (generator="fst-project-health") поле отсутствует —
    # и в HTML не появляется "Слепок от:".
    is_snapshot_generator = generator.startswith((
        "fst-project-health-snap-md",
        "fst-project-health-snapshot",
        "fst-project-health-from-md-snapshot",
    ))
    yaml_timestamp_line = (
        f'snapshot_timestamp: "{timestamp}"'
        if (timestamp and is_snapshot_generator)
        else None
    )

    lines = [
        "---",
        # v1.0.19: snapshot_timestamp пишется только для snapshot-генераторов.
        # Для live (generator="fst-project-health") — отсутствует, и в HTML
        # показывается только "Отчёт создан:".
        *([yaml_timestamp_line] if yaml_timestamp_line else []),
        f'generator: "{generator}"',
        f'skill_version: "{SCHEMA_VERSION}"',
        f'schema_version: "{SCHEMA_VERSION}"',
        f'source_skill: "{SOURCE_SKILL}"',
        f'source_skill_version: "{SKILL_VERSION}"',
        f'project_code: "{code}"',
        f'project_id: {project_id}',
        "---",
        "",
    ]
    if file_id:
        # вставим file_id перед закрывающим ---
        lines.insert(-2, f'file_id: "{file_id}"')
    return "\n".join(lines)


def main(
    project_code: str,
    project_name: str,
    project_id: int,
    section_suffix: str = "",
    timestamp: str | None = None,
    generator: str = SNAPSHOT_GENERATOR,
) -> int:
    """
    project_code:    e.g. "504-595"
    project_name:    e.g. "Космодром Жуковский внедрение ИСУП"
    project_id:      e.g. 4595
    section_suffix:  "" for default, or "_503-152" if you want project-specific files
    timestamp:       явный snapshot_timestamp; если None — текущее время.
    generator:       атрибуция — какой skill сгенерировал этот MD.
                     По умолчанию "fst-project-health-snap-md" (для обратной совместимости).
                     run_all.py должен передавать "fst-project-health",
                     fst-project-health-snapshot — "fst-project-health-snapshot", и т.д.
    """
    if not project_code or not project_name:
        print("Usage: rebuild_report.py <project_code> <project_name> <project_id> [section_suffix] [timestamp] [generator]")
        return 1

    now_ts = (timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")).strip()

    # v1.0.19: для live (generator="fst-project-health") поле
    # snapshot_timestamp НЕ пишем — иначе в HTML появляется "Слепок от: <сейчас>",
    # что неверно по смыслу. Логика (что считать snapshot-генератором) —
    # внутри _build_front_matter.
    yaml_timestamp = now_ts  # _build_front_matter решит, писать или нет

    # ВАЖНО: section_6_indicators_result.md включается между разделами 5 и 6
    # (согласно нумерации run_all.py: 6 = Показатели, 7 = Финансы,
    # 8 = Тех. данные, 9 = Сводка-индикатор).
    section_files = [
        f"section_3{section_suffix}_result.md",
        f"section_4{section_suffix}_result.md",
        f"section_5{section_suffix}_result.md",
        # === NEW: показатели проекта (16 индикаторов) — самодостаточность MD ===
        f"section_6_indicators{section_suffix}_result.md",
        f"section_6{section_suffix}_result.md",  # Финансы (по новой нумерации = "7.")
        f"section_7{section_suffix}_result.md",  # Тех. данные (= "8.")
        f"section_8{section_suffix}_result.md",  # Сводка-индикатор (= "9.")
    ]

    sections = []
    for fname in section_files:
        fpath = Path(f"/tmp/{fname}")
        if fpath.exists():
            sections.append(fpath.read_text(encoding="utf-8"))
        else:
            sections.append(f"\n## [{fname} — не выполнено]\n\n")

    header = f"""# Отчёт о здоровье проекта «{project_name}»

**Target:** {project_code} (ProjectId={project_id})
**Дата формирования:** {now_ts} (локальное время)
**MCP:** PMForesight MCP v3.2.4
**Scope:** полный отчёт по проекту (5 содержательных разделов + тех. данные + сводка)

---

"""

    front_matter = _build_front_matter(project_code, project_name, project_id, now_ts, generator=generator)

    report_path = Path(f"/tmp/project_{project_code}_report.md")
    report_path.write_text(
        front_matter + header + "\n---\n".join(sections) + "\n",
        encoding="utf-8",
    )

    line_count = sum(1 for _ in report_path.open(encoding="utf-8"))
    print(f"✅ Отчёт собран: {report_path}")
    print(f"   Размер: {report_path.stat().st_size} байт, {line_count} строк")
    print(f"   generator: {generator}")  # v1.0.19: печатаем атрибуцию для отладки
    print(f"   Отправка: MEDIA:{report_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: rebuild_report.py <project_code> <project_name> <project_id> "
              "[section_suffix] [timestamp] [generator]")
        sys.exit(1)
    code = sys.argv[1]
    name = sys.argv[2]
    pid = int(sys.argv[3])
    suffix = sys.argv[4] if len(sys.argv) > 4 else ""
    ts = sys.argv[5] if len(sys.argv) > 5 else None
    gen = sys.argv[6] if len(sys.argv) > 6 else SNAPSHOT_GENERATOR
    sys.exit(main(code, name, pid, suffix, ts, gen))
