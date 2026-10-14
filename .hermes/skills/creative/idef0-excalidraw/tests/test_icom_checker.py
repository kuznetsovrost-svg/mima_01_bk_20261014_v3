"""Тесты ICOMChecker."""
import unittest
from pathlib import Path

from conftest import (
    make_simple_diagram, make_inconsistent_diagram,
    write_excalidraw_file, make_binding
)
from excalidraw_parser import ExcalidrawParser
from block_extractor import BlockExtractor
from arrow_extractor import ArrowExtractor
from icom_checker import ICOMChecker


class TestICOMCheckerInit(unittest.TestCase):
    """Тесты инициализации."""

    def test_init_stores_params(self):
        checker = ICOMChecker([], [], [])
        self.assertEqual(checker.blocks, [])
        self.assertEqual(checker.arrows, [])
        self.assertEqual(checker.frames, [])


class TestICOMCheckerFindChildFrame(unittest.TestCase):
    """Тесты find_child_frame."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_inconsistent_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()
        self.checker = ICOMChecker(blocks, arrows, self.parser.frames)

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_find_child_frame_by_parent_marker(self):
        # A0.1 должен найти "A1 (parent: A0-1)"
        child = self.checker.find_child_frame("rect-group-parent")
        self.assertIsNotNone(child)
        self.assertEqual(child["id"], "frame-child")

    def test_find_child_frame_no_match(self):
        child = self.checker.find_child_frame("nonexistent")
        self.assertIsNone(child)


class TestICOMCheckerCheckConsistency(unittest.TestCase):
    """Тесты check_consistency."""

    def setUp(self):
        self.tmp = write_excalidraw_file(make_inconsistent_diagram())
        self.parser = ExcalidrawParser(self.tmp)
        self.parser.load()
        blocks = BlockExtractor(self.parser.elements).extract_all_blocks()
        arrows = ArrowExtractor(self.parser.elements).extract_all_arrows()
        self.checker = ICOMChecker(blocks, arrows, self.parser.frames)

    def tearDown(self):
        Path(self.tmp).unlink(missing_ok=True)

    def test_returns_list(self):
        errors = self.checker.check_consistency("rect-group-parent")
        self.assertIsInstance(errors, list)

    def test_parent_not_found_returns_error(self):
        errors = self.checker.check_consistency("nonexistent")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["type"], "parent_block_not_found")

    def test_inconsistent_detects_missing(self):
        """Parent имеет C1, child не имеет → missing_in_child."""
        errors = self.checker.check_consistency("rect-group-parent")
        missing_errors = [
            e for e in errors if e.get("type") == "missing_in_child"
        ]
        self.assertGreater(len(missing_errors), 0)

    def test_inconsistent_detects_extra(self):
        """Child имеет M1, parent не имеет → extra_in_child."""
        errors = self.checker.check_consistency("rect-group-parent")
        extra_errors = [
            e for e in errors if e.get("type") == "extra_in_child"
        ]
        self.assertGreater(len(extra_errors), 0)

    def test_errors_have_severity(self):
        errors = self.checker.check_consistency("rect-group-parent")
        for err in errors:
            self.assertIn("severity", err)
            self.assertIn(err["severity"], ["error", "warning", "info"])

    def test_errors_have_message(self):
        errors = self.checker.check_consistency("rect-group-parent")
        for err in errors:
            self.assertIn("message", err)
            self.assertIsInstance(err["message"], str)



if __name__ == '__main__':
    unittest.main()
