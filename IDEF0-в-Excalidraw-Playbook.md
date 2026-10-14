# Playbook: использование скилла `idef0-excalidraw`

> Скилл для анализа и валидации IDEF0 диаграмм, нарисованных в Excalidraw.
> Автоматически извлекает блоки, стрелки, туннели, проверяет ICOM consistency,
> генерирует каталог объектов (Arrow Catalogue) и описания блоков (Node Description).

---

## 1. Название скилла и как его вызвать

### 1.1 Имя

```
idef0-excalidraw
```

### 1.2 Расположение

Глобальный скилл в директории:

```
/root/.hermes/skills/creative/idef0-excalidraw/
```

Виден всем профилям Hermes (`default`, `analyst_training`, `fst-control` и др.) через `SKILLS_DIR`.

### 1.3 Способы вызова

#### Способ A: через Hermes агента (рекомендуется)

Скилл подгружается автоматически по триггерам — достаточно попросить словами:

```
@Hermes проверь IDEF0 диаграмму в /path/to/diagram.excalidraw
@Hermes сгенерируй каталог стрелок для A2 из diagram.excalidraw
@Hermes проверь ICOM consistency для блока A0.1
@Hermes сгенерируй описания блоков
```

Ключевые слова-триггеры: **IDEF0**, **Excalidraw**, **каталог стрелок**, **ICOM consistency**, **туннель в IDEF0**, **описание блока**.

#### Способ B: прямой вызов CLI

Все скрипты доступны в `scripts/`:

```bash
SKILL=/root/.hermes/skills/creative/idef0-excalidraw
FILE=/path/to/diagram.excalidraw
```

| Команда | Что делает |
|---|---|
| `python3 $SKILL/scripts/validator.py summary --file $FILE` | Краткая сводка (блоки, стрелки, туннели) |
| `python3 $SKILL/scripts/validator.py validate --file $FILE` | Полная валидация |
| `python3 $SKILL/scripts/validator.py generate-catalogue --file $FILE` | Каталог объектов (Arrow Catalogue) |
| `python3 $SKILL/scripts/validator.py generate-catalogue --file $FILE --frame "A2"` | Каталог для конкретного Frame |
| `python3 $SKILL/scripts/validator.py generate-description --file $FILE` | Описания всех блоков |
| `python3 $SKILL/scripts/validator.py check-icom --file $FILE --parent <block-id>` | Проверка ICOM consistency |
| `python3 $SKILL/scripts/validator.py validate --file $FILE --parent <block-id>` | Валидация + ICOM |

#### Способ C: как Python модуль

```python
import sys
sys.path.insert(0, '/root/.hermes/skills/creative/idef0-excalidraw/scripts')

from excalidraw_parser import ExcalidrawParser
from block_extractor import BlockExtractor
from arrow_extractor import ArrowExtractor
from side_detector import SideDetector
from tunnel_detector import TunnelDetector
from icom_checker import ICOMChecker
from catalogue_generator import CatalogueGenerator
from description_generator import DescriptionGenerator

parser = ExcalidrawParser('diagram.excalidraw')
parser.load()

blocks = BlockExtractor(parser.elements).extract_all_blocks()
arrows = ArrowExtractor(parser.elements).extract_all_arrows()
tunnels = TunnelDetector(arrows).find_all_tunnels()

# Сводка
print(parser.summary())
print(f"Tunnels: {len(tunnels)}")
```

#### Способ D: для LLM-агента через Hermes skill API

В профиле, где есть доступ к `skill_view` / `skill_manage`:

```
skill_view(name="idef0-excalidraw")
```

Подгружает полную инструкцию в контекст.

---

## 2. Что скилл делает (возможности)

| Функция | Описание |
|---|---|
| Парсинг `.excalidraw` JSON | Читает структуру файла |
| Извлечение блоков IDEF0 | Находит группы из 3 элементов: rectangle + func + num |
| Извлечение стрелок | Парсит все arrow-элементы с метаданными |
| Определение граней | Left/Right/Top/Bottom — к какой грани блока привязана стрелка |
| ICOM consistency | Сравнивает стрелки parent ↔ child Frame |
| Обнаружение туннелей | По скобкам `( )` в тексте стрелки |
| Генерация каталога | Таблица всех стрелок (имя, источник, получатель, тип) |
| Генерация описаний | По стандартному шаблону "На основании C, получает I, выдаёт O, опираясь на M" |
| Валидация | Проверка структуры (наличие блоков, стрелок, имён, номеров) |

