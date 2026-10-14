"""Фикстуры для тестов idef0-excalidraw."""
import sys
import json
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def make_rectangle(eid, x=0, y=0, width=200, height=100, group_ids=None,
                   frame_id=None):
    """Создать rectangle элемент."""
    return {
        "id": eid,
        "type": "rectangle",
        "x": x, "y": y,
        "width": width, "height": height,
        "groupIds": group_ids or [],
        "frameId": frame_id,
    }


def make_text(eid, text, x=0, y=0, width=100, height=20, group_ids=None,
              frame_id=None):
    """Создать text элемент."""
    return {
        "id": eid,
        "type": "text",
        "x": x, "y": y,
        "width": width, "height": height,
        "text": text,
        "groupIds": group_ids or [],
        "frameId": frame_id,
    }


def make_frame(eid, name, x=0, y=0, width=400, height=300, frame_id=None):
    """Создать frame элемент."""
    return {
        "id": eid,
        "type": "frame",
        "name": name,
        "x": x, "y": y,
        "width": width, "height": height,
        "frameId": frame_id,
    }


def make_binding(element_id, focus=0, gap=1):
    """Создать startBinding/endBinding."""
    return {"elementId": element_id, "focus": focus, "gap": gap}


def make_arrow(eid, points=None, x=0, y=0, width=100, height=10, text="",
               label="", start_binding=None, end_binding=None,
               frame_id=None):
    """Создать arrow элемент."""
    if points is None:
        points = [[0, 0], [100, 0]]
    return {
        "id": eid,
        "type": "arrow",
        "points": points,
        "x": x, "y": y,
        "width": width, "height": height,
        "text": text,
        "label": label,
        "startBinding": start_binding,
        "endBinding": end_binding,
        "frameId": frame_id,
        "groupIds": [],
    }


def make_block(group_id, x, y, number="A0.1", name="Функция",
               rect_id=None, func_id=None, num_id=None, width=200, height=100,
               frame_id=None):
    """Создать IDEF0 блок (3 элемента в группе)."""
    rect_id = rect_id or f"rect-{group_id}"
    func_id = func_id or f"func-{group_id}"
    num_id = num_id or f"num-{group_id}"

    return [
        make_rectangle(rect_id, x=x, y=y, width=width, height=height,
                       group_ids=[group_id], frame_id=frame_id),
        make_text(func_id, name, x=x + 10, y=y + 40, width=width - 20,
                  height=20, group_ids=[group_id], frame_id=frame_id),
        make_text(num_id, number, x=x + 5, y=y + 5, width=30, height=20,
                  group_ids=[group_id], frame_id=frame_id),
    ]


def make_simple_diagram():
    """
    Создать простую IDEF0 диаграмму (1 frame, 2 блока, 4 стрелки).
    Block A0.1 (x=150,y=200, 200x100).
    Block A0.2 (x=450,y=200, 200x100).
    """
    frame = make_frame("frame-1", "A0", x=50, y=50, width=600, height=400)
    block1 = make_block("group-A0-1", 150, 200, number="A0.1",
                        name="Разработка", frame_id="frame-1")
    block2 = make_block("group-A0-2", 450, 200, number="A0.2",
                        name="Тестирование", frame_id="frame-1")

    arrows = [
        # I1: end (150, 250) — left edge block1
        make_arrow("arrow-I1", points=[[0, 0], [40, 0]],
                   x=110, y=250, width=40, height=0,
                   text="I1 требования",
                   end_binding=make_binding("rect-group-A0-1"),
                   frame_id="frame-1"),
        # O1: start (350, 250) right of block1, end (450, 250) left of block2
        make_arrow("arrow-O1", points=[[0, 0], [100, 0]],
                   x=350, y=250, width=100, height=0,
                   text="O1 чертежи",
                   start_binding=make_binding("rect-group-A0-1"),
                   end_binding=make_binding("rect-group-A0-2"),
                   frame_id="frame-1"),
        # C1: end (250, 200) — top edge block1
        make_arrow("arrow-C1", points=[[0, 0], [0, 100]],
                   x=250, y=100, width=0, height=100,
                   text="C1 стандарты",
                   end_binding=make_binding("rect-group-A0-1"),
                   frame_id="frame-1"),
        # M1: start (250, 300) — bottom edge block1
        make_arrow("arrow-M1", points=[[0, 0], [0, 100]],
                   x=250, y=300, width=0, height=100,
                   text="M1 инженер",
                   start_binding=make_binding("rect-group-A0-1"),
                   frame_id="frame-1"),
    ]

    return [frame] + block1 + block2 + arrows


