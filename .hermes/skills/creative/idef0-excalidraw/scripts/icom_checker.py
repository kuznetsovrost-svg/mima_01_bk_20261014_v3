#!/usr/bin/env python3
"""
ICOM Consistency Check — проверка связности parent ↔ child.
"""

import re
from typing import Dict, List, Set, Tuple


class ICOMChecker:
    """Проверка ICOM consistency между parent блоком и child диаграммой."""

    def __init__(self, blocks: List[Dict], arrows: List[Dict], frames: List[Dict]):
        self.blocks = blocks
        self.arrows = arrows
        self.frames = frames

    def find_child_frame(self, parent_block_id: str) -> Dict:
        """
        Найти Frame диаграммы, которая декомпозирует parent блок.
        Ищем по соглашению в имени Frame.
        """
        # Найти parent блок
        parent_block = self._find_block_by_id(parent_block_id)
        if not parent_block:
            return None

        parent_number = parent_block.get('number', '')

        # Ищем Frame который:
        # 1. Содержит parent_number в имени (в parent: <number>)
        # 2. Или содержит этот block_id

        for frame in self.frames:
            name = frame.get('name', '')

            # Формат: "A1 Обработка (parent: A0-2)"
            m = re.search(r'\(parent:\s*([^)]+)\)', name)
            if m and parent_number == m.group(1).strip():
                return frame

            # Frame содержит parent block_id в своих элементах
            # (нужно проверить дочерние элементы frame)
            # Это упрощённая версия

        return None

    def extract_icom_from_block(self, block: Dict) -> Dict[str, Set[str]]:
        """Извлечь ICOM блока по привязанным стрелкам."""
        # Реализация требует side_detector
        # Здесь упрощённая версия — извлечение по связанным стрелкам
        from side_detector import SideDetector

        detector = SideDetector()
        icom = {
            'input': set(),
            'control': set(),
            'output': set(),
            'mechanism': set()
        }

        block_id = block.get('rectangle_id') or block.get('group_id')

        for arrow in self.arrows:
            side = detector.detect_side(arrow, block)
            if side != 'unknown':
                role = detector.detect_role(side)
                arrow_name = arrow.get('arrow_name', '')
                if arrow_name:
                    # Туннелированные стрелки помечаем
                    if arrow.get('is_tunneled'):
                        arrow_name = f"(tunnel) {arrow_name}"
                    icom[role].add(arrow_name)

        return icom

    def extract_icom_from_frame(self, frame: Dict) -> Dict[str, Set[str]]:
        """
        Извлечь ICOM всей диаграммы (граничные стрелки).
        Стрелки с одним свободным концом у границы Frame.
        """
        from arrow_extractor import ArrowExtractor

        extractor = ArrowExtractor(self.arrows)
        boundary_arrows = extractor.get_arrows_at_frame_boundary(
            self.arrows, frame
        )

        icom = {
            'input': set(),
            'control': set(),
            'output': set(),
            'mechanism': set()
        }

        side_to_role = {
            'left': 'input',
            'right': 'output',
            'top': 'control',
            'bottom': 'mechanism'
        }

        for entry in boundary_arrows:
            arrow = entry['arrow']
            side = entry['side']
            role = side_to_role.get(side, None)
            if role:
                arrow_name = arrow.get('arrow_name', '')
                if arrow_name:
                    icom[role].add(arrow_name)

        return icom

    def check_consistency(self, parent_block_id: str) -> List[Dict]:
        """
        Проверить ICOM consistency для пары parent-child.

        Returns:
            Список несоответствий (errors).
        """
        errors = []

        parent_block = self._find_block_by_id(parent_block_id)
        if not parent_block:
            return [{"type": "parent_block_not_found",
                     "block_id": parent_block_id,
                     "severity": "error",
                     "message": f"Parent block {parent_block_id} not found"}]

        child_frame = self.find_child_frame(parent_block_id)
        if not child_frame:
            return [{"type": "child_frame_not_found",
                     "parent_block": parent_block.get('number'),
                     "severity": "warning",
                     "message": "No child Frame found for this block"}]

        # Извлечь ICOM
        parent_icom = self.extract_icom_from_block(parent_block)
        child_icom = self.extract_icom_from_frame(child_frame)

        # Сравнить
        for role in ['input', 'control', 'output', 'mechanism']:
            parent_set = parent_icom[role]
            child_set = child_icom[role]

            missing = parent_set - child_set
            extra = child_set - parent_set

            # Игнорировать туннели в missing
            missing_real = {
                name for name in missing
                if 'tunnel' not in name
            }

            if missing_real:
                errors.append({
                    "type": "missing_in_child",
                    "role": role,
                    "severity": "error",
                    "missing": list(missing_real),
                    "message": f"Стрелки {role} отсутствуют в child: "
                               f"{', '.join(missing_real)}"
                })

            if extra:
                errors.append({
                    "type": "extra_in_child",
                    "role": role,
                    "severity": "warning",
                    "extra": list(extra),
                    "message": f"Лишние стрелки {role} в child: "
                               f"{', '.join(extra)}"
                })

        return errors

    def _find_block_by_id(self, block_id: str) -> Dict:
        """Найти блок по любому из его ID."""
        for block in self.blocks:
            if (block.get('rectangle_id') == block_id or
                block.get('func_text_id') == block_id or
                block.get('num_text_id') == block_id or
                block.get('group_id') == block_id):
                return block
        return None


if __name__ == '__main__':
    import sys
    import json
    from excalidraw_parser import ExcalidrawParser
    from block_extractor import BlockExtractor
    from arrow_extractor import ArrowExtractor

    if len(sys.argv) < 3:
        print("Usage: icom_checker.py <file.excalidraw> <parent_block_id>")
        sys.exit(1)

    parser = ExcalidrawParser(sys.argv[1])
    if not parser.load():
        sys.exit(1)

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()

    checker = ICOMChecker(blocks, arrows, parser.frames)
    errors = checker.check_consistency(sys.argv[2])

    if not errors:
        print("ICOM consistency: OK")
    else:
        print(f"Found {len(errors)} issues:")
        for err in errors:
            print(f"  [{err['severity'].upper()}] {err['message']}")
