#!/usr/bin/env python3
"""
Парсер .excalidraw файлов.
Извлекает структурированное представление диаграммы.
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class ExcalidrawParser:
    """Парсер .excalidraw JSON."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = None
        self.elements = []
        self.frames = []

    def load(self) -> bool:
        """Загрузить и распарсить файл."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.elements = self.data.get('elements', [])
            self.frames = self._extract_frames()
            return True
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading {self.file_path}: {e}")
            return False

    def _extract_frames(self) -> List[Dict]:
        """Найти все Frame элементы."""
        frames = []
        for elem in self.elements:
            if elem.get('type') == 'frame':
                name = elem.get('name', '')
                frames.append({
                    'id': elem.get('id'),
                    'name': name,
                    'x': elem.get('x', 0),
                    'y': elem.get('y', 0),
                    'width': elem.get('width', 0),
                    'height': elem.get('height', 0),
                    'frame_id': elem.get('frameId')
                })
        return frames

    def get_elements_in_frame(self, frame_id: str) -> List[Dict]:
        """Получить все элементы внутри Frame."""
        return [
            elem for elem in self.elements
            if elem.get('frameId') == frame_id
        ]

    def get_elements_by_type(self, elem_type: str) -> List[Dict]:
        """Получить все элементы определённого типа."""
        return [
            elem for elem in self.elements
            if elem.get('type') == elem_type
        ]

    def get_elements_by_group(self, group_id: str) -> List[Dict]:
        """Получить все элементы с данным groupId."""
        return [
            elem for elem in self.elements
            if group_id in elem.get('groupIds', [])
        ]

    def get_all_text_elements(self) -> List[Dict]:
        """Получить все текстовые элементы."""
        return [
            elem for elem in self.elements
            if elem.get('type') == 'text'
        ]

    def get_all_arrows(self) -> List[Dict]:
        """Получить все стрелки."""
        return [
            elem for elem in self.elements
            if elem.get('type') == 'arrow'
        ]

    def summary(self) -> Dict[str, Any]:
        """Получить краткую сводку по диаграмме."""
        return {
            'file': str(self.file_path),
            'total_elements': len(self.elements),
            'frames': len(self.frames),
            'rectangles': len(self.get_elements_by_type('rectangle')),
            'texts': len(self.get_elements_by_type('text')),
            'arrows': len(self.get_elements_by_type('arrow')),
            'frame_names': [f['name'] for f in self.frames]
        }


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: excalidraw_parser.py <file.excalidraw>")
        sys.exit(1)

    parser = ExcalidrawParser(sys.argv[1])
    if parser.load():
        s = parser.summary()
        print(json.dumps(s, indent=2, ensure_ascii=False))