def make_diagram_with_tunnels():
    """Диаграмма с туннелированными стрелками."""
    frame = make_frame("frame-tun", "A1 (parent: A0.1)", x=50, y=50,
                       width=600, height=400)
    block = make_block("group-A1-1", 250, 200, number="A1.1",
                       name="Подзадача", frame_id="frame-tun")

    arrows = [
        make_arrow("arrow-T1", points=[[0, 0], [50, 0]],
                   x=150, y=250, width=50, height=0,
                   text="( I1 входной документ",
                   end_binding=make_binding("rect-group-A1-1"),
                   frame_id="frame-tun"),
        make_arrow("arrow-T2", points=[[0, 0], [50, 0]],
                   x=350, y=250, width=50, height=0,
                   text="( O1 результат )",
                   start_binding=make_binding("rect-group-A1-1"),
                   frame_id="frame-tun"),
        make_arrow("arrow-T3", points=[[0, 0], [0, 50]],
                   x=350, y=150, width=0, height=50,
                   text="C1 управление )",
                   end_binding=make_binding("rect-group-A1-1"),
                   frame_id="frame-tun"),
    ]

    return [frame] + block + arrows


def make_inconsistent_diagram():
    """Диаграмма с ошибками ICOM consistency."""
    parent_frame = make_frame("frame-parent", "A0 (parent: A-0)",
                              x=50, y=50, width=600, height=400)
    parent_block = make_block("group-parent", 250, 200, number="A0.1",
                              name="Разработка", frame_id="frame-parent")

    child_frame = make_frame("frame-child", "A1 (parent: A0.1)",
                             x=700, y=50, width=600, height=400)
    child_block = make_block("group-child", 850, 200, number="A1.1",
                             name="Анализ", frame_id="frame-child")

    parent_arrows = [
        make_arrow("arrow-pI1", points=[[0, 0], [150, 0]],
                   x=50, y=250, width=150, height=0,
                   text="I1 вход",
                   end_binding=make_binding("rect-group-parent"),
                   frame_id="frame-parent"),
        make_arrow("arrow-pO1", points=[[0, 0], [200, 0]],
                   x=450, y=250, width=200, height=0,
                   text="O1 выход",
                   start_binding=make_binding("rect-group-parent"),
                   frame_id="frame-parent"),
        make_arrow("arrow-pC1", points=[[0, 0], [0, 150]],
                   x=350, y=50, width=0, height=150,
                   text="C1 стандарты",
                   end_binding=make_binding("rect-group-parent"),
                   frame_id="frame-parent"),
    ]

    child_arrows = [
        make_arrow("arrow-cI1", points=[[0, 0], [40, 0]],
                   x=700, y=250, width=40, height=0,
                   text="I1 вход",
                   end_binding=make_binding("rect-group-child"),
                   frame_id="frame-child"),
        make_arrow("arrow-cO1", points=[[0, 0], [40, 0]],
                   x=1260, y=250, width=40, height=0,
                   text="O1 выход",
                   start_binding=make_binding("rect-group-child"),
                   frame_id="frame-child"),
        make_arrow("arrow-cM1", points=[[0, 0], [0, 50]],
                   x=950, y=400, width=0, height=50,
                   text="M1 лишний механизм",
                   start_binding=make_binding("rect-group-child"),
                   frame_id="frame-child"),
    ]

    return ([parent_frame] + parent_block + parent_arrows +
            [child_frame] + child_block + child_arrows)


def write_excalidraw_file(elements, tmp_path=None):
    """Записать .excalidraw файл."""
    if tmp_path is None:
        tmp_path = Path(tempfile.mkstemp(suffix=".excalidraw")[1])
    data = {
        "type": "excalidraw",
        "version": 2,
        "source": "test",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff"},
        "files": {},
    }
    tmp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def fresh_tmp_file(suffix=".excalidraw"):
    """Создать пустой временный файл."""
    return Path(tempfile.mkstemp(suffix=suffix)[1])
