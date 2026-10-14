---
name: figma-api-import
description: Импорт фреймов/компонентов из Figma через Personal Access Token для построения HTML/CSS шаблонов. Получает дизайн, шрифты, заливки, геометрию, components с variants. Находит главные компоненты всех вариантов (включая collapsed/expanded для аккордеонов) и импортирует их тоже.
version: 0.2.0
metadata:
  hermes:
    tags: [figma, api, import, html, css, design, components, variants]
    category: creative
    related_skills: [figma-to-html-workflow, officecli, excalidraw]
    changelog: 'v0.1.0 (2026-08-08): initial creation. v0.2.0 (2026-08-08): added URL parsing recipe, real walkthrough section with concrete commands from the Project Report 01 demo, variant JSON shape with actual filled example from Project.indicator (3 variants critical/substantial/normal), 4 new pitfalls (get_components returns 0, token not in git, foreign file partial result, Property 1/2/... naming), added references/real-walkthrough.md.'
when_to_use: |
  - Когда нужно получить дизайн-данные из Figma для генерации HTML
  - Когда есть Figma frame с компонентами-вариантами (collapsed/expanded, on/off)
  - Когда нужно импортировать главные компоненты, на которые ссылаются инстансы
  - Когда нужно получить токены (colors, typography, spacing) из variables/styles
triggers:
  - "импортируй фрейм из figma"
  - "загрузи из figma"
  - "получи дизайн из figma"
  - "figma api"
  - "figma import"
scripts:
  - script: figma_client.py
    description: Python клиент для Figma REST API (auto-loads token from .env)
  - script: import_frame.py
    description: "Главный скрипт: импортирует фрейм + рекурсивно все его компоненты"
  - script: extract_components.py
    description: Извлекает главные компоненты с variants для построения "открывашек"
  - script: create_from_template.py
    description: Создаёт ноды в существующем Figma файле по JSON-шаблону (POST /v1/files/{file_key}/nodes)
---

# Figma API Import

Импорт фреймов из Figma через REST API для использования в HTML-шаблонах.

## Что делает

1. **Загружает фрейм** из Figma по `file_key` + `node_id`
2. **Находит все инстансы компонентов** в этом фрейме
3. **Рекурсивно подтягивает главные компоненты** с **ВСЕМИ вариантами** (Variant Property)
4. **Сохраняет JSON** с дизайн-токенами и геометрией
5. **Генерирует HTML+CSS** как опция

## Ключевая особенность

Для таблицы-«открывашки» с `state=collapsed|expanded` — оба варианта нужны. Скилл **автоматически** проходит по `componentPropertyDefinitions` и достаёт **все** комбинации variants.

## Как запустить

```bash
# Базовый вызов
python3 scripts/import_frame.py \
  --file-key=ABC123XYZ \
  --node-id=1:23

# С указанием пути сохранения
python3 scripts/import_frame.py \
  --file-key=ABC123XYZ \
  --node-id=1:23 \
  --output=./my-import/

# С дополнительными опциями
python3 scripts/import_frame.py \
  --file-key=ABC123XYZ \
  --node-id=1:23 \
  --include-variants=all \
  --format=json
```

## URL → параметры (как распарсить)

Figma URL формат:
```
https://www.figma.com/design/{FILE_KEY}/{name}?node-id={NODE_ID}&...
```

Пример:
```
https://www.figma.com/design/8yntLyh0QlN7HEvtaDsw8i/Project-Report-01?node-id=0-1&t=...
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                  ^^^^^^
                file_key = 8yntLyh0QlN7HEvtaDsw8i                                  node_id = 0-1 (или 0:1)
```

- `node-id` в URL использует **дефис** (`0-1`)
- `node_id` в API — **двоеточие** (`0:1`)
- Скрипт `figma_client.py` уже конвертирует автоматически
- `file_key` одинаков в обоих форматах

## Реальный прогон (что происходит)

Из успешного теста с файлом `Project Report 01` (file_key `8yntLyh0QlN7HEvtaDsw8i`):

| API call | Что возвращает | Когда нужен |
|---|---|---|
| `get_me` | информация о пользователе | проверка токена |
| `get_file(file_key)` | полное дерево документа, `name`, `lastModified`, `version` | разведка |
| `get_nodes(file_key, [id])` | конкретные ноды по ID | получение фрейма |
| `get_components(file_key)` | все компоненты (на 2026-08 возвращает 0 для многих файлов — известная проблема) | поиск компонентов |
| `get_styles(file_key)` | список Figma Styles (Color/Text/Effect) | извлечение токенов |
| `get_variables(file_key)` | Variables API (требует scope `file_variables:read`) | новые токены |

⚠️ **Pitfall: `get_components` часто возвращает 0**, даже когда компоненты есть. Не полагайся на этот endpoint — обходи `file.document` и ищи `COMPONENT_SET` ноды рекурсивно. См. `references/real-walkthrough.md`.

## Шаблон вызова (end-to-end)

```python
import sys
sys.path.insert(0, '/root/.hermes/skills/creative/figma-api-import/scripts')
from figma_client import FigmaClient

client = FigmaClient()  # авто-токен из ~/.hermes/.env
file_key = "8yntLyh0QlN7HEvtaDsw8i"
frame_id = "19:4"

# 1. Получаем фрейм
nodes = client.get_nodes(file_key, [frame_id])
frame = nodes['nodes'][frame_id]['document']

# 2. Рекурсивно достаём COMPONENT_SET из document
def find_components(node, found):
    if node.get('type') == 'COMPONENT_SET':
        found.append(node)
    if 'children' in node:
        for child in node['children']:
            find_components(child, found)

file_data = client.get_file(file_key)
component_sets = []
find_components(file_data['document'], component_sets)

# 3. Извлекаем variants из каждого COMPONENT_SET
for cs in component_sets:
    for variant in cs.get('children', []):
        print(f"  {cs['name']} → {variant['name']}")
        # variant['fills'] содержит цвет
        # variant['size'] содержит размеры
        # variant['componentProperties'] содержит Property 1=collapsed и т.д.
```

