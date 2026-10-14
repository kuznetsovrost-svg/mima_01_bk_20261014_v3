# Real walkthrough: Project Report 01

Демо-прогон на реальном файле пользователя (2026-08-08). Сохранилось в `/root/figma-import-test/`.

## Исходные данные

```
URL: https://www.figma.com/design/8yntLyh0QlN7HEvtaDsw8i/Project-Report-01?node-id=0-1&t=WwrrINrzy3i8KC9f-0
file_key: 8yntLyh0QlN7HEvtaDsw8i
node_id (URL): 0-1 → API: 0:1 (это page)
frame_id (наш выбор): 19:4 ("iPhone 16 & 17 Pro Max - 2")
```

Файл владельца `kuznetsov.rost@gmail.com` — Personal Access Token работает.

## Прогон

### Шаг 1: тест токена

```bash
python3 /root/.hermes/skills/creative/figma-api-import/scripts/figma_client.py
```

Возвращает:
```json
{
  "status": "ok",
  "user": {
    "id": "1664270591757365982",
    "email": "kuznetsov.rost@gmail.com",
    "handle": "Kuznetsov Rostislav"
  }
}
```

### Шаг 2: получить список компонентов (НЕ РАБОТАЕТ на 2026-08)

```python
client.get_components("8yntLyh0QlN7HEvtaDsw8i")
# → {"meta": {"components": []}}   # ПУСТОЙ даже когда в файле 8+ COMPONENT_SET
```

**Это известная проблема Figma API.** Не полагайся на `get_components`. Обходи `file.document` рекурсивно.

### Шаг 3: получить фрейм через get_file + обход document

```python
file_data = client.get_file(file_key)
page_id = file_data['document']['children'][0]['id']  # "0:1" (Page 1)
```

Получили детей страницы — 29 элементов верхнего уровня, среди них:

| Имя | Тип | Размер |
|---|---|---|
| `iPhone 16 & 17 Pro Max - 1` | FRAME | — |
| `Frame 6` | FRAME | — |
| `tbl` | INSTANCE | — |
| `iPhone 16 & 17 Pro Max - 2` | FRAME | 440×956 (наш целевой) |
| `cmp.collapsible.tbl3` | FRAME (×5 шт) | — |
| `Variant.tbl1/expanded` | FRAME | — |
| `Variant.tbl1/collapsed` | FRAME | — |
| ... (×8 frames для каждой таблицы) | | |
| `Project.indicator` | COMPONENT_SET | — |
| `Variant.tbl1..5` | COMPONENT_SET | — |
| 3× TEXT-шаблона (markdown-таблицы) | TEXT | — |
| `Component 1` | COMPONENT | — |
| `Component 3` | FRAME | — |

### Шаг 4: получить frame 19:4

```python
nodes_data = client.get_nodes(file_key, ["19-4"])
frame = nodes_data['nodes']['19-4']['document']
```

Frame: `iPhone 16 & 17 Pro Max - 2`, size 440×956, position (727, -14), background `r:1.0 g:1.0 b:1.0 a:1.0` (белый).

### Шаг 5: обход COMPONENT_SET вручную

```python
def find_components_recursive(node, found):
    if node.get('type') == 'COMPONENT_SET':
        found.append(node)
    if 'children' in node:
        for child in node['children']:
            find_components_recursive(child, found)

component_sets = []
find_components_recursive(file_data['document'], component_sets)
```

**Результат: 8 COMPONENT_SET** (вместо 0 из get_components):

| Имя | Variants | Описание |
|---|---|---|
| `tbl` | 2 (`state=collapsed`, `state=expanded`) | базовая открывашка |
| `Variant.tbl1` | 2 (`Property 1=expanded`, `Property 1=collapsed`) | таблица замечаний |
| `Variant.tbl2` | 2 | финансовый статус |
| `Variant.tbl3` | 2 | ответственный |
| `Variant.tbl4` | 2 | финансовый контроль |
| `Variant.tbl5` | 2 | системные параметры |
| `Project.indicator` | 3 (`Property 2=critical/substantial/normal`) | статус-индикатор |
| `Variant.tbl1` (дубль) | 2 | (один и тот же id, Figma баг) |

**Итого: 17 variants** сконвертировано в JSON.

### Шаг 6: выходная структура

```
/root/figma-import-test/
├── frame.json                          (698 KB) — полное дерево фрейма
├── summary.json                        (1.0 KB)
└── components/
    ├── Project.indicator.json          (1.8 KB) — 3 variants
    ├── Variant.tbl1.json               (806 B) — 2 variants
    ├── Variant.tbl2.json               (806 B)
    ├── Variant.tbl3.json               (806 B)
    ├── Variant.tbl4.json               (806 B)
    ├── Variant.tbl5.json               (806 B)
    └── tbl.json                        (1.2 KB)
```

## Конкретный JSON варианта Project.indicator

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
  "variant_count": 3,
  "variants": [
    {
      "id": "41:220",
      "name": "Property 2=critical",
      "componentProperties": {},
      "size": null,
      "fills": [
        {
          "blendMode": "NORMAL",
          "type": "SOLID",
          "color": {
            "r": 0.14509804546833038,
            "g": 0.38823530077934265,
            "b": 0.9215686321258545,
            "a": 1.0
          }
        }
      ],
      "strokes": [],
      "strokeWeight": 1.0,
      "cornerRadius": null,
      "characters": null
    },
    {
      "id": "41:221",
      "name": "Property 2=substantial",
      ...same structure, different fill...
    },
    {
      "id": "41:222",
      "name": "Property 2=normal",
      ...same structure, different fill...
    }
  ]
}
```

## Конвертация цвета (для CSS)

```python
def figma_color_to_hex(color):
    """r/g/b в 0.0-1.0 → #RRGGBB"""
    r = int(color['r'] * 255)
    g = int(color['g'] * 255)
    b = int(color['b'] * 255)
    return f"#{r:02X}{g:02X}{b:02X}"

# Пример: color {'r': 0.145, 'g': 0.388, 'b': 0.921}
# → '#2563EB' (blue-600 в Tailwind)
```

## Lessons learned (для следующих прогонов)

1. **`get_components` возвращает 0** — обходи `file.document` сам. Не трать время на debug.
2. **`get_file` стоит ~5 секунд** на больших файлах — кэшируй результат, если будешь делать несколько запросов
3. **`get_nodes` быстрее** (~1 сек), но не даёт полного дерева
4. **`get_styles` и `get_variables` могут требовать scope** — проверить при создании токена
5. **Variant property names = "Property 1", "Property 2"** — это **нормально**, не баг
6. **Размер variant JSON обычно 800-1800 B** — компактно, удобно для diff
7. **Position в Figma = `absoluteBoundingBox`** — `{x, y, width, height}` в координатах страницы
8. **Background фрейма в `backgroundColor`** — `r/g/b/a` (0.0-1.0)

## Что делать с результатами

Для следующего шага (HTML-генерация) использовать:
- `frame.json` → структура фрейма + детей → HTML layout
- `components/*.json` → каждый variant → CSS class
- `fills[]` → background-color
- `characters` → текстовое содержимое
- `size` → width/height ячеек

Реальный сгенерированный HTML (для этого фрейма) — в `/root/figma-frame.html` (13.8 KB), отправлен в Telegram msg_id 2010.
