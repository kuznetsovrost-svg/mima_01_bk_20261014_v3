"""Тесты cell_extractor.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cell_extractor import (
    classify_group_elements, extract_cells, detect_grid_dims, CellContent
)


class TestClassifyGroupElements:
    def test_complete_group(self):
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "##001"},
            {"id": "t2", "type": "text", "text": "Git"},
        ]
        rect_id, nnn, name = classify_group_elements(group)
        assert rect_id == "r1"
        assert nnn == "001"
        assert name == "Git"

    def test_no_number(self):
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "Git"},
        ]
        rect_id, nnn, name = classify_group_elements(group)
        assert rect_id == "r1"
        assert nnn is None
        assert name == "Git"

    def test_no_name(self):
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "##001"},
        ]
        rect_id, nnn, name = classify_group_elements(group)
        assert rect_id == "r1"
        assert nnn == "001"
        assert name is None

    def test_only_rectangle(self):
        group = [
            {"id": "r1", "type": "rectangle"},
        ]
        rect_id, nnn, name = classify_group_elements(group)
        assert rect_id == "r1"
        assert nnn is None
        assert name is None

    def test_name_not_starting_with_hash(self):
        # Если текст начинается с #, это не имя в таблице
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "##001"},
            {"id": "t2", "type": "text", "text": "#BadName"},
        ]
        rect_id, nnn, name = classify_group_elements(group)
        assert nnn == "001"
        assert name is None  # #BadName не считается именем


class TestExtractCells:
    def test_3x3_grid(self):
        groups = [
            # Row 0
            [
                {"id": "r1", "type": "rectangle", "x": 10, "y": 10,
                 "width": 100, "height": 50, "groupIds": ["g1"]},
                {"id": "t1", "type": "text", "text": "##001",
                 "x": 20, "y": 20, "width": 30, "height": 20,
                 "groupIds": ["g1"]},
                {"id": "n1", "type": "text", "text": "Skill1",
                 "x": 20, "y": 40, "width": 80, "height": 20,
                 "groupIds": ["g1"]},
            ],
            # Другие клетки...
        ]
        cells = extract_cells(groups, 500, 300)
        assert len(cells) == 1
        assert cells[0].nnn == "001"
        assert cells[0].name == "Skill1"
        assert cells[0].col == 0
        assert cells[0].row == 0

    def test_empty_groups(self):
        assert extract_cells([], 500, 300) == []


class TestDetectGridDims:
    def test_3x3(self):
        cells = []
        for row in range(3):
            for col in range(3):
                c = CellContent(group_id="g", nnn="001", name="x",
                                rectangle_id="r", col=col, row=row)
                cells.append(c)
        rows, cols = detect_grid_dims(cells)
        assert rows == 3
        assert cols == 3


class TestCellContent:
    def test_complete(self):
        c = CellContent(group_id="g", nnn="001", name="x", rectangle_id="r")
        assert c.is_complete() is True
        assert c.is_empty() is False

    def test_empty(self):
        c = CellContent(group_id="g", nnn=None, name=None, rectangle_id="r")
        assert c.is_complete() is False
        assert c.is_empty() is True


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])