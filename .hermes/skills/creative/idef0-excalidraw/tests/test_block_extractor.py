"""Тесты BlockExtractor."""
import unittest
from pathlib import Path

from conftest import (
    make_simple_diagram, write_excalidraw_file,
    make_rectangle, make_text
)
from block_extractor import BlockExtractor


class TestBlockExtractorBasic(unittest.TestCase):
    """Базовые тесты извлечения блоков."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_simple_diagram())
        from excalidraw_parser import ExcalidrawParser
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_extract_finds_all_blocks(self):
        ex = BlockExtractor(self.parser.elements)
        blocks = ex.extract_all_blocks()
        # simple_diagram: 2 блока
        self.assertEqual(len(blocks), 2)

    def test_block_has_required_fields(self):
        ex = BlockExtractor(self.parser.elements)
        blocks = ex.extract_all_blocks()
        for block in blocks:
            for field in ['group_id', 'rectangle_id', 'func_text_id',
                          'num_text_id', 'name', 'number', 'x', 'y',
                          'width', 'height', 'frame_id']:
                self.assertIn(field, block, f"Missing field: {field}")

    def test_block_numbers_extracted(self):
        ex = BlockExtractor(self.parser.elements)
        blocks = ex.extract_all_blocks()
        numbers = sorted([b['number'] for b in blocks])
        self.assertEqual(numbers, ['A0.1', 'A0.2'])

    def test_block_names_extracted(self):
        ex = BlockExtractor(self.parser.elements)
        blocks = ex.extract_all_blocks()
        names = sorted([b['name'] for b in blocks])
        self.assertEqual(names, ['Разработка', 'Тестирование'])

    def test_blocks_sorted_by_number(self):
        # По sort key: A0.1 < A0.2
        ex = BlockExtractor(self.parser.elements)
        blocks = ex.extract_all_blocks()
        self.assertEqual(blocks[0]['number'], 'A0.1')
        self.assertEqual(blocks[1]['number'], 'A0.2')

    def test_block_frame_id(self):
        ex = BlockExtractor(self.parser.elements)
        blocks = ex.extract_all_blocks()
        for block in blocks:
            self.assertEqual(block['frame_id'], 'frame-1')


class TestBlockExtractorEdgeCases(unittest.TestCase):
    """Крайние случаи."""

    def test_empty_elements(self):
        ex = BlockExtractor([])
        self.assertEqual(ex.extract_all_blocks(), [])

    def test_only_rectangle_no_text(self):
        """Только rectangle без текстов — не должно быть блоком."""
        tmp = write_excalidraw_file([
            make_rectangle("r1", group_ids=["g1"])
        ])
        try:
            ex = BlockExtractor([
                {"id": "r1", "type": "rectangle",
                 "groupIds": ["g1"], "x": 0, "y": 0,
                 "width": 100, "height": 100}
            ])
            blocks = ex.extract_all_blocks()
            self.assertEqual(blocks, [])
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_two_texts_no_rectangle(self):
        """Два текста без rectangle — не блок."""
        tmp = write_excalidraw_file([
            make_text("t1", "Функция", group_ids=["g1"]),
            make_text("t2", "1.1", group_ids=["g1"]),
        ])
        try:
            ex = BlockExtractor([
                {"id": "t1", "type": "text", "text": "Функция",
                 "groupIds": ["g1"]},
                {"id": "t2", "type": "text", "text": "1.1",
                 "groupIds": ["g1"]},
            ])
            self.assertEqual(ex.extract_all_blocks(), [])
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_minimal_block_rect_plus_func(self):
        """Минимальный блок: rectangle + func text (без номера)."""
        elems = [
            {"id": "r", "type": "rectangle", "x": 0, "y": 0,
             "width": 100, "height": 100, "groupIds": ["g"]},
            {"id": "f", "type": "text", "text": "Функция",
             "x": 10, "y": 40, "width": 80, "height": 20,
             "groupIds": ["g"]},
        ]
        ex = BlockExtractor(elems)
        blocks = ex.extract_all_blocks()
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['name'], 'Функция')
        self.assertEqual(blocks[0]['number'], '')


class TestBlockExtractorLookalikeNumber(unittest.TestCase):
    """Тесты эвристики _looks_like_number."""

    def test_simple_number(self):
        ex = BlockExtractor([])
        self.assertTrue(ex._looks_like_number("1.2"))
        self.assertTrue(ex._looks_like_number("A1.2"))
        self.assertTrue(ex._looks_like_number("A-0.1"))
        self.assertTrue(ex._looks_like_number("123"))

    def test_function_text(self):
        ex = BlockExtractor([])
        self.assertFalse(ex._looks_like_number("Разработка чертежей"))
        self.assertFalse(ex._looks_like_number("Тест"))

    def test_too_long_is_not_number(self):
        ex = BlockExtractor([])
        # Больше 10 символов — не номер
        self.assertFalse(ex._looks_like_number("1.2345678901"))

    def test_empty(self):
        ex = BlockExtractor([])
        self.assertFalse(ex._looks_like_number(""))


class TestBlockExtractorFindByNumber(unittest.TestCase):
    """Тесты поиска блоков."""

    def setUp(self):
        from excalidraw_parser import ExcalidrawParser
        self.tmp = write_excalidraw_file(make_simple_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        self.ex = BlockExtractor(self.parser.elements)
        self.blocks = self.ex.extract_all_blocks()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_find_existing(self):
        block = self.ex.find_block_by_number(self.blocks, "A0.1")
        self.assertIsNotNone(block)
        self.assertEqual(block['name'], 'Разработка')

    def test_find_unknown(self):
        block = self.ex.find_block_by_number(self.blocks, "X9.9")
        self.assertIsNone(block)


class TestBlockExtractorFindById(unittest.TestCase):
    """Поиск по ID."""

    def setUp(self):
        from excalidraw_parser import ExcalidrawParser
        self.tmp = write_excalidraw_file(make_simple_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        self.ex = BlockExtractor(self.parser.elements)
        self.blocks = self.ex.extract_all_blocks()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_find_by_rectangle_id(self):
        block = self.ex.find_block_by_id(
            self.blocks, "rect-group-A0-1"
        )
        self.assertIsNotNone(block)

    def test_find_by_func_text_id(self):
        block = self.ex.find_block_by_id(
            self.blocks, "func-group-A0-1"
        )
        self.assertIsNotNone(block)

    def test_find_by_num_text_id(self):
        block = self.ex.find_block_by_id(
            self.blocks, "num-group-A0-1"
        )
        self.assertIsNotNone(block)

    def test_find_unknown_id(self):
        block = self.ex.find_block_by_id(self.blocks, "nonexistent")
        self.assertIsNone(block)


class TestBlockExtractorParseNumberForSort(unittest.TestCase):
    """Тесты парсинга номеров для сортировки."""

    def test_simple_numbers(self):
        ex = BlockExtractor([])
        # A1.2 -> ("A1", 2, "")
        key = ex._parse_number_for_sort("A1.2")
        self.assertEqual(key[1], 2)

    def test_letter_suffix(self):
        ex = BlockExtractor([])
        # Требуется префикс [A-]+ для работы regex сортировки
        key = ex._parse_number_for_sort("A1.2a")
        self.assertEqual(key[2], "a")

    def test_sort_order(self):
        ex = BlockExtractor([])
        # A0.1 < A0.2 < A1.1
        k1 = ex._parse_number_for_sort("A0.1")
        k2 = ex._parse_number_for_sort("A0.2")
        k3 = ex._parse_number_for_sort("A1.1")
        self.assertLess(k1, k2)
        self.assertLess(k2, k3)


if __name__ == '__main__':
    unittest.main()