## Что внутри variant JSON

Из реального файла `Project.indicator` (3 variants: critical/substantial/normal):

```json
{
  "id": "41:223",
  "name": "Project.indicator",
  "componentPropertyDefinitions": {
    "Property 2": {
      "type": "VARIANT",
      "defaultValue": "critical",
      "variantOptions": ["critical", "normal", "substantial"]
    }
  },
  "variants": [
    {
      "id": "41:220",
      "name": "Property 2=critical",
      "fills": [
        {"type": "SOLID", "color": {"r": 0.145, "g": 0.388, "b": 0.921, "a": 1.0}}
      ],
      "strokeWeight": 1.0,
      "characters": null,
      "size": null
    }
  ]
}
```

**Ключевые поля:**
- `componentPropertyDefinitions.<Property N>.variantOptions` — список значений варианта
- `variants[i].name` — формат `"Property N=<value>"` (например `state=collapsed`)
- `variants[i].fills` — массив слоёв заливки, color в `r/g/b/a` (0.0-1.0)
- `variants[i].size` — `{"x": W, "y": H}` если есть
- `variants[i].characters` — текстовое содержимое для TEXT-вариантов

**Конвертация цвета:** `rgb(0.145 * 255, 0.388 * 255, 0.921 * 255) = rgb(37, 99, 235)` = `#2563EB`

## Известные ограничения (на 2026-08)

| Endpoint | Проблема | Обход |
|---|---|---|
| `get_components` | возвращает 0 даже когда есть `COMPONENT_SET` | обходить `file.document` рекурсивно |
| `get_styles` | требует scope `file_content:read` (не везде есть в Personal Access Token) | проверить scopes при создании токена |
| `get_variables` | требует scope `file_variables:read` | создать токен с этим scope |
| `get_nodes` для конкретного id | может вернуть node без size (например `tbl/expanded`) | это нормально — design-time состояние без рамок |
| node_id из URL (`0-1`) vs API (`0:1`) | разные форматы разделителей | скрипт конвертирует автоматически |

## Что нужно от пользователя

| Параметр | Где взять |
|---|---|
| `file_key` | URL Figma: `figma.com/file/<FILE_KEY>/...` |
| `node_id` | URL Figma: `figma.com/file/...?node-id=<NODE_ID>` (формат `1:23`) |

**Пример:**
- URL: `https://www.figma.com/file/ABC123XYZ/My-Design?node-id=1:23`
- file_key: `ABC123XYZ`
- node_id: `1:23`

## Где хранится токен

Токен автоматически загружается из `~/.hermes/.env`:
```
FIGMA_PERSONAL_ACCESS_TOKEN=figd_xxxxx
```

Если не установлен — выведет инструкцию.

## Что получается на выходе

```
my-import/
├── frame.json                 ← главный файл с фреймом
├── components/
│   ├── cmp_button.json        ← главный компонент кнопки
│   ├── cmp_status_badge.json  ← badge с variants
│   │   ├── variants/
│   │   │   ├── state=critical.json
│   │   │   ├── state=attention.json
│   │   │   └── state=healthy.json
│   └── ...
├── styles.json                ← Figma Styles (Color, Text, Effect)
├── variables.json             ← Variables (если есть)
└── summary.md                 ← сводка для разработчика
```

## Pitfalls

### Token не должен попадать в git

FIGMA_PERSONAL_ACCESS_TOKEN — это секрет. Не коммитить в git, не отправлять в Telegram файл с токеном. `.env` файл должен быть в `.gitignore`.

### Запрос чужого файла вернёт частичный результат

Если ты не владелец файла, `get_file` может вернуть имя и метаданные, но `get_nodes`/`get_styles`/`get_variables` вернут ошибки. Перед прогоном попроси пользователя подтвердить что он владелец файла, или сделай `File → Make a copy` в Figma UI.

### Variants могут называться "Property 1", "Property 2", ...

Figma API не сохраняет человеко-читаемые имена variant properties в `componentPropertyDefinitions`. Ты увидишь `"Property 1"`, `"Property 2"`. Связать имя с значением можно только через `componentProperties` инстанса. Для бейджей в твоих файлах это нормально (один property — `state` или `Property 2`).

### get_components возвращает 0 — не верь ему

Самый частый pitfall. `meta.components` пустой даже когда в файле есть 8+ COMPONENT_SET. Не доверяй — обходи `file.document` напрямую и ищи `node.type == "COMPONENT_SET"` рекурсивно. `extract_components.py` уже делает это правильно.

### node_id формата `0:1` — это page_id

Если ты запросишь `node_id=0:1` (как page), API вернёт всю страницу со всеми нодами. Используй конкретный `frame_id` (`19:4` в нашем примере), чтобы получить только нужный фрейм.

## Связь с другими скиллами

| Скилл | Что дополняет |
|---|---|
| `figma-to-html-workflow` | следующий шаг: превращение JSON в HTML |
| `officecli` | для генерации .docx/.pdf из отчёта |
| `excalidraw` | для альтернативного редактирования |
