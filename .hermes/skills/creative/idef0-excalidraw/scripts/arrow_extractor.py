#!/usr/bin/env python3
"""
Извлечение стрелок ICOM из Excalidraw.
"""

import re
from typing import Dict, List, Optional


class ArrowExtractor:
    """Извлечение стрелок IDEF0."""

    def __init__(self, elements: List[Dict]):
        self.elements = elements

    def extract_all_arrows(self) -> List[Dict]:
        """Извлечь все стрелки с метаданными."""
        arrows = []
        for elem in self.elements:
            if elem.get('type') == 'arrow':
                arrow = self._parse_arrow(elem)
                arrows.append(arrow)
        return arrows

    def _parse_arrow(self, elem: Dict) -> Dict:
        """Распарсить стрелку."""
        text = elem.get('text', '') or ''
        label = elem.get('label', '') or ''

        # Текст стрелки (приоритет text, потом label)
        full_text = text or label

        # Парсинг туннеля
        is_tunneled, tunnel_side = self._parse_tunnel(full_text)

        # Извлечение имени (ICОM-код) — обычно до пробела или скобки
        arrow_name = self._extract_arrow_name(full_text)

        return {
            'id': elem.get('id'),
            'points': elem.get('points', []),
            'x': elem.get('x', 0),
            'y': elem.get('y', 0),
            'width': elem.get('width', 0),
            'height': elem.get('height', 0),
            'text': text,
            'label': label,
            'full_text': full_text,
            'arrow_name': arrow_name,
            'is_tunneled': is_tunneled,
            'tunnel_side': tunnel_side,
            'start_binding': elem.get('startBinding'),
            'end_binding': elem.get('endBinding'),
            'frame_id': elem.get('frameId')
        }

    def _parse_tunnel(self, text: str) -> tuple:
        """
        Определить туннель по скобкам ( ) в тексте.
        Возвращает (is_tunneled, tunnel_side).
        tunnel_side: "start" | "end" | "both" | None
        """
        text = text.strip()
        starts_with_paren = text.startswith('(')
        ends_with_paren = text.endswith(')')

        if starts_with_paren and ends_with_paren:
            return True, 'both'
        elif starts_with_paren:
            return True, 'end'  # скобка в начале = туннель на конце
        elif ends_with_paren:
            return True, 'start'  # скобка в конце = туннель на начале
        else:
            return False, None

    def _extract_arrow_name(self, text: str) -> str:
        """Извлечь имя стрелки (ICOM-код)."""
        # Убрать скобки для чистого имени
        clean = re.sub(r'[()]', '', text).strip()
        # Имя обычно первое слово или до пробела
        parts = clean.split()
        if parts:
            return parts[0]
        return ''

    def get_arrows_attached_to_block(self, arrows: List[Dict], block_id: str) -> List[Dict]:
        """Получить стрелки, привязанные к блоку."""
        attached = []
        for arrow in arrows:
            if (arrow.get('start_binding') and
                arrow['start_binding'].get('elementId') == block_id):
                attached.append(arrow)
            elif (arrow.get('end_binding') and
                  arrow['end_binding'].get('elementId') == block_id):
                attached.append(arrow)
        return attached

    def get_arrows_at_frame_boundary(self, arrows: List[Dict],
                                      frame: Dict) -> List[Dict]:
        """Получить стрелки, чьи свободные концы у границы Frame."""
        boundary_arrows = []
        frame_x = frame.get('x', 0)
        frame_y = frame.get('y', 0)
        frame_w = frame.get('width', 0)
        frame_h = frame.get('height', 0)

        for arrow in arrows:
            # Стрелка внутри frame (или frame_id совпадает)
            if arrow.get('frame_id') != frame.get('id'):
                continue

            # Найти свободный конец
            free_end = self._find_free_end(arrow)
            if free_end is None:
                continue

            fx, fy = free_end
            # Проверяем близость к границе
            TOLERANCE = 20  # px
            on_left = abs(fx - frame_x) < TOLERANCE
            on_right = abs(fx - (frame_x + frame_w)) < TOLERANCE
            on_top = abs(fy - frame_y) < TOLERANCE
            on_bottom = abs(fy - (frame_y + frame_h)) < TOLERANCE

            if on_left or on_right or on_top or on_bottom:
                boundary_arrows.append({
                    'arrow': arrow,
                    'free_end': (fx, fy),
                    'side': self._which_side(fx, fy, frame)
                })

        return boundary_arrows

    def _find_free_end(self, arrow: Dict) -> Optional[tuple]:
        """Найти свободный конец стрелки (не привязанный к блоку)."""
        start_bound = arrow.get('start_binding')
        end_bound = arrow.get('end_binding')

        # Если начало не привязано — это свободный конец
        if not start_bound:
            points = arrow.get('points', [])
            if points:
                start_x = arrow['x'] + points[0][0]
                start_y = arrow['y'] + points[0][1]
                return (start_x, start_y)

        # Если конец не привязан — это свободный конец
        if not end_bound:
            points = arrow.get('points', [])
            if points:
                end_x = arrow['x'] + points[-1][0]
                end_y = arrow['y'] + points[-1][1]
                return (end_x, end_y)

        return None

    def _which_side(self, x: float, y: float, frame: Dict) -> str:
        """Определить грань Frame."""
        frame_x = frame.get('x', 0)
        frame_y = frame.get('y', 0)
        frame_w = frame.get('width', 0)
        frame_h = frame.get('height', 0)

        TOLERANCE = 20
        if abs(x - frame_x) < TOLERANCE:
            return 'left'
        if abs(x - (frame_x + frame_w)) < TOLERANCE:
            return 'right'
        if abs(y - frame_y) < TOLERANCE:
            return 'top'
        if abs(y - (frame_y + frame_h)) < TOLERANCE:
            return 'bottom'
        return 'unknown'


if __name__ == '__main__':
    import sys
    import json
    from excalidraw_parser import ExcalidrawParser

    if len(sys.argv) < 2:
        print("Usage: arrow_extractor.py <file.excalidraw>")
        sys.exit(1)

    parser = ExcalidrawParser(sys.argv[1])
    if not parser.load():
        sys.exit(1)

    extractor = ArrowExtractor(parser.elements)
    arrows = extractor.extract_all_arrows()

    print(f"Found {len(arrows)} arrows:")
    for arrow in arrows:
        tunnel_mark = "TUNNEL" if arrow['is_tunneled'] else "normal"
        bound = ("bound" if arrow['start_binding'] or arrow['end_binding']
                 else "free")
        print(f"  [{arrow['arrow_name']}] {arrow['full_text'][:50]} "
              f"({tunnel_mark}, {bound})")
