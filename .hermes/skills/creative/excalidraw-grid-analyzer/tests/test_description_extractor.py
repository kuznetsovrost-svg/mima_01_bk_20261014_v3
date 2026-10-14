"""Тесты description_extractor.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from description_extractor import (
    classify_group_elements, extract_descriptions, DescriptionContent
)


class TestClassifyGroupElements:
    def test_complete_group(self):
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "##001"},
            {"id": "n1", "type": "text", "text": "#Git"},
            {"id": "d1", "type": "text", "text": "Описание навыка"},
        ]
        rect_id, nnn, name, text, text_id = classify_group_elements(group)
        assert rect_id == "r1"
        assert nnn == "001"
        assert name == "#Git"
        assert text == "Описание навыка"
        assert text_id == "d1"

    def test_multiline_description(self):
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "##001"},
            {"id": "n1", "type": "text", "text": "#Git"},
            {"id": "d1", "type": "text", "text": "Line 1\nLine 2\nLine 3"},
        ]
        rect_id, nnn, name, text, text_id = classify_group_elements(group)
        assert "Line 1" in text
        assert "Line 2" in text
        assert text_id == "d1"

    def test_longest_text_is_description(self):
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "##001"},
            {"id": "n1", "type": "text", "text": "#Git"},
            {"id": "s1", "type": "text", "text": "short"},
            {"id": "s2", "type": "text", "text": "this is a much longer text"},
        ]
        _, nnn, name, text, text_id = classify_group_elements(group)
        assert text == "this is a much longer text"
        assert text_id == "s2"

    def test_no_description_text(self):
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "##001"},
            {"id": "n1", "type": "text", "text": "#Git"},
        ]
        rect_id, nnn, name, text, text_id = classify_group_elements(group)
        assert nnn == "001"
        assert name == "#Git"
        assert text is None

    def test_number_not_treated_as_name(self):
        # ##NNN не должно быть именем
        group = [
            {"id": "r1", "type": "rectangle"},
            {"id": "t1", "type": "text", "text": "##001"},
            {"id": "d1", "type": "text", "text": "описание"},
        ]
        _, nnn, name, text, text_id = classify_group_elements(group)
        assert nnn == "001"
        assert name is None  # ##001 не имя
        assert text == "описание"


class TestExtractDescriptions:
    def test_basic(self):
        groups = [
            [
                {"id": "r1", "type": "rectangle", "x": 10, "y": 10,
                 "width": 100, "height": 50, "groupIds": ["g1"]},
                {"id": "t1", "type": "text", "text": "##001",
                 "x": 20, "y": 20, "width": 30, "height": 20,
                 "groupIds": ["g1"]},
                {"id": "n1", "type": "text", "text": "#Git",
                 "x": 60, "y": 20, "width": 50, "height": 20,
                 "groupIds": ["g1"]},
                {"id": "d1", "type": "text", "text": "Description here",
                 "x": 20, "y": 40, "width": 80, "height": 20,
                 "groupIds": ["g1"]},
            ]
        ]
        descs = extract_descriptions(groups)
        assert len(descs) == 1
        assert descs[0].nnn == "001"
        assert descs[0].name == "#Git"
        assert descs[0].text == "Description here"


class TestDescriptionContent:
    def test_complete(self):
        d = DescriptionContent(
            group_id="g", nnn="001", name="#Git", text="desc",
            rectangle_id="r", text_id="t"
        )
        assert d.is_complete() is True

    def test_incomplete_no_text(self):
        d = DescriptionContent(
            group_id="g", nnn="001", name="#Git", text="",
            rectangle_id="r", text_id=None
        )
        assert d.is_complete() is False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])