"""Тесты grid_parser.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from grid_parser import (
    parse_table_frame_name, is_table_frame, is_entity_number,
    is_skill_name_in_table, is_description_name,
    find_table_frame, group_by_group_id, element_in_frame,
)


class TestParseTableFrameName:
    def test_basic(self):
        assert parse_table_frame_name("Таблица 500x300") == (500, 300)

    def test_russian_x(self):
        assert parse_table_frame_name("Таблица 500х300") == (500, 300)

    def test_uppercase(self):
        assert parse_table_frame_name("Таблица 500X300") == (500, 300)

    def test_capital_x(self):
        assert parse_table_frame_name("Таблица 500Х300") == (500, 300)

    def test_with_spaces(self):
        assert parse_table_frame_name("  Таблица  500 x 300  ") == (500, 300)

    def test_invalid(self):
        assert parse_table_frame_name("Table 500x300") is None
        assert parse_table_frame_name("Таблица") is None
        assert parse_table_frame_name("") is None
        assert parse_table_frame_name("Таблица abc") is None

    def test_numbers(self):
        assert parse_table_frame_name("Таблица 100x200")[0] == 100
        assert parse_table_frame_name("Таблица 100x200")[1] == 200


class TestIsEntityNumber:
    def test_double_hash(self):
        assert is_entity_number("##001") == "001"

    def test_single_hash(self):
        assert is_entity_number("#42") == "42"

    def test_with_spaces(self):
        assert is_entity_number("## 001") == "001"
        assert is_entity_number("  ##001  ") == "001"

    def test_invalid(self):
        assert is_entity_number("001") is None
        assert is_entity_number("##abc") is None
        assert is_entity_number("##") is None
        assert is_entity_number("#Name") is None  # имя, не номер
        assert is_entity_number("") is None


class TestIsSkillNameInTable:
    def test_valid(self):
        assert is_skill_name_in_table("Git синхронизация") is True
        assert is_skill_name_in_table("Parser") is True

    def test_starts_with_hash_invalid(self):
        assert is_skill_name_in_table("#Name") is False
        assert is_skill_name_in_table("##001") is False

    def test_empty(self):
        assert is_skill_name_in_table("") is False
        assert is_skill_name_in_table("   ") is False

    def test_too_long(self):
        assert is_skill_name_in_table("x" * 201) is False


class TestIsDescriptionName:
    def test_valid(self):
        assert is_description_name("#Git синхронизация") is True
        assert is_description_name("#Parser") is True

    def test_bare_hash_invalid(self):
        # Просто "#" без текста — не имя
        assert is_description_name("#") is False

    def test_number_invalid(self):
        # ##NNN — это номер, не имя
        assert is_description_name("##001") is False

    def test_no_hash_invalid(self):
        assert is_description_name("Name") is False

    def test_empty(self):
        assert is_description_name("") is False


class TestFindTableFrame:
    def test_found(self):
        elements = [
            {"id": "f1", "type": "frame", "name": "Таблица 500x300",
             "x": 0, "y": 0, "width": 1500, "height": 900},
            {"id": "r1", "type": "rectangle", "x": 10, "y": 10,
             "width": 100, "height": 50},
        ]
        frame = find_table_frame(elements)
        assert frame is not None
        assert frame["id"] == "f1"

    def test_not_found(self):
        elements = [
            {"id": "f1", "type": "frame", "name": "Random Frame",
             "x": 0, "y": 0, "width": 100, "height": 100},
        ]
        assert find_table_frame(elements) is None


class TestGroupByGroupId:
    def test_groups(self):
        elements = [
            {"id": "e1", "type": "rectangle", "groupIds": ["g1"]},
            {"id": "e2", "type": "text", "groupIds": ["g1"]},
            {"id": "e3", "type": "rectangle", "groupIds": ["g2"]},
            {"id": "e4", "type": "rectangle"},  # без группы
        ]
        groups = group_by_group_id(elements)
        assert len(groups) == 2
        assert len(groups["g1"]) == 2
        assert len(groups["g2"]) == 1


class TestElementInFrame:
    def test_inside(self):
        frame = {"x": 0, "y": 0, "width": 100, "height": 100}
        el = {"x": 50, "y": 50, "width": 10, "height": 10}
        assert element_in_frame(el, frame) is True

    def test_outside(self):
        frame = {"x": 0, "y": 0, "width": 100, "height": 100}
        el = {"x": 200, "y": 50, "width": 10, "height": 10}
        assert element_in_frame(el, frame) is False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])