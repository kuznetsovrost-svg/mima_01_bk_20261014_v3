"""Фикстуры для тестов excalidraw-grid-analyzer."""
import sys
import json
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SKILL_DIR))


# Размеры по умолчанию для тестовой таблицы
DEFAULT_CELL_W = 500
DEFAULT_CELL_H = 300
DEFAULT_OFFSET_X = 50
DEFAULT_OFFSET_Y = 50


def make_rectangle(eid, x, y, width, height, group_ids=None, frame_id=None):
    """Прямоугольник."""
    return {
        "id": eid, "type": "rectangle",
        "x": x, "y": y, "width": width, "height": height,
        "groupIds": group_ids or [],
        "frameId": frame_id,
    }


def make_text(eid, text, x, y, width, height, group_ids=None, frame_id=None):
    """Текстовый элемент."""
    return {
        "id": eid, "type": "text",
        "text": text, "x": x, "y": y, "width": width, "height": height,
        "groupIds": group_ids or [],
        "frameId": frame_id,
    }


def make_frame(eid, name, x, y, width, height):
    """Frame."""
    return {
        "id": eid, "type": "frame", "name": name,
        "x": x, "y": y, "width": width, "height": height,
    }


def make_skill_group(group_id, number, name, cell_x, cell_y,
                      cell_w=DEFAULT_CELL_W, cell_h=DEFAULT_CELL_H,
                      frame_id="frame-table"):
    """
    Создать группу навыка (3 элемента): rect + ##NNN + name.
    Размещает по центру клетки.
    """
    rect_w = cell_w - 100
    rect_h = cell_h - 100
    rect_x = cell_x + 50
    rect_y = cell_y + 50

    return [
        make_rectangle(
            f"r-{group_id}", rect_x, rect_y, rect_w, rect_h,
            group_ids=[group_id], frame_id=frame_id
        ),
        make_text(
            f"t-{group_id}", f"##{number:03d}",
            rect_x + 10, rect_y + 10, 60, 30,
            group_ids=[group_id], frame_id=frame_id
        ),
        make_text(
            f"n-{group_id}", name,
            rect_x + 80, rect_y + 60, rect_w - 100, 30,
            group_ids=[group_id], frame_id=frame_id
        ),
    ]


def make_description_group(group_id, number, name, description,
                            cell_x, cell_y, cell_w=500, cell_h=300,
                            frame_id="frame-desc"):
    """Группа описания: rect + ##NNN + #name + описание."""
    rect_w = cell_w - 50
    rect_h = cell_h - 50
    rect_x = cell_x + 25
    rect_y = cell_y + 25

    return [
        make_rectangle(
            f"r-d-{group_id}", rect_x, rect_y, rect_w, rect_h,
            group_ids=[group_id], frame_id=frame_id
        ),
        make_text(
            f"t-d-{group_id}", f"##{number:03d}",
            rect_x + 10, rect_y + 10, 60, 30,
            group_ids=[group_id], frame_id=frame_id
        ),
        make_text(
            f"n-d-{group_id}", f"#{name}",
            rect_x + 80, rect_y + 10, rect_w - 100, 30,
            group_ids=[group_id], frame_id=frame_id
        ),
        make_text(
            f"desc-d-{group_id}", description,
            rect_x + 10, rect_y + 60, rect_w - 30, rect_h - 80,
            group_ids=[group_id], frame_id=frame_id
        ),
    ]


def cell_origin(row, col,
                 cell_w=DEFAULT_CELL_W, cell_h=DEFAULT_CELL_H,
                 offset_x=DEFAULT_OFFSET_X, offset_y=DEFAULT_OFFSET_Y):
    """Координаты левого верхнего угла клетки (row, col)."""
    return (offset_x + (col - 1) * cell_w,
            offset_y + (row - 1) * cell_h)


def make_table_frame(name="Таблица 500x300",
                      num_rows=3, num_cols=3,
                      cell_w=DEFAULT_CELL_W, cell_h=DEFAULT_CELL_H,
                      offset_x=DEFAULT_OFFSET_X, offset_y=DEFAULT_OFFSET_Y,
                      frame_id="frame-table"):
    """Создать Frame таблицы указанного размера."""
    width = num_cols * cell_w + offset_x * 2
    height = num_rows * cell_h + offset_y * 2
    return make_frame(frame_id, name, 0, 0, width, height)


def make_description_frame(name="Описание",
                            x=2000, y=0,
                            width=600, height=900,
                            frame_id="frame-desc"):
    """Frame описаний."""
    return make_frame(frame_id, name, x, y, width, height)


def make_test_grid(skills=None, descriptions=None,
                    num_rows=3, num_cols=3,
                    cell_w=DEFAULT_CELL_W, cell_h=DEFAULT_CELL_H):
    """
    Создать тестовую таблицу.

    skills: список (row, col, number, name) для навыков
    descriptions: список (number, name, description_text) для описаний
    """
    skills = skills or []
    descriptions = descriptions or []

    elements = [make_table_frame(
        num_rows=num_rows, num_cols=num_cols,
        cell_w=cell_w, cell_h=cell_h
    )]

    # Навыки
    for i, (row, col, number, name) in enumerate(skills, start=1):
        x, y = cell_origin(row, col, cell_w, cell_w)
        # Используем cell_w/cell_h по факту
        x, y = cell_origin(row, col, cell_w, cell_h)
        group_id = f"skill-{number:03d}"
        elements.extend(make_skill_group(
            group_id, number, name, x, y,
            cell_w=cell_w, cell_h=cell_h
        ))

    elements.append(make_description_frame(
        height=max(900, len(descriptions) * 250)
    ))

    # Описания
    for i, (number, name, desc_text) in enumerate(descriptions, start=1):
        x = 25 + 2000
        y = 25 + (i - 1) * 250
        group_id = f"desc-{number:03d}"
        elements.extend(make_description_group(
            group_id, number, name, desc_text, x, y,
            cell_w=cell_w - 50, cell_h=cell_h - 50
        ))

    return elements


def make_excalidraw_file(elements, suffix=".excalidraw"):
    """Создать .excalidraw файл и вернуть Path."""
    path = Path(tempfile.mkstemp(suffix=suffix)[1])
    data = {
        "type": "excalidraw",
        "version": 2,
        "source": "test",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff"},
        "files": {},
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path