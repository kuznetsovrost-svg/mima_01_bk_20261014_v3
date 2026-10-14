#!/usr/bin/env python3
"""
Обнаружение туннелированных стрелок.
Туннель обозначается скобками ( ) в тексте стрелки.
"""

import re
from typing import Dict, List


class TunnelDetector:
    """Обнаружение туннелированных стрелок IDEF0."""

    def __init__(self, arrows: List[Dict]):
        self.arrows = arrows

    def find_all_tunnels(self) -> List[Dict]:
        """Найти все туннелированные стрелки."""
        tunnels = []
        for arrow in self.arrows:
            if arrow.get('is_tunneled'):
                tunnels.append({
                    'arrow_id': arrow.get('id'),
                    'arrow_name': arrow.get('arrow_name'),
                    'full_text': arrow.get('full_text'),
                    'tunnel_side': arrow.get('tunnel_side'),
                    'arrow': arrow
                })
        return tunnels

    def classify_tunnel(self, arrow: Dict) -> str:
        """
        Классифицировать туннель.

        Возвращает:
        - "single_start": скобка только в начале (туннель на конце)
        - "single_end": скобка только в конце (туннель на начале)
        - "double": скобки с обеих сторон
        """
        if not arrow.get('is_tunneled'):
            return "not_tunnel"

        side = arrow.get('tunnel_side', '')
        if side == 'both':
            return "double"
        elif side == 'end':
            return "single_end"
        elif side == 'start':
            return "single_start"
        return "unknown"

    def get_icom_role(self, arrow: Dict) -> str:
        """
        Определить ICOM роль туннелированной стрелки.

        Туннелированная стрелка:
        - на конце блока (side=end): проходит дальше как есть
        - на начале блока (side=start): проходит дальше как есть
        - роль определяется по граню присоединения
        """
        # Это зависит от того, как стрелка присоединена к блоку
        # Упрощение: возвращаем unknown
        return "unknown"

    def explain_tunnel(self, arrow: Dict) -> str:
        """Текстовое объяснение туннеля."""
        side = self.classify_tunnel(arrow)
        name = arrow.get('arrow_name', '')

        if side == "single_end":
            return (f"Стрелка '{name}' — туннель на конце. "
                    f"Она проходит сквозь child диаграмму и "
                    f"должна быть в ICOM листа child.")
        elif side == "single_start":
            return (f"Стрелка '{name}' — туннель на начале. "
                    f"Она проходит сквозь child диаграмму.")
        elif side == "double":
            return (f"Стрелка '{name}' — двойной туннель. "
                    f"Проходит сквозь всю child диаграмму.")
        elif side == "not_tunnel":
            return f"Стрелка '{name}' — обычная, должна быть декомпозирована в child."
        return f"Стрелка '{name}' — туннель ({side})."


if __name__ == '__main__':
    import sys
    from excalidraw_parser import ExcalidrawParser
    from arrow_extractor import ArrowExtractor

    if len(sys.argv) < 2:
        print("Usage: tunnel_detector.py <file.excalidraw>")
        sys.exit(1)

    parser = ExcalidrawParser(sys.argv[1])
    if not parser.load():
        sys.exit(1)

    arrows = ArrowExtractor(parser.elements).extract_all_arrows()
    detector = TunnelDetector(arrows)

    tunnels = detector.find_all_tunnels()
    print(f"Found {len(tunnels)} tunnels:")

    for t in tunnels:
        explanation = detector.explain_tunnel(t['arrow'])
        print(f"  {explanation}")
