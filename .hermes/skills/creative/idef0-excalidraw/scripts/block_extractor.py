#!/usr/bin/env python3
"""
Извлечение IDEF0 блоков из Excalidraw.
Блок = группа из 3 элементов: rectangle + func text + num text.
"""

import re
from typing import Dict, List, Optional, Tuple


class BlockExtractor:
    """Извлечение блоков IDEF0 из элементов Excalidraw."""

    # Паттерн номера блока в IDEF0: A<n>.<m> или просто <n>
    # Примеры: "1", "1.2", "A1.2", "A-0.1", "1.2a"
    BLOCK_NUMBER_PATTERN = re.compile(
        r'^[A]-?\d*\.?\d*[a-z]?$|^[A]-?\d+[a-z]?$|^\d+\.?\d*[a-z]?$'
    )

    def __init__(self, elements: List[Dict]):
        self.elements = elements

    def extract_all_blocks(self) -> List[Dict]:
        """
        Найти все блоки IDEF0 в списке элементов.
        Блок = группа с rectangle, func text, num text.
        """
        # Группируем по groupIds
        groups = {}
        for elem in self.elements:
            for gid in elem.get('groupIds', []):
                if gid not in groups:
                    groups[gid] = []
                groups[gid].append(elem)

        blocks = []
        for gid, group_elems in groups.items():
            block = self._parse_block_group(gid, group_elems)
            if block:
                blocks.append(block)

        # Сортировка по номеру
        blocks.sort(key=lambda b: self._parse_number_for_sort(b.get('number', '')))
        return blocks

    def _parse_block_group(self, group_id: str, elements: List[Dict]) -> Optional[Dict]:
        """Распарсить группу как блок."""
        rectangle = None
        func_text = None
        num_text = None

        for elem in elements:
            if elem.get('type') == 'rectangle':
                rectangle = elem
            elif elem.get('type') == 'text':
                text_content = elem.get('text', '').strip()
                # Эвристика: если текст похож на номер (короткий, цифры/буквы)
                if self._looks_like_number(text_content):
                    num_text = elem
                else:
                    func_text = elem

        # Блок = минимум rectangle + func text
        if not (rectangle and func_text):
            return None

        block = {
            'group_id': group_id,
            'rectangle_id': rectangle.get('id'),
            'func_text_id': func_text.get('id') if func_text else None,
            'num_text_id': num_text.get('id') if num_text else None,
            'name': func_text.get('text', '').strip() if func_text else '',
            'number': num_text.get('text', '').strip() if num_text else '',
            'x': rectangle.get('x', 0),
            'y': rectangle.get('y', 0),
            'width': rectangle.get('width', 0),
            'height': rectangle.get('height', 0),
            'frame_id': rectangle.get('frameId') or func_text.get('frameId')
        }
        return block

    def _looks_like_number(self, text: str) -> bool:
        """Проверить, похож ли текст на номер блока."""
        text = text.strip()
        if not text:
            return False
        # Короткий текст с цифрами и точкой: "1.2", "A1.2", "A-0.1"
        return bool(self.BLOCK_NUMBER_PATTERN.match(text)) and len(text) <= 10

    def _parse_number_for_sort(self, number_str: str) -> Tuple:
        """Парсинг номера для сортировки."""
        # "A1.2" → ("A1", 2)
        # "A-0.1" → ("A-0", 1)
        m = re.match(r'^([A-]+\d*)?\.?(\d+)([a-z]?)$', number_str.strip())
        if m:
            return (m.group(1) or '', int(m.group(2)), m.group(3) or '')
        return (number_str, 0, '')

    def find_block_by_number(self, blocks: List[Dict], number: str) -> Optional[Dict]:
        """Найти блок по его номеру."""
        for block in blocks:
            if block['number'] == number:
                return block
        return None

    def find_block_by_id(self, blocks: List[Dict], block_id: str) -> Optional[Dict]:
        """Найти блок по ID элемента."""
        for block in blocks:
            if (block['rectangle_id'] == block_id or
                block['func_text_id'] == block_id or
                block['num_text_id'] == block_id):
                return block
        return None


if __name__ == '__main__':
    import sys
    import json
    from excalidraw_parser import ExcalidrawParser

    if len(sys.argv) < 2:
        print("Usage: block_extractor.py <file.excalidraw>")
        sys.exit(1)

    parser = ExcalidrawParser(sys.argv[1])
    if not parser.load():
        sys.exit(1)

    extractor = BlockExtractor(parser.elements)
    blocks = extractor.extract_all_blocks()

    print(f"Found {len(blocks)} blocks:")
    for block in blocks:
        print(f"  [{block['number']}] {block['name']} "
              f"(rect at {block['x']},{block['y']} "
              f"{block['width']}x{block['height']}, "
              f"frame: {block.get('frame_id', 'none')})")
