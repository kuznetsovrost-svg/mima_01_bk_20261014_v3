"""
cell_extractor.py — Извлечение сущностей из клеток таблицы.

Клетка = группа из 3-х элементов внутри Frame "Таблица WxH":
1. Прямоугольник (background)
2. ##NNN (номер сущности)
3. Наименование (текст без # в начале)
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from grid_parser import (
    is_entity_number, is_skill_name_in_table,
    get_entity_bounds, get_group_center
)


@dataclass
class CellContent:
    """Содержимое одной клетки таблицы."""
    group_id: str
    nnn: Optional[str]
    name: Optional[str]
    rectangle_id: Optional[str]
    bounds: Tuple[float, float, float, float] = (0, 0, 0, 0)
    center: Tuple[float, float] = (0, 0)
    col: int = 0
    row: int = 0

    def is_complete(self) -> bool:
        """Клетка считается полной если есть ##NNN и наименование."""
        return self.nnn is not None and self.name is not None

    def is_empty(self) -> bool:
        """Клетка считается пустой если ни номера, ни имени."""
        return self.nnn is None and self.name is None

    def to_dict(self) -> Dict:
        return {
            'group_id': self.group_id,
            'nnn': self.nnn,
            'name': self.name,
            'col': self.col,
            'row': self.row,
            'rectangle_id': self.rectangle_id,
            'complete': self.is_complete(),
        }


def classify_group_elements(group: List[Dict]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Классифицирует элементы группы клетки.

    Returns:
        (rectangle_id, nnn, name)
    """
    rectangle_id = None
    nnn = None
    name = None

    for el in group:
        el_type = el.get('type')

        if el_type == 'rectangle':
            if rectangle_id is None:
                rectangle_id = el.get('id')
            continue

        if el_type == 'text':
            text = el.get('text', '').strip()
            if not text:
                continue

            # Проверяем номер ##NNN
            extracted_nnn = is_entity_number(text)
            if extracted_nnn and nnn is None:
                nnn = extracted_nnn
                continue

            # Проверяем имя (не начинается с #)
            if is_skill_name_in_table(text) and name is None:
                name = text
                continue

    return rectangle_id, nnn, name


def extract_cells(groups_in_frame: List[List[Dict]],
                  cell_width: int,
                  cell_height: int) -> List[CellContent]:
    """
    Извлекает клетки из групп внутри Frame таблицы.
    rows × cols вычисляются автоматически по позициям групп.
    """
    cells = []
    for group in groups_in_frame:
        if not group:
            continue
        rect_id, nnn, name = classify_group_elements(group)
        bounds = get_entity_bounds(group)
        center = get_group_center(group)
        gid = group[0].get('groupIds', ['?'])
        cells.append(CellContent(
            group_id=gid[0] if gid else '?',
            nnn=nnn,
            name=name,
            rectangle_id=rect_id,
            bounds=bounds,
            center=center,
        ))

    # Назначаем позиции (col, row)
    if cells and cell_width and cell_height:
        base_x = min(c.bounds[0] for c in cells)
        base_y = min(c.bounds[1] for c in cells)
        for cell in cells:
            cx, cy = cell.center
            cell.col = round((cx - base_x) / cell_width)
            cell.row = round((cy - base_y) / cell_height)

    return cells


def detect_grid_dims(cells: List[CellContent]) -> Tuple[int, int]:
    """Возвращает (rows, cols) по позициям клеток."""
    if not cells:
        return 0, 0
    rows = max(c.row for c in cells) + 1
    cols = max(c.col for c in cells) + 1
    return rows, cols