---

## 3. Как оформлять диаграмму IDEF0 в Excalidraw

Это критически важный раздел. Скилл работает только если диаграмма оформлена по **строгим соглашениям**. Неправильное оформление = скилл не найдёт блоки.

### 3.1 Блок (3 элемента в группе)

**Каждый блок IDEF0 = группа из ровно 3 элементов:**

| Элемент | Тип | Где в прямоугольнике | Содержание |
|---|---|---|---|
| Прямоугольник | `rectangle` | Весь блок | (пустой) |
| Имя функции | `text` | **Центр** | "Разработка чертежей", "Тестирование" |
| Номер блока | `text` | **Левый нижний угол** | "A0.1", "A1.2", "A-0" |

**Все три элемента должны иметь одинаковый `groupIds`** — например `["group-A0-1"]`.

#### Создание в Excalidraw (UI)

1. Нарисуйте прямоугольник
2. Добавьте текст с именем функции в центре
3. Добавьте текст с номером в левом нижнем углу
4. Выделите все 3 элемента → **Ctrl/Cmd + Shift + G** (группировка)
5. (Опционально) Имя группы: `group-A0-1`

#### Размеры и пропорции (рекомендация)

```
Ширина блока: 200 px
Высота блока: 100 px
```

Номер блока: 30×20 px в углу
Имя функции: 180×20 px в центре

### 3.2 Стрелки ICOM

**Каждая стрелка должна быть привязана к блоку** — кликните по стрелке, потяните за конец к его грани.

| Грань блока | ICOM роль | Пример стрелки |
|---|---|---|
| **Левая** (left) | **I** (Input) | Идёт В блок слева |
| **Правая** (right) | **O** (Output) | Идёт ИЗ блока вправо |
| **Верхняя** (top) | **C** (Control) | Идёт В блок сверху |
| **Нижняя** (bottom) | **M** (Mechanism) | Идёт В блок снизу |

#### Текст стрелки (формат)

Текст стрелки должен начинаться с **кода ICOM**:

```
I1 требования от заказчика
I2 документация
O1 готовый чертёж
O2 спецификация
C1 ГОСТ 2.307
C2 стандарт предприятия
M1 инженер-конструктор
M2 CAD-система
```

Код — это **первое слово** в тексте. Остальной текст — описание.

### 3.3 Туннелирование

**Туннель обозначается скобками `( )` в начале или конце текста стрелки.**

| Тип туннеля | Текст стрелки | Где скобка | Значение |
|---|---|---|---|
| На конце | `( I1 входной документ` | В начале | Стрелка "проваливается" через блок и выходит с другой стороны |
| На начале | `C1 управление )` | В конце | Стрелка приходит снаружи и уходит дальше |
| Двойной | `( O1 результат )` | С обеих сторон | Проходит через всю диаграмму транзитом |

**Правило:** одна открывающая `(` или одна закрывающая `)` — НЕ две подряд `((`.

### 3.4 Frame для уровней декомпозиции

Каждый уровень IDEF0 = один Frame с именем по соглашению.

#### Контекстная диаграмма (верхний уровень)

```
Frame name: "A-0 Контекст"
или просто: "A-0"
```

Внутри — **один блок** A-0 (или без номера — просто "Деятельность").

#### Декомпозиция

Frame имя содержит ссылку на parent-блок:

```
Frame name: "A0 (parent: A-0)"
```

Это означает: декомпозиция блока A-0 на уровень A0.

#### Декомпозиция блока

```
Frame name: "A1 (parent: A0-2)"
```

Это: декомпозиция блока номер 2 из уровня A0 → уровень A1.

**Соглашение:** `(parent: <parent_block_number>)` — точное совпадение с номером блока в parent.

### 3.5 Arrow Catalogue (опционально)

Если хотите, чтобы скилл сгенерировал каталог для конкретной диаграммы — создайте Frame с именем:

```
"Arrow Catalogue A2"
```

Внутри Frame — таблица (произвольная разметка). Скилл её не читает — генерирует свою.

### 3.6 Что НЕ делать

