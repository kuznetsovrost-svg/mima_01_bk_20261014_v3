"""
grid_parser.py — Парсер структуры Excalidraw файла со скиллами.

Определяет:
- Frame "Таблица WxH" (cell_width=W, cell_height=H)
- Группы клеток внутри Frame (rows × cols — авто по позициям)
- Группы описаний вне Frame (порядок произвольный)
"""
import re
from typing import Dict, List, Tuple, Optional, Any


# Паттерн имени Frame: "Таблица WxH", "Таблица W x H" (любые пробелы вокруг x),
# "Таблица WхH" (русская х)
TABLE_FRAME_NAME_PATTERN = re.compile(
    r'^Таблица\s+(\d+)\s*[xхХX]\s*(\d+)\s*$',
    re.IGNORECASE
)

# Паттерн номера сущности: "##NNN" или "#NNN"
ENTITY_NUMBER_PATTERN = re.compile(r'^#+\s*(\d+)\s*$')

# Паттерн наименования в таблице: НЕ начинается с #
SKILL_NAME_PATTERN = re.compile(r'^[^#].{1,200}$')

# Паттерн наименования в описании: начинается с # (но не #NNN)
# "наименование сущности, начинающееся с #"
DESCRIPTION_NAME_PATTERN = re.compile(r'^#\s*([^\d].*|.*\D.*)$')


def parse_table_frame_name(name: str) -> Optional[Tuple[int, int]]:
    """
    Извлекает cell_width и cell_height из имени Frame.
    'Таблица 500x300' → (500, 300)
    'Таблица 500х300' → (500, 300)  # русская х
    """
    if not name:
        return None
    m = TABLE_FRAME_NAME_PATTERN.match(name.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def is_table_frame(element: Dict) -> bool:
    """Является ли элемент Frame таблицы."""
    if element.get('type') != 'frame':
        return False
    name = element.get('name', '').strip()
    return parse_table_frame_name(name) is not None


def is_entity_number(text: str) -> Optional[str]:
    """Извлекает номер из '##NNN' или '#NNN'. Возвращает 'NNN' или None."""
    if not text:
        return None
    text = text.strip()
    m = ENTITY_NUMBER_PATTERN.match(text)
    if m:
        return m.group(1)
    return None


def is_skill_name_in_table(text: str) -> bool:
    """
    Наименование в таблице: НЕ начинается с #.
    Возвращает True если текст может быть именем навыка в клетке.
    """
    if not text:
        return False
    text = text.strip()
    if not text:
        return False
    # Имя в таблице НЕ должно начинаться с #
    if text.startswith('#'):
        return False
    # Должно быть не пустое, не слишком длинное
    return 1 <= len(text) <= 200


def is_description_name(text: str) -> bool:
    """
    Наименование в описании: начинается с #, но НЕ является просто '##NNN'.
    Возвращает True если текст может быть именем навыка в зоне описаний.
    """
    if not text:
        return False
    text = text.strip()
    if not text.startswith('#'):
        return False
    # Не должно быть просто ##NNN (это номер, не имя)
    if ENTITY_NUMBER_PATTERN.match(text):
        return False
    return 2 <= len(text) <= 200


def find_table_frame(elements: List[Dict]) -> Optional[Dict]:
    """Находит Frame таблицы в файле."""
    for el in elements:
        if is_table_frame(el):
            return el
    return None


def point_in_rect(x: float, y: float, rect: Dict, padding: float = 0) -> bool:
    """Точка внутри прямоугольника (с padding)."""
    rx, ry = rect.get('x', 0), rect.get('y', 0)
    rw, rh = rect.get('width', 0), rect.get('height', 0)
    return (rx - padding <= x <= rx + rw + padding and
            ry - padding <= y <= ry + rh + padding)


def element_in_frame(element: Dict, frame: Dict) -> bool:
    """Находится ли элемент внутри Frame."""
    x = element.get('x', 0) + element.get('width', 0) / 2
    y = element.get('y', 0) + element.get('height', 0) / 2
    return point_in_rect(x, y, frame, padding=10)


def group_by_group_id(elements: List[Dict]) -> Dict[str, List[Dict]]:
    """Группирует элементы по groupIds[0]."""
    groups: Dict[str, List[Dict]] = {}
    for el in elements:
        gids = el.get('groupIds', [])
        if gids:
            gid = gids[0]
            groups.setdefault(gid, []).append(el)
    return groups


def detect_rows_cols_from_groups(groups_in_frame: List[List[Dict]],
                                  cell_width: int,
                                  cell_height: int) -> Tuple[int, int]:
    """
    Определяет количество строк и столбцов по позициям групп.

    Использует центры bounding box групп. Группирует по cell_width/cell_height.
    """
    if not groups_in_frame:
        return 0, 0

    # Центры групп
    centers = []
    for grp in groups_in_frame:
        if not grp:
            continue
        xs = [el.get('x', 0) for el in grp]
        ys = [el.get('y', 0) for el in grp]
        ws = [el.get('width', 0) for el in grp]
        hs = [el.get('height', 0) for el in grp]
        x_min = min(xs)
        y_min = min(ys)
        x_max = max(x + w for x, w in zip(xs, ws))
        y_max = max(y + h for y, h in zip(ys, hs))
        cx = (x_min + x_max) / 2
        cy = (y_min + y_max) / 2
        centers.append((cx, cy, x_min, y_min))

    if not centers:
        return 0, 0

    # Базовая точка для вычисления индексов
    base_x = min(c[0] for c in centers)
    base_y = min(c[1] for c in centers)

    col_set = set()
    row_set = set()
    for cx, cy, _, _ in centers:
        col = round((cx - base_x) / cell_width)
        row = round((cy - base_y) / cell_height)
        col_set.add(col)
        row_set.add(row)

    rows = max(row_set) + 1 if row_set else 0
    cols = max(col_set) + 1 if col_set else 0
    return rows, cols


def get_grid_position(cx: float, cy: float,
                      base_x: float, base_y: float,
                      cell_width: int, cell_height: int) -> Tuple[int, int]:
    """Возвращает (col, row) для точки в сетке."""
    col = round((cx - base_x) / cell_width)
    row = round((cy - base_y) / cell_height)
    return col, row


def get_entity_bounds(group: List[Dict]) -> Tuple[float, float, float, float]:
    """Возвращает (x_min, y_min, x_max, y_max) для группы."""
    if not group:
        return 0, 0, 0, 0
    xs = [el.get('x', 0) for el in group]
    ys = [el.get('y', 0) for el in group]
    ws = [el.get('width', 0) for el in group]
    hs = [el.get('height', 0) for el in group]
    return (
        min(xs), min(ys),
        max(x + w for x, w in zip(xs, ws)),
        max(y + h for y, h in zip(ys, hs))
    )


def get_group_center(group: List[Dict]) -> Tuple[float, float]:
    """Возвращает центр bounding box группы."""
    x_min, y_min, x_max, y_max = get_entity_bounds(group)
    return (x_min + x_max) / 2, (y_min + y_max) / 2


def extract_text(element: Dict) -> str:
    """Извлекает текст из элемента."""
    if element.get('type') == 'text':
        return element.get('text', '').strip()
    return ''