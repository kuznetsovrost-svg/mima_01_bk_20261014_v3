"""Тесты SideDetector."""
import unittest
from pathlib import Path

from conftest import (
    make_arrow, make_rectangle, make_binding
)
from arrow_extractor import ArrowExtractor
from side_detector import SideDetector


def arrow_via_extractor(raw_arrow):
    """Преобразовать raw arrow через arrow_extractor (camel -> snake)."""
    return ArrowExtractor([raw_arrow]).extract_all_arrows()[0]


class TestSideDetectorInit(unittest.TestCase):
    """Тесты инициализации."""

    def test_default_tolerance(self):
        d = SideDetector()
        self.assertEqual(d.tolerance, 20)

    def test_custom_tolerance(self):
        d = SideDetector(tolerance=50)
        self.assertEqual(d.tolerance, 50)


class TestSideDetectorDetectSide(unittest.TestCase):
    """Тесты detect_side."""

    def setUp(self):
        self.block = make_rectangle("b1", x=100, y=100,
                                    width=200, height=100)
        self.detector = SideDetector()

    def test_detect_left(self):
        raw = make_arrow("a", x=50, y=100, width=50, height=0,
                         points=[[0, 0], [50, 0]],
                         end_binding=make_binding("b1"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'left')

    def test_detect_right(self):
        raw = make_arrow("a", x=250, y=200, width=50, height=0,
                         points=[[0, 0], [50, 0]],
                         end_binding=make_binding("b1"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'right')

    def test_detect_top(self):
        raw = make_arrow("a", x=200, y=50, width=0, height=50,
                         points=[[0, 0], [0, 50]],
                         end_binding=make_binding("b1"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'top')

    def test_detect_bottom(self):
        raw = make_arrow("a", x=200, y=150, width=0, height=50,
                         points=[[0, 0], [0, 50]],
                         end_binding=make_binding("b1"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'bottom')

    def test_detect_unknown_when_far(self):
        raw = make_arrow("a", x=1000, y=1000, width=10, height=10,
                         points=[[0, 0], [10, 0]],
                         end_binding=make_binding("b1"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'unknown')

    def test_detect_unknown_no_binding(self):
        raw = make_arrow("a", points=[[0, 0], [10, 0]])
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'unknown')

    def test_detect_unknown_other_block(self):
        raw = make_arrow("a", x=100, y=100, width=50, height=0,
                         points=[[0, 0], [50, 0]],
                         end_binding=make_binding("other-block"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'unknown')

    def test_no_points_returns_unknown(self):
        raw = make_arrow("a", points=[],
                         end_binding=make_binding("b1"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'unknown')


class TestSideDetectorDetectRole(unittest.TestCase):
    """Маппинг side -> ICOM."""

    def setUp(self):
        self.d = SideDetector()

    def test_left_to_input(self):
        self.assertEqual(self.d.detect_role('left'), 'input')

    def test_right_to_output(self):
        self.assertEqual(self.d.detect_role('right'), 'output')

    def test_top_to_control(self):
        self.assertEqual(self.d.detect_role('top'), 'control')

    def test_bottom_to_mechanism(self):
        self.assertEqual(self.d.detect_role('bottom'), 'mechanism')

    def test_unknown_role(self):
        self.assertEqual(self.d.detect_role('unknown'), 'unknown')


class TestSideDetectorStartBinding(unittest.TestCase):
    """Стрелка привязана НАЧАЛОМ к блоку."""

    def setUp(self):
        self.block = make_rectangle("b1", x=100, y=100,
                                    width=200, height=100)
        self.detector = SideDetector()

    def test_start_at_left(self):
        raw = make_arrow("a", x=100, y=100, width=50, height=0,
                         points=[[0, 0], [50, 0]],
                         start_binding=make_binding("b1"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'left')

    def test_start_at_top(self):
        raw = make_arrow("a", x=200, y=100, width=0, height=50,
                         points=[[0, 0], [0, 50]],
                         start_binding=make_binding("b1"))
        arrow = arrow_via_extractor(raw)
        side = self.detector.detect_side(arrow, self.block)
        self.assertEqual(side, 'top')


if __name__ == '__main__':
    unittest.main()
