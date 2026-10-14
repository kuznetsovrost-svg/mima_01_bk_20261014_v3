---
name: idef0-excalidraw
description: |
  Анализ и валидация IDEF0 диаграмм, нарисованных в Excalidraw.
  Поддерживает: парсинг .excalidraw, извлечение блоков и стрелок,
  определение граней стрелок, ICOM consistency check между parent
  и child диаграммами, обнаружение туннелей, генерация каталога
  объектов (Arrow Catalogue), генерация описаний блоков
  (Node Description). Полное руководство в /root/IDEF0-в-Excalidraw-01.md.
version: 0.1.0
author: Hermes Agent (для Rost)
metadata:
  hermes:
    tags: [idef0, excalidraw, modeling, validation, bpmn-adjacent, diagram-analysis]
    category: creative
    related_skills: [excalidraw, figma-api-import]
---

# idef0-excalidraw

Анализ и валидация IDEF0 диаграмм в Excalidraw.

## Что делает

- Парсит `.excalidraw` файл (JSON)
- Извлекает блоки (группы из 3 элементов: rectangle + func + num)
- Извлекает стрелки и определяет их грань присоединения
- Обнаруживает уровни (Frame с именами A-0, A0, A1...)
- Строит дерево декомпозиции (parent ↔ child)
- Проверяет ICOM consistency (число/имена стрелок на границах)
- Обнаруживает туннели (скобки ( ) в тексте стрелок)
- Генерирует каталог объектов (Arrow Catalogue)
- Генерирует описания блоков (Node Description)

## Использование

### Валидация

```bash
python3 scripts/validator.py validate \
  --file path/to/diagram.excalidraw
```

### Генерация каталога

```bash
python3 scripts/validator.py generate-catalogue \
  --file path/to/diagram.excalidraw \
  --frame "A2"
```

### Проверка ICOM consistency

```bash
python3 scripts/validator.py check-icom \
  --file path/to/diagram.excalidraw \
  --parent "A0" \
  --child "A2"
```

### Генерация описаний

```bash
python3 scripts/validator.py generate-description \
  --file path/to/diagram.excalidraw \
  --frame "A2"
```

## Архитектура

```
scripts/
  excalidraw_parser.py     # парсер .excalidraw JSON
  block_extractor.py       # извлечение блоков по groupIds
  arrow_extractor.py       # извлечение стрелок
  side_detector.py         # определение грани (left/right/top/bottom)
  icom_checker.py          # ICOM consistency parent ↔ child
  tunnel_detector.py       # обнаружение туннелей по скобкам
  catalogue_parser.py      # парсер таблицы каталога
  catalogue_generator.py   # генерация каталога из стрелок
  description_generator.py # генерация описаний блоков
  validator.py             # главный CLI модуль
references/
  idef0-rules.md           # правила IDEF0 (FIPS 183)
  excalidraw-conventions.md # соглашения разметки в Excalidraw
  examples.md              # примеры IDEF0 в Excalidraw
templates/
  idef0-template.excalidraw # пустой шаблон IDEF0 диаграммы
```

## Соглашения по разметке в Excalidraw

### Блок (функция)

```
block-<N>    rectangle
func-<N>     text (имя функции, по центру)
num-<N>      text (номер A1.2, в нижнем левом углу)
group-<N>    имя группы (общий groupIds у всех 3 элементов)
```

### Уровень (Frame)

Имя Frame: `"A<n> <Описание> (parent: A<m>-<код>)"`

Примеры:
- `"A-0 Контекст"`
- `"A0 (parent: A-0)"`
- `"A1 Обработка заявки (parent: A0-2)"`

### Стрелка ICOM

Текст стрелки:
- Без туннеля: `"I1 Имя объекта"`
- С туннелем: `"( I1 Имя объекта"` или `"I1 Имя объекта )"`

### Каталог объектов

Frame внутри диаграммы: `"Arrow Catalogue A2"`

Содержит таблицу с полями: Имя | Источник | Получатель | Тип

## Возвращаемые значения

### validate

Список ошибок и предупреждений:
```python
[
    {
        "type": "block_without_number",
        "block_id": "block-A1-3",
        "severity": "error",
        "message": "Block A1-3 missing number text"
    },
    ...
]
```

### generate-catalogue

Текст таблицы:
```
| Имя           | Источник    | Получатель | Тип |
| Заявка клиента | Граница    | Блок 1     | I   |
| Правила       | Граница     | Блок 1, 2 | C   |
```

### check-icom

Список несоответствий:
```python
[
    {
        "role": "input",
        "missing_in_child": ["I3"],
        "extra_in_child": ["I4"]
    }
]
```

### generate-description

Текст описания:
```
Блок 1. Обработка заявки. На основании "Правила работы",
получает "Заявка клиента", выдаёт "Заявка проверенная",
опираясь на "Менеджер".
```

## Ограничения

⚠️ Не определяет семантическую правильность (только структуру)
⚠️ Не обрабатывает стрелки привязанные к углам блоков
⚠️ Не обрабатывает повёрнутые блоки
⚠️ Frame внутри Frame требует дополнительной логики

## Полное руководство

См. `/root/IDEF0-в-Excalidraw-01.md` — подробный playbook
со всеми правилами, алгоритмами и примерами.

## Примеры использования

См. `references/examples.md`.

## История версий

- 0.1.0 (2026-08-09): начальная версия
