"""Тесты CatalogueGenerator."""
import unittest
from pathlib import Path

from conftest import (
    make_simple_diagram, make_diagram_with_tunnels,
    write_excalidraw_file
)
from excalidraw_parser import ExcalidrawParser
from block_extractor import BlockExtractor
from arrow_extractor import ArrowExtractor
from catalogue_generator import CatalogueGenerator


class TestCatalogueGeneratorBasic(unittest.TestCase):
    """Базовые тесты."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_simple_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()
        self.gen = CatalogueGenerator(blocks, arrows)

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_init(self):
        self.assertIsNotNone(self.gen)

    def test_generate_returns_list(self):
        cat = self.gen.generate_catalogue()
        self.assertIsInstance(cat, list)

    def test_generate_not_empty(self):
        cat = self.gen.generate_catalogue()
        self.assertGreater(len(cat), 0)

    def test_catalogue_entry_fields(self):
        cat = self.gen.generate_catalogue()
        for entry in cat:
            for field in ['name', 'source', 'target', 'type', 'is_tunneled']:
                self.assertIn(field, entry)

    def test_types_are_icom(self):
        cat = self.gen.generate_catalogue()
        types = {e['type'] for e in cat}
        # Production code возвращает 'INPUT'/'OUTPUT'/'CONTROL'/'MECHANISM'
        self.assertTrue(
            types.issubset({'INPUT', 'OUTPUT', 'CONTROL', 'MECHANISM'})
        )

class TestCatalogueGeneratorWithTunnels(unittest.TestCase):
    """Каталог с туннелями."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_diagram_with_tunnels())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()
        self.gen = CatalogueGenerator(blocks, arrows)

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_tunneled_flag(self):
        cat = self.gen.generate_catalogue()
        tunneled = [e for e in cat if e['is_tunneled']]
        self.assertGreater(len(tunneled), 0)


class TestCatalogueGeneratorTable(unittest.TestCase):
    """format_catalogue_table."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_simple_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()
        self.gen = CatalogueGenerator(blocks, arrows)

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_table_is_string(self):
        cat = self.gen.generate_catalogue()
        table = self.gen.format_catalogue_table(cat)
        self.assertIsInstance(table, str)

    def test_table_has_header(self):
        cat = self.gen.generate_catalogue()
        table = self.gen.format_catalogue_table(cat)
        self.assertIn("Имя стрелки", table)
        self.assertIn("Источник", table)
        self.assertIn("Получатель", table)
        self.assertIn("Тип", table)

    def test_table_has_separator(self):
        cat = self.gen.generate_catalogue()
        table = self.gen.format_catalogue_table(cat)
        self.assertIn("---", table)

    def test_table_empty_catalogue(self):
        table = self.gen.format_catalogue_table([])
        self.assertIn("пуст", table.lower())

    def test_table_dedup(self):
        # Если добавить дубликаты — должны удалиться
        cat = self.gen.generate_catalogue()
        cat_doubled = cat + cat
        table1 = self.gen.format_catalogue_table(cat)
        table2 = self.gen.format_catalogue_table(cat_doubled)
        # Количество строк одинаково
        lines1 = len(table1.splitlines())
        lines2 = len(table2.splitlines())
        self.assertEqual(lines1, lines2)


class TestCatalogueGeneratorBlockLabel(unittest.TestCase):
    """_block_label."""

    def setUp(self):
        self.gen = CatalogueGenerator([], [])

    def test_label_with_number(self):
        b = {"number": "A1.2", "name": "Разработка"}
        self.assertEqual(self.gen._block_label(b), "A1.2")

    def test_label_without_number(self):
        b = {"number": "", "name": "Разработка"}
        self.assertEqual(self.gen._block_label(b), "Разработка")

    def test_label_empty(self):
        b = {"number": "", "name": ""}
        self.assertEqual(self.gen._block_label(b), "?")


class TestCatalogueGeneratorEmpty(unittest.TestCase):
    """Пустые данные."""

    def test_empty_blocks_and_arrows(self):
        gen = CatalogueGenerator([], [])
        self.assertEqual(gen.generate_catalogue(), [])

    def test_empty_table(self):
        gen = CatalogueGenerator([], [])
        table = gen.format_catalogue_table([])
        self.assertIn("пуст", table.lower())


if __name__ == '__main__':
    unittest.main()
