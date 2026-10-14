"""
description_extractor.py — Извлечение описаний сущностей.

Описание = группа из 4-х элементов ВНЕ Frame таблицы:
1. Прямоугольник (background)
2. ##NNN (номер сущности)
3. #Наименование (начинается с #, не является просто ##NNN)
4. Многострочный текст (описание)

Расположены в произвольном порядке (не сеткой).
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from grid_parser import (
    is_entity_number, is_description_name,
    get_entity_bounds, get_group_center
)


@dataclass
class DescriptionContent:
    """Описание одной сущности."""
    group_id: str
    nnn: Optional[str]
    name: Optional[str]
    text: str
    rectangle_id: Optional[str]
    text_id: Optional[str]
    bounds: Tuple[float, float, float, float] = (0, 0, 0, 0)
    center: Tuple[float, float] = (0, 0)

    def is_complete(self) -> bool:
        """Описание считается полным если есть NNN и имя и текст."""
        return (self.nnn is not None and
                self.name is not None and
                self.text is not None and
                len(self.text) > 0)

    def to_dict(self) -> Dict:
        return {
            'group_id': self.group_id,
            'nnn': self.nnn,
            'name': self.name,
            'text': self.text,
            'rectangle_id': self.rectangle_id,
            'text_id': self.text_id,
            'complete': self.is_complete(),
            'text_length': len(self.text) if self.text else 0,
        }


def classify_group_elements(group: List[Dict]) -> Tuple[Optional[str], Optional[str],
                                                          Optional[str], Optional[str], Optional[str]]:
    """
    Классифицирует элементы группы описания.

    Returns:
        (rectangle_id, nnn, name, text, text_id)

    Логика приоритета для текстов:
    - Если текст = ##NNN → номер
    - Если текст начинается с # и не = ##NNN → имя
    - Иначе → текст описания (выбираем самый длинный текст без #)
    """
    rectangle_id = None
    nnn = None
    name = None
    description_text = None
    text_id = None

    candidates_for_description = []

    for el in group:
        el_type = el.get('type')

        if el_type == 'rectangle':
            if rectangle_id is None:
                rectangle_id = el.get('id')
            continue

        if el_type == 'text':
            text = el.get('text', '').strip()
            if not text:
                continue

            el_id = el.get('id')

            # 1. Номер ##NNN
            extracted_nnn = is_entity_number(text)
            if extracted_nnn and nnn is None:
                nnn = extracted_nnn
                continue

            # 2. Имя (начинается с #, не = ##NNN)
            if is_description_name(text) and name is None:
                name = text
                continue

            # 3. Кандидат на текст описания (не начинается с #)
            if not text.startswith('#'):
                candidates_for_description.append((text, el_id))

    # Выбираем самый длинный текст-кандидат как описание
    if candidates_for_description:
        # Сортируем по длине, берём самый длинный
        candidates_for_description.sort(key=lambda x: len(x[0]), reverse=True)
        description_text, text_id = candidates_for_description[0]

    return rectangle_id, nnn, name, description_text, text_id


def extract_descriptions(groups_outside_frame: List[List[Dict]]) -> List[DescriptionContent]:
    """
    Извлекает описания из групп ВНЕ Frame таблицы.
    Группы могут быть в любом Frame (или без Frame).
    """
    descriptions = []
    for group in groups_outside_frame:
        if not group:
            continue
        rect_id, nnn, name, text, text_id = classify_group_elements(group)
        bounds = get_entity_bounds(group)
        center = get_group_center(group)
        gid = group[0].get('groupIds', ['?'])
        descriptions.append(DescriptionContent(
            group_id=gid[0] if gid else '?',
            nnn=nnn,
            name=name,
            text=text or '',
            rectangle_id=rect_id,
            text_id=text_id,
            bounds=bounds,
            center=center,
        ))
    return descriptions