| Ошибка | Почему плохо | Как правильно |
|---|---|---|
| Блок = 1 rectangle без текстов | Скилл не распознает | Добавьте текст с именем |
| Блок = rectangle + текст без номера | Скилл ругается warning'ом | Добавьте текст с номером |
| Стрелка НЕ привязана к блоку | Не определится грань (unknown) | Кликните по стрелке, потяните к грани |
| Стрелка в центре блока, не у грани | Не определится ICOM роль | Тяните конец ровно к грани |
| Текст стрелки начинается с имени, а не с кода | arrow_name будет пустой | Первое слово = "I1", "O1", "C1", "M1" |
| Frame без соглашения `parent: <number>` | ICOM check не найдёт child | Используйте строгий формат имени |

---

## 4. Примеры

### 4.1 Минимальный пример (1 блок, 4 стрелки)

Файл: `minimal.excalidraw`

```
┌─────────────────────────┐
│ Frame: "A-0 Контекст"   │
│                         │
│  I1 →┌─────────┐        │
│      │Разработка│──O1──→ │
│      │  A-0    │        │
│  C1 ↘└─────────┘↙ M1    │
│                         │
└─────────────────────────┘
```

Группа: `group-context`
- Rectangle: id=`rect-context`, x=300, y=200, 200×100
- Function: id=`func-context`, text="Разработка", в центре
- Number: id=`num-context`, text="A-0", в левом нижнем углу
- Стрелка I1: text="I1 требования", end_binding→rect-context (left)
- Стрелка O1: text="O1 чертёж", start_binding→rect-context (right)
- Стрелка C1: text="C1 стандарты", end_binding→rect-context (top)
- Стрелка M1: text="M1 инженер", start_binding→rect-context (bottom)

#### Команда проверки

```bash
python3 /root/.hermes/skills/creative/idef0-excalidraw/scripts/validator.py \
    summary --file minimal.excalidraw
```

Ожидаемый вывод:

```json
{
  "file": "minimal.excalidraw",
  "total_elements": 7,
  "frames": 1,
  "rectangles": 1,
  "texts": 2,
  "arrows": 4,
  "frame_names": ["A-0 Контекст"]
}

Tunnels: 0
```

### 4.2 Декомпозиция (parent → child)

```
Frame "A0 (parent: A-0)"     Frame "A1 (parent: A0-2)"
┌──────────────────┐         ┌──────────────────┐
│ A0.1 Разработка  │         │ A1.1 Анализ      │
│ A0.2 Тестирование│         │ A1.2 Проектирование│
└──────────────────┘         └──────────────────┘
       ↓                            ↑
  ICOM check: parent block A0.2 должен иметь те же стрелки,
  что и Frame "A1 (parent: A0-2)"
```

#### Команда ICOM проверки

```bash
python3 /root/.hermes/skills/creative/idef0-excalidraw/scripts/validator.py \
    check-icom --file diagram.excalidraw --parent rect-A0-2
```

### 4.3 Туннелированные стрелки

```
Frame "A1 (parent: A0-2)"
┌──────────────────────────────────────┐
│ ┌──────────┐                          │
│ │ A1.2     │                          │
│ │Проектиров.│                          │
│ └──────────┘                          │
│   ↑      ↓                            │
│ ( I1     ( O1 результат )  ← двойной │
│  вход)               туннель           │
└──────────────────────────────────────┘
```

- Стрелка `I1 вход` с `( ` в начале → туннель на конце
- Стрелка `O1 результат` с `( ... )` → двойной туннель

#### Команда обнаружения туннелей

```bash
python3 /root/.hermes/skills/creative/idef0-excalidraw/scripts/validator.py \
    summary --file diagram.excalidraw
```

В выводе:

```
Tunnels: 2
  - I1 (end)
  - O1 (both)
```

### 4.4 Полный цикл (комплексная диаграмма)

Сценарий: у вас есть `production.excalidraw` с 5 уровнями декомпозиции, 30 блоков, 80 стрелок (из них 12 туннелированных).

```bash
SKILL=/root/.hermes/skills/creative/idef0-excalidraw
FILE=production.excalidraw

# 1. Краткая сводка
python3 $SKILL/scripts/validator.py summary --file $FILE

# 2. Полная валидация
python3 $SKILL/scripts/validator.py validate --file $FILE > validation.txt

# 3. Каталог для всей диаграммы
python3 $SKILL/scripts/validator.py generate-catalogue --file $FILE > catalogue.md

# 4. Каталог для конкретного уровня
python3 $SKILL/scripts/validator.py generate-catalogue --file $FILE --frame "A2" > catalogue-A2.md

# 5. Описания всех блоков
python3 $SKILL/scripts/validator.py generate-description --file $FILE > descriptions.md

# 6. ICOM check для каждого декомпозированного блока
for block in block1 block2 block3; do
    python3 $SKILL/scripts/validator.py check-icom \
        --file $FILE --parent $block >> icom-errors.txt
done
```

