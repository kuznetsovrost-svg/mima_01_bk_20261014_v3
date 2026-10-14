"""Тесты DescriptionGenerator."""
import unittest
from pathlib import Path

from conftest import (
    make_simple_diagram, write_excalidraw_file
)
from excalidraw_parser import ExcalidrawParser
from block_extractor import BlockExtractor
from arrow_extractor import ArrowExtractor
from description_generator import DescriptionGenerator


class TestDescriptionGeneratorBasic(unittest.TestCase):
    """Базовые тесты."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_simple_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()
        self.gen = DescriptionGenerator(blocks, arrows)

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_generate_all_returns_string(self):
        out = self.gen.generate_all_descriptions()
        self.assertIsInstance(out, str)

    def test_generate_all_not_empty(self):
        out = self.gen.generate_all_descriptions()
        self.assertGreater(len(out), 0)

    def test_describe_block_returns_string(self):
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        desc = self.gen.describe_block(blocks[0])
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)

    def test_description_starts_with_block_label(self):
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        desc = self.gen.describe_block(blocks[0])
        # "Блок A0.1."
        self.assertTrue(desc.startswith("Блок"))

    def test_description_includes_keywords(self):
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        # A0.1 имеет I1, O1, C1, M1 — все 4 роли
        desc = self.gen.describe_block(blocks[0])
        self.assertIn("На основании", desc)
        self.assertIn("получает", desc)
        self.assertIn("выдаёт", desc)
        self.assertIn("опираясь на", desc)

    def test_description_ends_with_dot(self):
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        desc = self.gen.describe_block(blocks[0])
        self.assertTrue(desc.rstrip().endswith("."))

    def test_description_includes_block_name(self):
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        desc = self.gen.describe_block(blocks[0])
        # Должно включать имя блока
        if blocks[0]['name']:
            self.assertIn(blocks[0]['name'], desc)


class TestDescriptionGeneratorFormatList(unittest.TestCase):
    """_format_list приватный, но критичный."""

    def setUp(self):
        self.gen = DescriptionGenerator([], [])

    def test_empty(self):
        self.assertEqual(self.gen._format_list([]), "")

    def test_single(self):
        self.assertEqual(self.gen._format_list(["I1"]), '"I1"')

    def test_two(self):
        self.assertEqual(
            self.gen._format_list(["I1", "I2"]),
            '"I1" и "I2"'
        )

    def test_three(self):
        self.assertEqual(
            self.gen._format_list(["I1", "I2", "I3"]),
            '"I1", "I2" и "I3"'
        )

    def test_many(self):
        # 4+ элемента
        result = self.gen._format_list(["a", "b", "c", "d"])
        self.assertIn('"a"', result)
        self.assertIn('"b"', result)
        self.assertIn('"c"', result)
        self.assertIn('"d"', result)


class TestDescriptionGeneratorBlockOnly(unittest.TestCase):
    """Блок без стрелок."""

    def test_block_no_arrows(self):
        from conftest import make_block
        from block_extractor import BlockExtractor
        elems = make_block("g1", 0, 0, "A0.1", "Функция")
        block = BlockExtractor(elems).extract_all_blocks()[0]
        gen = DescriptionGenerator([block], [])
        desc = gen.describe_block(block)
        self.assertIn("Блок A0.1", desc)
        # Без стрелок — не должно быть "получает" и пр.
        self.assertNotIn("На основании", desc)
        self.assertNotIn("получает", desc)
        self.assertNotIn("выдаёт", desc)


class TestDescriptionGeneratorEmpty(unittest.TestCase):
    """Пустые данные."""

    def test_no_blocks(self):
        gen = DescriptionGenerator([], [])
        out = gen.generate_all_descriptions()
        self.assertIn("Нет блоков", out)


class TestDescriptionGeneratorSorting(unittest.TestCase):
    """Блоки сортируются по (x, y)."""

    def setUp(self):
        from conftest import make_block
        # Создаём 2 блока в разном порядке
        self.tmp = write_excalidraw_file(
            make_block("b-right", 500, 100, "A0.2", "Второй") +
            make_block("b-left", 100, 100, "A0.1", "Первый")
        )
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()
        self.gen = DescriptionGenerator(blocks, arrows)

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_left_block_first(self):
        out = self.gen.generate_all_descriptions()
        # Левый блок должен идти первым
        first_pos = out.find("A0.1")
        second_pos = out.find("A0.2")
        self.assertGreater(second_pos, first_pos)
        self.assertGreater(first_pos, 0)


if __name__ == '__main__':
    unittest.main()
