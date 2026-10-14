"""Тесты ExcalidrawParser."""
import unittest
import json
from pathlib import Path

from conftest import (
    make_simple_diagram, write_excalidraw_file,
    make_rectangle, make_text, make_frame
)
from excalidraw_parser import ExcalidrawParser


class TestExcalidrawParserInit(unittest.TestCase):
    """Тесты инициализации."""

    def test_init_stores_file_path(self):
        parser = ExcalidrawParser("/tmp/test.excalidraw")
        self.assertEqual(str(parser.file_path), "/tmp/test.excalidraw")
        self.assertIsNone(parser.data)
        self.assertEqual(parser.elements, [])
        self.assertEqual(parser.frames, [])

    def test_init_default_state(self):
        parser = ExcalidrawParser("x")
        self.assertEqual(parser.frames, [])


class TestExcalidrawParserLoad(unittest.TestCase):
    """Тесты загрузки файла."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_simple_diagram())

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_load_success(self):
        parser = ExcalidrawParser(self.tmp)
        self.assertTrue(parser.load())
        self.assertIsNotNone(parser.data)
        self.assertGreater(len(parser.elements), 0)

    def test_load_nonexistent_file(self):
        parser = ExcalidrawParser("/nonexistent/file.excalidraw")
        self.assertFalse(parser.load())

    def test_load_invalid_json(self):
        tmp = Path("/tmp/bad.excalidraw")
        tmp.write_text("{not valid json", encoding="utf-8")
        try:
            parser = ExcalidrawParser(tmp)
            self.assertFalse(parser.load())
        finally:
            tmp.unlink(missing_ok=True)

    def test_load_extracts_frames(self):
        parser = ExcalidrawParser(self.tmp)
        parser.load()
        self.assertEqual(len(parser.frames), 1)
        self.assertEqual(parser.frames[0]["name"], "A0")
        self.assertEqual(parser.frames[0]["id"], "frame-1")


class TestExcalidrawParserQueries(unittest.TestCase):
    """Тесты методов запросов."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_simple_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_get_elements_in_frame(self):
        elements = self.parser.get_elements_in_frame("frame-1")
        # 2 блока (6 элементов) + 4 стрелки = 10
        self.assertEqual(len(elements), 10)

    def test_get_elements_in_unknown_frame(self):
        elements = self.parser.get_elements_in_frame("nonexistent")
        self.assertEqual(elements, [])

    def test_get_elements_by_type_rectangle(self):
        rects = self.parser.get_elements_by_type("rectangle")
        self.assertEqual(len(rects), 2)

    def test_get_elements_by_type_text(self):
        texts = self.parser.get_elements_by_type("text")
        self.assertEqual(len(texts), 4)

    def test_get_elements_by_type_arrow(self):
        arrows = self.parser.get_elements_by_type("arrow")
        self.assertEqual(len(arrows), 4)

    def test_get_elements_by_type_unknown(self):
        elements = self.parser.get_elements_by_type("diamond")
        self.assertEqual(elements, [])

    def test_get_elements_by_group(self):
        elements = self.parser.get_elements_by_group("group-A0-1")
        self.assertEqual(len(elements), 3)

    def test_get_elements_by_group_unknown(self):
        elements = self.parser.get_elements_by_group("group-XXX")
        self.assertEqual(elements, [])

    def test_get_elements_by_group_multiple_groups(self):
        tmp = write_excalidraw_file([
            make_rectangle("r1", group_ids=["grp1", "extra"])
        ])
        try:
            p = ExcalidrawParser(tmp)
            p.load()
            self.assertEqual(len(p.get_elements_by_group("grp1")), 1)
            self.assertEqual(len(p.get_elements_by_group("extra")), 1)
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_get_all_text_elements(self):
        texts = self.parser.get_all_text_elements()
        self.assertEqual(len(texts), 4)

    def test_get_all_arrows(self):
        arrows = self.parser.get_all_arrows()
        self.assertEqual(len(arrows), 4)


class TestExcalidrawParserSummary(unittest.TestCase):
    """Тесты сводки."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_simple_diagram())

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_summary_keys(self):
        parser = ExcalidrawParser(self.tmp)
        parser.load()
        s = parser.summary()
        for key in ['file', 'total_elements', 'frames', 'rectangles',
                    'texts', 'arrows', 'frame_names']:
            self.assertIn(key, s)

    def test_summary_counts(self):
        parser = ExcalidrawParser(self.tmp)
        parser.load()
        s = parser.summary()
        self.assertEqual(s['frames'], 1)
        self.assertEqual(s['rectangles'], 2)
        self.assertEqual(s['texts'], 4)
        self.assertEqual(s['arrows'], 4)
        self.assertEqual(s['total_elements'], 11)

    def test_summary_frame_names(self):
        parser = ExcalidrawParser(self.tmp)
        parser.load()
        s = parser.summary()
        self.assertEqual(s['frame_names'], ['A0'])


class TestExcalidrawParserEmpty(unittest.TestCase):
    """Тесты пустого файла."""

    def test_empty_diagram(self):
        tmp = write_excalidraw_file([])
        try:
            parser = ExcalidrawParser(tmp)
            parser.load()
            self.assertEqual(len(parser.elements), 0)
            self.assertEqual(len(parser.frames), 0)
            s = parser.summary()
            self.assertEqual(s['total_elements'], 0)
        finally:
            Path(tmp).unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
