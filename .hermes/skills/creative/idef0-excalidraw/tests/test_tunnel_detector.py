"""Тесты TunnelDetector."""
import unittest
from pathlib import Path

from conftest import (
    make_diagram_with_tunnels, make_simple_diagram,
    write_excalidraw_file, make_arrow
)
from arrow_extractor import ArrowExtractor
from tunnel_detector import TunnelDetector


class TestTunnelDetectorFindAll(unittest.TestCase):
    """Тесты find_all_tunnels."""

    def setUp(self):
        from excalidraw_parser import ExcalidrawParser
        self.tmp = write_excalidraw_file(make_diagram_with_tunnels())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        self.arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_count_tunnels(self):
        d = TunnelDetector(self.arrows)
        tunnels = d.find_all_tunnels()
        self.assertEqual(len(tunnels), 3)

    def test_no_tunnels_in_simple(self):
        from excalidraw_parser import ExcalidrawParser
        tmp2 = write_excalidraw_file(make_simple_diagram())
        try:
            p = ExcalidrawParser(tmp2)
            p.load()
            arrows = ArrowExtractor(p.elements).extract_all_arrows()
            d = TunnelDetector(arrows)
            tunnels = d.find_all_tunnels()
            self.assertEqual(tunnels, [])
        finally:
            Path(tmp2).unlink(missing_ok=True)

    def test_tunnel_record_fields(self):
        d = TunnelDetector(self.arrows)
        tunnels = d.find_all_tunnels()
        for t in tunnels:
            for field in ['arrow_id', 'arrow_name', 'full_text',
                          'tunnel_side', 'arrow']:
                self.assertIn(field, t)


class TestTunnelDetectorClassify(unittest.TestCase):
    """Тесты classify_tunnel."""

    def setUp(self):
        from excalidraw_parser import ExcalidrawParser
        self.tmp = write_excalidraw_file(make_diagram_with_tunnels())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        self.arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_classify_not_tunnel(self):
        d = TunnelDetector([])
        self.assertEqual(d.classify_tunnel(
            {"is_tunneled": False, "tunnel_side": None}
        ), "not_tunnel")

    def test_classify_double(self):
        d = TunnelDetector([])
        self.assertEqual(d.classify_tunnel(
            {"is_tunneled": True, "tunnel_side": "both"}
        ), "double")

    def test_classify_single_end(self):
        d = TunnelDetector([])
        # side=end означает скобка в начале текста
        self.assertEqual(d.classify_tunnel(
            {"is_tunneled": True, "tunnel_side": "end"}
        ), "single_end")

    def test_classify_single_start(self):
        d = TunnelDetector([])
        self.assertEqual(d.classify_tunnel(
            {"is_tunneled": True, "tunnel_side": "start"}
        ), "single_start")

    def test_classify_unknown_side(self):
        d = TunnelDetector([])
        self.assertEqual(d.classify_tunnel(
            {"is_tunneled": True, "tunnel_side": "weird"}
        ), "unknown")


class TestTunnelDetectorExplain(unittest.TestCase):
    """Тесты explain_tunnel."""

    def setUp(self):
        from excalidraw_parser import ExcalidrawParser
        self.tmp = write_excalidraw_file(make_diagram_with_tunnels())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        self.arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_explain_single_end(self):
        d = TunnelDetector(self.arrows)
        # arrow-T1 имеет side=end
        t1 = next(a for a in self.arrows if a['id'] == 'arrow-T1')
        expl = d.explain_tunnel(t1)
        self.assertIn("туннель на конце", expl)
        self.assertIn("I1", expl)

    def test_explain_single_start(self):
        d = TunnelDetector(self.arrows)
        t3 = next(a for a in self.arrows if a['id'] == 'arrow-T3')
        expl = d.explain_tunnel(t3)
        self.assertIn("туннель на начале", expl)

    def test_explain_double(self):
        d = TunnelDetector(self.arrows)
        t2 = next(a for a in self.arrows if a['id'] == 'arrow-T2')
        expl = d.explain_tunnel(t2)
        self.assertIn("двойной туннель", expl)

    def test_explain_not_tunnel(self):
        d = TunnelDetector([])
        arrow = {"is_tunneled": False, "tunnel_side": None,
                 "arrow_name": "X1"}
        expl = d.explain_tunnel(arrow)
        self.assertIn("обычная", expl)


if __name__ == '__main__':
    unittest.main()
