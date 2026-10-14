#!/usr/bin/env python3
"""
Генерация описаний блоков IDEF0 (Node Description).
Гуманизированный текст по стандартному шаблону.
"""

from typing import Dict, List


class DescriptionGenerator:
    """Генерация описаний блоков."""

    def __init__(self, blocks: List[Dict], arrows: List[Dict]):
        self.blocks = blocks
        self.arrows = arrows

    def generate_all_descriptions(self) -> str:
        """
        Сгенерировать описания всех блоков.
        Сортирует блоки по (x, y) — сначала по X, потом по Y.
        """
        if not self.blocks:
            return "Нет блоков для описания."

        # Сортировка: сначала по X (левый), потом по Y (верхний)
        sorted_blocks = sorted(
            self.blocks,
            key=lambda b: (b.get('x', 0), b.get('y', 0))
        )

        descriptions = []
        for block in sorted_blocks:
            desc = self.describe_block(block)
            descriptions.append(desc)

        return "\n\n".join(descriptions)

    def describe_block(self, block: Dict) -> str:
        """Описать один блок по стандартному шаблону."""
        from side_detector import SideDetector

        detector = SideDetector()

        # Собираем стрелки по граням
        icom = {
            'control': [],
            'input': [],
            'output': [],
            'mechanism': []
        }

        block_id = block.get('rectangle_id') or block.get('group_id')

        for arrow in self.arrows:
            side = detector.detect_side(arrow, block)
            if side == 'unknown':
                continue
            role = detector.detect_role(side)
            arrow_name = arrow.get('arrow_name', '')
            if arrow_name:
                if arrow.get('is_tunneled'):
                    arrow_name = f"(( {arrow_name}"
                icom[role].append(arrow_name)

        # Сортировка внутри каждой стороны
        for role in icom:
            icom[role].sort()

        # Генерация текста
        parts = []
        block_label = block.get('number', '') or block.get('name', 'Без имени')
        block_name = block.get('name', '')

        parts.append(f"Блок {block_label}.")
        if block_name and block_name != block_label:
            parts.append(block_name + ".")

        # На основании (Controls)
        if icom['control']:
            parts.append(f"На основании {self._format_list(icom['control'])}")

        # Получает (Inputs)
        if icom['input']:
            parts.append(f"получает {self._format_list(icom['input'])}")

        # Выдаёт (Outputs)
        if icom['output']:
            parts.append(f"выдаёт {self._format_list(icom['output'])}")

        # Опираясь на (Mechanisms)
        if icom['mechanism']:
            parts.append(f"опираясь на {self._format_list(icom['mechanism'])}")

        text = " ".join(parts)
        if not text.endswith('.'):
            text += "."

        return text

    def _format_list(self, items: List[str]) -> str:
        """Форматировать список с правильными союзами."""
        if not items:
            return ""
        if len(items) == 1:
            return f'"{items[0]}"'
        elif len(items) == 2:
            return f'"{items[0]}" и "{items[1]}"'
        else:
            quoted = [f'"{x}"' for x in items]
            return ", ".join(quoted[:-1]) + f' и "{quoted[-1][1:-1]}"'


if __name__ == '__main__':
    import sys
    from excalidraw_parser import ExcalidrawParser
    from block_extractor import BlockExtractor
    from arrow_extractor import ArrowExtractor

    if len(sys.argv) < 2:
        print("Usage: description_generator.py <file.excalidraw>")
        sys.exit(1)

    parser = ExcalidrawParser(sys.argv[1])
    if not parser.load():
        sys.exit(1)

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()

    generator = DescriptionGenerator(blocks, arrows)
    descriptions = generator.generate_all_descriptions()

    print(descriptions)
