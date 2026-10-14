"""Тесты ArrowExtractor."""
import unittest
from pathlib import Path

from conftest import (
    make_binding,
    make_simple_diagram, make_diagram_with_tunnels,
    write_excalidraw_file, make_arrow
)
from arrow_extractor import ArrowExtractor


class TestArrowExtractorBasic(unittest.TestCase):
    """Базовые тесты."""

    def setUp(self):
        from excalidraw_parser import ExcalidrawParser
        self.tmp = write_excalidraw_file(make_simple_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_extract_count(self):
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        self.assertEqual(len(arrows), 4)

    def test_arrow_has_required_fields(self):
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        for arrow in arrows:
            for field in ['id', 'points', 'x', 'y', 'width', 'height',
                          'text', 'arrow_name', 'is_tunneled',
                          'tunnel_side', 'start_binding', 'end_binding',
                          'frame_id']:
                self.assertIn(field, arrow)

    def test_arrow_names(self):
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        names = sorted([a['arrow_name'] for a in arrows])
        self.assertEqual(names, ['C1', 'I1', 'M1', 'O1'])

    def test_no_tunnels(self):
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        for arrow in arrows:
            self.assertFalse(arrow['is_tunneled'])
            self.assertIsNone(arrow['tunnel_side'])

    def test_arrow_full_text(self):
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        i1 = next(a for a in arrows if a['arrow_name'] == 'I1')
        self.assertEqual(i1['full_text'], 'I1 требования')


class TestArrowExtractorTunnelParsing(unittest.TestCase):
    """Тесты парсинга туннелей."""

    def setUp(self):
        from excalidraw_parser import ExcalidrawParser
        self.tmp = write_excalidraw_file(make_diagram_with_tunnels())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_count_tunnels(self):
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        # 3 стрелки, все туннели
        self.assertEqual(len(arrows), 3)
        tunneled = [a for a in arrows if a['is_tunneled']]
        self.assertEqual(len(tunneled), 3)

    def test_single_end_tunnel(self):
        # "( I1 входной документ" — скобка в начале → туннель на конце
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        t1 = next(a for a in arrows if a['id'] == 'arrow-T1')
        self.assertTrue(t1['is_tunneled'])
        self.assertEqual(t1['tunnel_side'], 'end')
        # Имя очищено от скобок
        self.assertEqual(t1['arrow_name'], 'I1')

    def test_double_tunnel(self):
        # "( O1 результат )" — скобки с обеих сторон
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        t2 = next(a for a in arrows if a['id'] == 'arrow-T2')
        self.assertTrue(t2['is_tunneled'])
        self.assertEqual(t2['tunnel_side'], 'both')
        self.assertEqual(t2['arrow_name'], 'O1')

    def test_single_start_tunnel(self):
        # "C1 управление )" — скобка в конце → туннель на начале
        ex = ArrowExtractor(self.parser.elements)
        arrows = ex.extract_all_arrows()
        t3 = next(a for a in arrows if a['id'] == 'arrow-T3')
        self.assertTrue(t3['is_tunneled'])
        self.assertEqual(t3['tunnel_side'], 'start')


class TestArrowExtractorAttachments(unittest.TestCase):
    """Тесты привязки стрелок."""

    def setUp(self):
        from excalidraw_parser import ExcalidrawParser
        self.tmp = write_excalidraw_file(make_simple_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        self.ex = ArrowExtractor(self.parser.elements)
        self.arrows = self.ex.extract_all_arrows()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_arrows_attached_to_block(self):
        attached = self.ex.get_arrows_attached_to_block(
            self.arrows, "rect-group-A0-1"
        )
        # I1, O1, C1, M1 — все 4 привязаны к A0.1
        self.assertEqual(len(attached), 4)

    def test_arrows_attached_to_block_2(self):
        attached = self.ex.get_arrows_attached_to_block(
            self.arrows, "rect-group-A0-2"
        )
        # Только O1 привязан к A0.2 (как конец)
        self.assertEqual(len(attached), 1)
        self.assertEqual(attached[0]['arrow_name'], 'O1')

    def test_arrows_attached_to_unknown_block(self):
        attached = self.ex.get_arrows_attached_to_block(
            self.arrows, "rect-unknown"
        )
        self.assertEqual(attached, [])


class TestArrowExtractorNameExtraction(unittest.TestCase):
    """Тесты _extract_arrow_name."""

    def test_basic(self):
        ex = ArrowExtractor([])
        self.assertEqual(ex._extract_arrow_name("I1 требования"), "I1")
        self.assertEqual(ex._extract_arrow_name("O1"), "O1")
        self.assertEqual(ex._extract_arrow_name("A12"), "A12")

    def test_strip_parens(self):
        ex = ArrowExtractor([])
        # Скобки должны быть удалены ДО split
        name = ex._extract_arrow_name("( I1 входной документ")
        self.assertEqual(name, "I1")

    def test_empty(self):
        ex = ArrowExtractor([])
        self.assertEqual(ex._extract_arrow_name(""), "")


class TestArrowExtractorFreeEnd(unittest.TestCase):
    """Тесты _find_free_end."""

    def _raw_to_extracted(self, raw):
        """Преобразовать raw arrow через ArrowExtractor."""
        return ArrowExtractor([raw]).extract_all_arrows()[0]

    def test_start_free(self):
        raw = make_arrow("a", x=100, y=100, width=50, height=0,
                         points=[[0, 0], [50, 0]],
                         end_binding={"elementId": "x",
                                      "focus": 0, "gap": 1})
        arrow = self._raw_to_extracted(raw)
        ex = ArrowExtractor([])
        end = ex._find_free_end(arrow)
        # start свободен → (100, 100)
        self.assertEqual(end, (100, 100))

    def test_end_free(self):
        raw = make_arrow("a", x=100, y=100, width=50, height=0,
                         points=[[0, 0], [50, 0]],
                         start_binding={"elementId": "x",
                                        "focus": 0, "gap": 1})
        arrow = self._raw_to_extracted(raw)
        ex = ArrowExtractor([])
        end = ex._find_free_end(arrow)
        # end свободен → (150, 100)
        self.assertEqual(end, (150, 100))

    def test_both_bound(self):
        raw = make_arrow("a", points=[[0, 0], [50, 0]],
                         start_binding={"elementId": "x",
                                        "focus": 0, "gap": 1},
                         end_binding={"elementId": "y",
                                      "focus": 0, "gap": 1})
        arrow = self._raw_to_extracted(raw)
        ex = ArrowExtractor([])
        self.assertIsNone(ex._find_free_end(arrow))

    def test_no_points(self):
        raw = make_arrow("a", points=[])
        arrow = self._raw_to_extracted(raw)
        ex = ArrowExtractor([])
        self.assertIsNone(ex._find_free_end(arrow))


if __name__ == '__main__':
    unittest.main()
