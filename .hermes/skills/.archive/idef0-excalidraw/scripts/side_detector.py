#!/usr/bin/env python3
"""
Определение грани стрелки ICOM (left/right/top/bottom).
"""

from typing import Dict, Optional


class SideDetector:
    """Определение грани стрелки при привязке к блоку."""

    TOLERANCE = 20  # px

    def __init__(self, tolerance: int = 20):
        self.tolerance = tolerance

    def detect_side(self, arrow: Dict, block: Dict) -> str:
        """
        Определить грань блока, к которой привязан конец стрелки.

        Args:
            arrow: элемент стрелки из Excalidraw
            block: элемент блока (rectangle)

        Returns:
            "left" | "right" | "top" | "bottom" | "unknown"
        """
        # Определить какой конец стрелки привязан к блоку
        end_x, end_y = self._find_attached_end(arrow, block)

        if end_x is None or end_y is None:
            return "unknown"

        block_x = block.get('x', 0)
        block_y = block.get('y', 0)
        block_w = block.get('width', 0)
        block_h = block.get('height', 0)

        # Грани блока
        left = block_x
        right = block_x + block_w
        top = block_y
        bottom = block_y + block_h

        # Расстояния до граней
        distances = {
            'left': abs(end_x - left),
            'right': abs(end_x - right),
            'top': abs(end_y - top),
            'bottom': abs(end_y - bottom)
        }

        nearest = min(distances, key=distances.get)

        # Проверяем что расстояние действительно близко
        if distances[nearest] > self.tolerance:
            return "unknown"

        return nearest

    def _find_attached_end(self, arrow: Dict, block: Dict) -> tuple:
        """
        Найти координаты конца стрелки, привязанного к блоку.

        Returns:
            (x, y) или (None, None)
        """
        block_id = block.get('id')
        points = arrow.get('points', [])
        if not points:
            return (None, None)

        arrow_x = arrow.get('x', 0)
        arrow_y = arrow.get('y', 0)

        # Проверяем start_binding
        start_binding = arrow.get('start_binding')
        if start_binding and start_binding.get('elementId') == block_id:
            start_x = arrow_x + points[0][0]
            start_y = arrow_y + points[0][1]
            return (start_x, start_y)

        # Проверяем end_binding
        end_binding = arrow.get('end_binding')
        if end_binding and end_binding.get('elementId') == block_id:
            end_x = arrow_x + points[-1][0]
            end_y = arrow_y + points[-1][1]
            return (end_x, end_y)

        return (None, None)

    def detect_role(self, side: str) -> str:
        """Преобразовать грань в ICOM роль."""
        mapping = {
            'left': 'input',
            'right': 'output',
            'top': 'control',
            'bottom': 'mechanism'
        }
        return mapping.get(side, 'unknown')


if __name__ == '__main__':
    import sys
    import json
    from excalidraw_parser import ExcalidrawParser
    from arrow_extractor import ArrowExtractor
    from block_extractor import BlockExtractor

    if len(sys.argv) < 2:
        print("Usage: side_detector.py <file.excalidraw>")
        sys.exit(1)

    parser = ExcalidrawParser(sys.argv[1])
    if not parser.load():
        sys.exit(1)

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()
    detector = SideDetector()

    print(f"Analyzing {len(arrows)} arrows for {len(blocks)} blocks:")

    for arrow in arrows:
        for block in blocks:
            side = detector.detect_side(arrow, block)
            if side != 'unknown':
                role = detector.detect_role(side)
                print(f"  Arrow '{arrow['arrow_name']}' "
                      f"attached to {block['number'] or block['name']} "
                      f"on {side} ({role})")
