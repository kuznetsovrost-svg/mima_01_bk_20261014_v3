#!/usr/bin/env python3
"""
grid_analyzer.py — CLI для анализа Excalidraw файла со скиллами.

Структура файла:
- Frame "Таблица WxH" (cell_width=W, cell_height=H):
  Клетки с группами {прямоугольник, ##NNN, наименование (без #)}
- Любые другие Frame (или без Frame):
  Группы описаний {прямоугольник, ##NNN, #Наименование, многострочный текст}

Команды:
  summary                    Общая статистика
  list-skills                Все сущности таблицы
  list-descriptions          Все описания
  get-skill NNN              Информация о сущности NNN
  get-description NNN        Текст описания NNN
  find-orphan-descriptions   Описания без сущности в таблице
  find-missing-descriptions  Сущности без описания
  find-name-mismatches       NNN совпал, но имя отличается
  coverage                   % покрытия сущностей описаниями
  match-skills               Полный отчёт о сопоставлении
  validate                   Все проверки сразу
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Импорты модулей скилла
from grid_parser import (
    parse_table_frame_name, find_table_frame, is_table_frame,
    group_by_group_id, element_in_frame,
)
from cell_extractor import extract_cells, detect_grid_dims, CellContent
from description_extractor import extract_descriptions, DescriptionContent
from skill_matcher import (
    SkillRecord, DescriptionRecord, match, MatchReport,
    find_orphan_descriptions as _find_orphan,
    find_missing_descriptions as _find_missing,
    find_name_mismatches,
)


def load_file(filepath: str) -> Dict:
    """Загружает .excalidraw файл."""
    path = Path(filepath)
    if not path.exists():
        print(f"Ошибка: файл не найден: {filepath}", file=sys.stderr)
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def split_groups_by_location(elements: List[Dict],
                              table_frame: Optional[Dict]) -> tuple:
    """
    Разделяет все группы на:
    - groups_in_table: внутри Frame таблицы
    - groups_outside: вне Frame таблицы
    Возвращает (groups_in_table, groups_outside) — каждая список групп.
    """
    groups = group_by_group_id(elements)
    in_table = []
    outside = []
    for gid, group in groups.items():
        # Проверяем положение по центру группы
        xs = [el.get('x', 0) for el in group]
        ys = [el.get('y', 0) for el in group]
        ws = [el.get('width', 0) for el in group]
        hs = [el.get('height', 0) for el in group]
        cx = (min(xs) + max(x + w for x, w in zip(xs, ws))) / 2
        cy = (min(ys) + max(y + h for y, h in zip(ys, hs))) / 2

        if table_frame and element_in_frame({'x': cx - 1, 'y': cy - 1,
                                              'width': 2, 'height': 2},
                                             table_frame):
            in_table.append(group)
        else:
            outside.append(group)
    return in_table, outside


def extract_all(data: Dict) -> Dict[str, Any]:
    """Извлекает всю информацию из файла."""
    elements = data.get('elements', [])
    if not elements:
        print("Ошибка: в файле нет элементов", file=sys.stderr)
        sys.exit(1)

    table_frame = find_table_frame(elements)
    if table_frame is None:
        print("Ошибка: Frame 'Таблица WxH' не найден", file=sys.stderr)
        sys.exit(1)

    dims = parse_table_frame_name(table_frame.get('name', ''))
    if dims is None:
        print(f"Ошибка: не удалось распарсить имя Frame: {table_frame.get('name')}",
              file=sys.stderr)
        sys.exit(1)
    cell_width, cell_height = dims

    in_table_groups, outside_groups = split_groups_by_location(elements, table_frame)
    cells = extract_cells(in_table_groups, cell_width, cell_height)
    descriptions = extract_descriptions(outside_groups)
    rows, cols = detect_grid_dims(cells)

    # Строим SkillRecord из клеток
    skills = []
    for cell in cells:
        if cell.nnn is not None:  # Только клетки с номерами
            skills.append(SkillRecord(
                nnn=cell.nnn,
                name=cell.name or '',
                col=cell.col,
                row=cell.row,
                group_id=cell.group_id,
                extra={'rectangle_id': cell.rectangle_id},
            ))

    # Строим DescriptionRecord из описаний
    desc_records = []
    for d in descriptions:
        if d.nnn is not None:
            desc_records.append(DescriptionRecord(
                nnn=d.nnn,
                name=d.name or '',
                text=d.text or '',
                group_id=d.group_id,
                extra={'rectangle_id': d.rectangle_id, 'text_id': d.text_id},
            ))

    return {
        'table_frame': {
            'name': table_frame.get('name'),
            'cell_width': cell_width,
            'cell_height': cell_height,
            'x': table_frame.get('x'),
            'y': table_frame.get('y'),
        },
        'rows': rows,
        'cols': cols,
        'total_cells': rows * cols,
        'filled_cells': len(cells),
        'skills': skills,
        'descriptions': desc_records,
        'raw_cells': cells,
        'raw_descriptions': descriptions,
    }


def cmd_summary(extracted: Dict) -> None:
    """Общая статистика."""
    tf = extracted['table_frame']
    print("=" * 60)
    print(f"📊 ОБЩАЯ СТАТИСТИКА")
    print("=" * 60)
    print(f"Frame таблицы:    {tf['name']}")
    print(f"Размер клетки:    {tf['cell_width']} × {tf['cell_height']} px")
    print(f"Сетка:            {extracted['rows']} × {extracted['cols']} = {extracted['total_cells']} ячеек")
    print(f"Заполнено:        {extracted['filled_cells']} клеток")
    print(f"Сущностей:        {len(extracted['skills'])}")
    print(f"Описаний:         {len(extracted['descriptions'])}")
    if extracted['skills']:
        match_report = match(extracted['skills'], extracted['descriptions'])
        print(f"Сопоставлено:     {len(match_report.matched)}")
        print(f"Покрытие:         {match_report.coverage_pct}%")


def cmd_list_skills(extracted: Dict) -> None:
    """Список всех сущностей таблицы."""
    skills = sorted(extracted['skills'], key=lambda s: int(s.nnn) if s.nnn.isdigit() else 0)
    print(f"📋 СУЩНОСТИ ТАБЛИЦЫ ({len(skills)}):")
    print("-" * 60)
    print(f"{'NNN':<8} {'Позиция':<12} {'Наименование':<40}")
    print("-" * 60)
    for s in skills:
        pos = f"[{s.row},{s.col}]"
        name = (s.name[:37] + '...') if len(s.name) > 40 else s.name
        print(f"{s.nnn:<8} {pos:<12} {name:<40}")


def cmd_list_descriptions(extracted: Dict) -> None:
    """Список всех описаний."""
    descs = sorted(extracted['descriptions'], key=lambda d: int(d.nnn) if d.nnn.isdigit() else 0)
    print(f"📝 ОПИСАНИЯ СУЩНОСТЕЙ ({len(descs)}):")
    print("-" * 60)
    print(f"{'NNN':<8} {'#Имя':<30} {'Длина':<8} {'Текст (preview)'}")
    print("-" * 60)
    for d in descs:
        name = d.name[1:].strip() if d.name.startswith('#') else d.name
        name = (name[:27] + '...') if len(name) > 30 else name
        preview = (d.text[:30] + '...') if len(d.text) > 30 else d.text
        preview = preview.replace('\n', ' ')
        print(f"{d.nnn:<8} #{name:<29} {len(d.text):<8} {preview}")


def cmd_get_skill(extracted: Dict, nnn: str) -> None:
    """Информация о сущности NNN."""
    skill = next((s for s in extracted['skills']
                  if s.nnn.lstrip('0') == nnn.lstrip('0')), None)
    if not skill:
        print(f"❌ Сущность #{nnn} не найдена в таблице")
        sys.exit(1)
    print(f"📌 СУЩНОСТЬ #{skill.nnn}")
    print(f"   Наименование: {skill.name}")
    print(f"   Позиция:      [{skill.row}, {skill.col}] (row, col)")
    print(f"   Group ID:     {skill.group_id}")
    print(f"   Rectangle:    {skill.extra.get('rectangle_id')}")

    # Показываем связанное описание если есть
    desc = next((d for d in extracted['descriptions']
                 if d.nnn.lstrip('0') == nnn.lstrip('0')), None)
    if desc:
        print(f"\n   ОПИСАНИЕ:")
        print(f"   Имя в описании: {desc.name}")
        print(f"   Текст:")
        for line in desc.text.split('\n'):
            print(f"     {line}")
    else:
        print(f"\n   ⚠️  Описание отсутствует")


def cmd_get_description(extracted: Dict, nnn: str) -> None:
    """Текст описания NNN."""
    desc = next((d for d in extracted['descriptions']
                 if d.nnn.lstrip('0') == nnn.lstrip('0')), None)
    if not desc:
        print(f"❌ Описание для #{nnn} не найдено", file=sys.stderr)
        sys.exit(1)
    print(desc.text)


def cmd_find_orphan(extracted: Dict) -> None:
    """Описания без сущности в таблице."""
    orphans = _find_orphan(extracted['skills'], extracted['descriptions'])
    if not orphans:
        print("✅ Нет описаний-сирот (все описания имеют сущность в таблице)")
        return
    print(f"⚠️  ОПИСАНИЯ БЕЗ СУЩНОСТИ В ТАБЛИЦЕ ({len(orphans)}):")
    for d in orphans:
        print(f"   #{d.nnn} {d.name}")


def cmd_find_missing(extracted: Dict) -> None:
    """Сущности без описания."""
    missing = _find_missing(extracted['skills'], extracted['descriptions'])
    if not missing:
        print("✅ У всех сущностей есть описания")
        return
    print(f"⚠️  СУЩНОСТИ БЕЗ ОПИСАНИЯ ({len(missing)}):")
    for s in missing:
        print(f"   #{s.nnn} {s.name}  [{s.row},{s.col}]")


def cmd_find_name_mismatches(extracted: Dict) -> None:
    """NNN совпал, но имя отличается."""
    mismatches = find_name_mismatches(extracted['skills'], extracted['descriptions'])
    if not mismatches:
        print("✅ Все имена в описаниях совпадают с именами в таблице")
        return
    print(f"⚠️  РАСХОЖДЕНИЯ ИМЁН ({len(mismatches)}):")
    for s, d in mismatches:
        print(f"   #{s.nnn}")
        print(f"     В таблице:   '{s.name}'")
        print(f"     В описании:  '{d.name}'")


def cmd_coverage(extracted: Dict) -> None:
    """Процент покрытия."""
    match_report = match(extracted['skills'], extracted['descriptions'])
    print(f"📊 ПОКРЫТИЕ:")
    print(f"   Сущностей в таблице:   {match_report.total_skills}")
    print(f"   Описаний:              {match_report.total_descriptions}")
    print(f"   Сопоставлено:          {len(match_report.matched)}")
    print(f"   Покрытие:              {match_report.coverage_pct}%")


def cmd_match_skills(extracted: Dict) -> None:
    """Полный отчёт о сопоставлении."""
    match_report = match(extracted['skills'], extracted['descriptions'])
    d = match_report.to_dict()
    print(json.dumps(d, indent=2, ensure_ascii=False))


def cmd_validate(extracted: Dict) -> int:
    """Все проверки. Возвращает exit code (0 = ok, 1 = есть проблемы)."""
    match_report = match(extracted['skills'], extracted['descriptions'])

    print("=" * 60)
    print(f"🔍 ВАЛИДАЦИЯ ФАЙЛА")
    print("=" * 60)

    tf = extracted['table_frame']
    print(f"\nFrame таблицы: {tf['name']} ({tf['cell_width']}×{tf['cell_height']})")
    print(f"Сетка: {extracted['rows']}×{extracted['cols']} = {extracted['total_cells']} ячеек")

    issues = []

    # 1. Пустые клетки
    filled_nnns = {s.nnn for s in extracted['skills']}
    all_cells = set()
    for r in range(extracted['rows']):
        for c in range(extracted['cols']):
            all_cells.add((r, c))
    filled_positions = {(s.row, s.col) for s in extracted['skills']}
    empty_positions = all_cells - filled_positions
    if empty_positions:
        print(f"\n⚠️  Пустых клеток: {len(empty_positions)}")
        for r, c in sorted(empty_positions):
            print(f"     [{r},{c}]")
        issues.append(f"empty_cells={len(empty_positions)}")

    # 2. Orphan descriptions
    if match_report.orphan_descriptions:
        print(f"\n⚠️  Описаний без сущности: {len(match_report.orphan_descriptions)}")
        for d in match_report.orphan_descriptions:
            print(f"     #{d.nnn} {d.name}")
        issues.append(f"orphan_descriptions={len(match_report.orphan_descriptions)}")

    # 3. Missing descriptions
    if match_report.missing_descriptions:
        print(f"\n⚠️  Сущностей без описания: {len(match_report.missing_descriptions)}")
        for s in match_report.missing_descriptions:
            print(f"     #{s.nnn} {s.name}")
        issues.append(f"missing_descriptions={len(match_report.missing_descriptions)}")

    # 4. Name mismatches (двойная проверка)
    if match_report.name_mismatches:
        print(f"\n⚠️  Расхождения имён: {len(match_report.name_mismatches)}")
        for m in match_report.name_mismatches:
            print(f"     #{m.nnn}")
            print(f"       В таблице:  '{m.skill.name}'")
            print(f"       В описании: '{m.description.name}'")
        issues.append(f"name_mismatches={len(match_report.name_mismatches)}")

    # 5. NNN mismatches
    if match_report.nnn_mismatches:
        print(f"\n⚠️  Расхождения NNN: {len(match_report.nnn_mismatches)}")
        for m in match_report.nnn_mismatches:
            print(f"     #{m.nnn}")
        issues.append(f"nnn_mismatches={len(match_report.nnn_mismatches)}")

    # Итог
    print(f"\n{'='*60}")
    if not issues:
        print(f"✅ ВСЁ ОК")
        print(f"   Сущностей: {match_report.total_skills}")
        print(f"   Описаний:  {match_report.total_descriptions}")
        print(f"   Покрытие:  {match_report.coverage_pct}%")
        return 0
    else:
        print(f"❌ НАЙДЕНЫ ПРОБЛЕМЫ:")
        for iss in issues:
            print(f"   - {iss}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Анализ Excalidraw файла со скиллами',
    )
    parser.add_argument('command', help='Команда (см. выше)')
    parser.add_argument('arg', nargs='?', help='Аргумент команды (NNN)')
    parser.add_argument('file', help='Путь к .excalidraw файлу')
    parser.add_argument('--json', action='store_true', help='Вывод в JSON')

    args = parser.parse_args()

    data = load_file(args.file)
    extracted = extract_all(data)

    cmd = args.command
    if cmd == 'summary':
        cmd_summary(extracted)
    elif cmd == 'list-skills':
        cmd_list_skills(extracted)
    elif cmd == 'list-descriptions':
        cmd_list_descriptions(extracted)
    elif cmd == 'get-skill':
        if not args.arg:
            print("Ошибка: укажите NNN", file=sys.stderr)
            sys.exit(1)
        cmd_get_skill(extracted, args.arg)
    elif cmd == 'get-description':
        if not args.arg:
            print("Ошибка: укажите NNN", file=sys.stderr)
            sys.exit(1)
        cmd_get_description(extracted, args.arg)
    elif cmd == 'find-orphan-descriptions':
        cmd_find_orphan(extracted)
    elif cmd == 'find-missing-descriptions':
        cmd_find_missing(extracted)
    elif cmd == 'find-name-mismatches':
        cmd_find_name_mismatches(extracted)
    elif cmd == 'coverage':
        cmd_coverage(extracted)
    elif cmd == 'match-skills':
        cmd_match_skills(extracted)
    elif cmd == 'validate':
        exit_code = cmd_validate(extracted)
        sys.exit(exit_code)
    else:
        print(f"Неизвестная команда: {cmd}", file=sys.stderr)
        print("Доступные: summary, list-skills, list-descriptions, get-skill, "
              "get-description, find-orphan-descriptions, find-missing-descriptions, "
              "find-name-mismatches, coverage, match-skills, validate",
              file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()