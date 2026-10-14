#!/usr/bin/env python3
"""
Генерация каталога объектов (Arrow Catalogue) для IDEF0 диаграммы.
"""

from typing import Dict, List


class CatalogueGenerator:
    """Генерация таблицы каталога объектов."""

    def __init__(self, blocks: List[Dict], arrows: List[Dict], frame: Dict = None):
        self.blocks = blocks
        self.arrows = arrows
        self.frame = frame

    def generate_catalogue(self) -> List[Dict]:
        """
        Сгенерировать каталог объектов.

        Returns:
            Список словарей {name, source, target, type}.
        """
        from side_detector import SideDetector

        detector = SideDetector()

        catalogue = []

        # Для каждого блока найти привязанные стрелки
        for block in self.blocks:
            block_id = block.get('rectangle_id') or block.get('group_id')
            block_name = block.get('number') or block.get('name', '')

            for arrow in self.arrows:
                side = detector.detect_side(arrow, block)
                if side == 'unknown':
                    continue

                role = detector.detect_role(side)
                arrow_name = arrow.get('arrow_name', '')

                if not arrow_name:
                    continue

                # Определить источник и получатель
                source, target = self._determine_endpoints(
                    arrow, block, side
                )

                catalogue.append({
                    'name': arrow_name,
                    'source': source,
                    'target': target,
                    'type': role.upper(),
                    'is_tunneled': arrow.get('is_tunneled', False)
                })

        return catalogue

    def _determine_endpoints(self, arrow: Dict, block: Dict, side: str) -> tuple:
        """Определить источник и получатель стрелки."""
        start_bound = arrow.get('start_binding')
        end_bound = arrow.get('end_binding')
        block_id = block.get('rectangle_id') or block.get('group_id')

        # Стрелка привязана к блоку — определяем кто источник, кто получатель
        if start_bound and start_bound.get('elementId') == block_id:
            # Начало в этом блоке → это источник
            source = self._block_label(block)
            target = self._other_endpoint(arrow, block_id, is_start=False)
        else:
            # Конец в этом блоке → это получатель
            source = self._other_endpoint(arrow, block_id, is_start=True)
            target = self._block_label(block)

        return source, target

    def _block_label(self, block: Dict) -> str:
        """Метка блока (номер или имя)."""
        number = block.get('number', '')
        name = block.get('name', '')
        if number:
            return number
        return name or '?'

    def _other_endpoint(self, arrow: Dict, current_block_id: str,
                        is_start: bool) -> str:
        """Найти другой конец стрелки."""
        if is_start:
            # Конец стрелки
            end_bound = arrow.get('end_binding')
            if end_bound:
                target_id = end_bound.get('elementId')
                if target_id == current_block_id:
                    return "?"
                return self._find_block_label_by_id(target_id)
            else:
                return "Граница"
        else:
            # Начало стрелки
            start_bound = arrow.get('start_binding')
            if start_bound:
                target_id = start_bound.get('elementId')
                if target_id == current_block_id:
                    return "?"
                return self._find_block_label_by_id(target_id)
            else:
                return "Граница"

    def _find_block_label_by_id(self, block_id: str) -> str:
        """Найти метку блока по ID."""
        for block in self.blocks:
            if (block.get('rectangle_id') == block_id or
                block.get('group_id') == block_id):
                return self._block_label(block)
        return "?"

    def format_catalogue_table(self, catalogue: List[Dict]) -> str:
        """Форматировать каталог как таблицу Markdown."""
        if not catalogue:
            return "Каталог пуст."

        # Убрать дубликаты (стрелка может быть в каталоге дважды
        # если привязана к двум блокам)
        seen = set()
        unique_catalogue = []
        for entry in catalogue:
            key = (entry['name'], entry['source'], entry['target'])
            if key not in seen:
                seen.add(key)
                unique_catalogue.append(entry)

        # Форматирование
        lines = []
        lines.append("| Имя стрелки | Источник | Получатель | Тип |")
        lines.append("|--------------|----------|------------|-----|")

        for entry in unique_catalogue:
            name = entry['name']
            if entry.get('is_tunneled'):
                name = f"(( {name}"  # маркер туннеля
            lines.append(f"| {name} | {entry['source']} | "
                         f"{entry['target']} | {entry['type']} |")

        return "\n".join(lines)


if __name__ == '__main__':
    import sys
    from excalidraw_parser import ExcalidrawParser
    from block_extractor import BlockExtractor
    from arrow_extractor import ArrowExtractor

    if len(sys.argv) < 2:
        print("Usage: catalogue_generator.py <file.excalidraw>")
        sys.exit(1)

    parser = ExcalidrawParser(sys.argv[1])
    if not parser.load():
        sys.exit(1)

    blocks = BlockExtractor(parser.elements).extract_all_blocks()
    arrows = ArrowExtractor(parser.elements).extract_all_arrows()

    generator = CatalogueGenerator(blocks, arrows)
    catalogue = generator.generate_catalogue()
    table = generator.format_catalogue_table(catalogue)

    print(table)