---

## 5. Структура скилла

```
/root/.hermes/skills/creative/idef0-excalidraw/
├── SKILL.md                    ← главное описание
├── README.md                   ← краткое описание
├── scripts/
│   ├── excalidraw_parser.py    ← парсинг JSON
│   ├── block_extractor.py      ← извлечение блоков
│   ├── arrow_extractor.py      ← извлечение стрелок
│   ├── side_detector.py        ← определение граней
│   ├── tunnel_detector.py      ← обнаружение туннелей
│   ├── icom_checker.py         ← проверка parent/child
│   ├── catalogue_generator.py  ← генерация Arrow Catalogue
│   ├── description_generator.py ← генерация Node Description
│   └── validator.py            ← CLI (точка входа)
├── references/
│   ├── idef0-rules.md          ← правила IDEF0 (FIPS 183)
│   ├── excalidraw-conventions.md ← соглашения разметки
│   └── examples.md             ← примеры
├── templates/
│   └── idef0-template.excalidraw ← шаблон пустой IDEF0
└── tests/                      ← 145 unit-тестов
    ├── conftest.py
    ├── test_*.py
    └── run_tests.py
```

---

## 6. Устранение неполадок

### 6.1 "No IDEF0 blocks found"

**Причина:** в файле нет ни одной группы из 3 элементов (rectangle + func + num).

**Решение:**
1. Откройте файл в Excalidraw
2. Проверьте: каждый блок = прямоугольник + текст имени + текст номера
3. Выделите все 3 → сгруппируйте (Ctrl/Cmd+Shift+G)

### 6.2 Стрелки не имеют ICOM роли (все unknown)

**Причина:** стрелки не привязаны к граням блоков, или привязаны в центре.

**Решение:**
1. Кликните по стрелке
2. Потяните за её конец **к грани** блока (не в центр)
3. Привязка появится автоматически (синяя точка)

### 6.3 ICOM consistency errors: missing_in_child

**Причина:** в child Frame нет стрелок, которые есть у parent блока.

**Решение:** добавьте в child Frame стрелки с теми же именами (I1, O1, C1, M1) и привяжите к соответствующим граням.

### 6.4 ICOM consistency errors: extra_in_child

**Причина:** в child Frame есть стрелки, которых нет у parent блока. Это обычно легитимные **туннели** — стрелки, проходящие сквозь.

**Решение:** если стрелка — туннель, добавьте скобки в текст. Иначе удалите лишнюю стрелку.

### 6.5 Туннель не обнаружен

**Причина:** скобки не в начале или конце текста.

**Проверьте:**

```
✅  ( I1 вход         — скобка в начале
✅  O1 результат )    — скобка в конце
✅  ( C1 управление ) — скобки с обеих сторон

❌  I1 ( вход         — скобка в середине
❌  (( I1 вход        — двойная скобка
```

### 6.6 Запуск тестов

```bash
cd /root/.hermes/skills/creative/idef0-excalidraw
python3 tests/run_tests.py
```

Ожидаемый результат: **145 passed / 0 failed**.

---

## 7. Краткая шпаргалка

| Что хочу | Что делаю |
|---|---|
| Проверить диаграмму | `@Hermes validate diagram.excalidraw` |
| Увидеть сводку | `python3 scripts/validator.py summary --file X.excalidraw` |
| Получить каталог | `python3 scripts/validator.py generate-catalogue --file X.excalidraw` |
| Получить описания блоков | `python3 scripts/validator.py generate-description --file X.excalidraw` |
| Проверить ICOM parent↔child | `python3 scripts/validator.py check-icom --file X.excalidraw --parent <id>` |
| Запустить все тесты | `cd /root/.hermes/skills/creative/idef0-excalidraw && python3 tests/run_tests.py` |

---

## 8. Связанные ресурсы

- **`/root/IDEF0-в-Excalidraw-01.md`** — глубокий playbook с теорией IDEF0 (msg_id=2449)
- **`/root/.hermes/skills/creative/excalidraw/`** — базовый скилл для работы с .excalidraw файлами
- **`/root/.hermes/skills/creative/excalidraw-json-gotchas/`** — подводные камни парсинга JSON

---

*Playbook версия 1.0 — 2026-08-17*
*Автор: Hermes Agent (для Rost)*