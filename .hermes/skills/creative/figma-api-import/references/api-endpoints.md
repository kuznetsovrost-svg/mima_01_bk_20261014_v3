---
name: figma-api-import
description: Figma REST API endpoints used by figma-api-import skill
version: 0.1.0
---

# Figma API Endpoints

## Authentication

Все запросы используют header:
```
X-Figma-Token: <FIGMA_PERSONAL_ACCESS_TOKEN>
```

## Endpoints

### GET /v1/me
Информация о текущем пользователе.

**Response:**
```json
{
  "id": "1664270591757365982",
  "email": "user@example.com",
  "handle": "Username",
  "img_url": "https://..."
}
```

### GET /v1/files/:file_key
Получить весь файл.

**Use case:** Получить document со всеми нодами.

### GET /v1/files/:file_key/nodes
Получить конкретные ноды.

**Params:**
- `ids` (required): comma-separated node IDs
- `depth` (optional): how deep to traverse
- `geometry` (optional): "paths"

### GET /v1/files/:file_key/styles
Список стилей файла.

### GET /v1/files/:file_key/components
Список компонентов файла.

**Use case:** Получить все `component_key` для дальнейших запросов.

### GET /v1/components/:component_key
Получить конкретный компонент.

### GET /v1/files/:file_key/variables/local
Локальные переменные (Variables API).

### GET /v1/images/:file_key
Получить URL для рендера нодов в PNG/SVG/JPG/PDF.

**Params:**
- `ids` (required): comma-separated node IDs
- `format`: `png` | `jpg` | `svg` | `pdf`
- `scale`: 1-4 (default 1)
- `version`: file version

**Response:**
```json
{
  "err": null,
  "images": {
    "1:23": "https://figma-alpha-api.s3.us-west-2.amazonaws.com/..."
  }
}
```

## Rate limits

- 60 requests/minute (User)
- Higher limits for paid plans

## Node IDs

В URL формате: `1:23`
В API формате: `1-23` (с дефисом вместо двоеточия)

Скилл автоматически конвертирует.

## Type hierarchy

- `DOCUMENT` — корневая
- `CANVAS` — страница
- `FRAME` — фрейм
- `GROUP` — группа
- `COMPONENT` — одиночный компонент
- `COMPONENT_SET` — главный с вариантами
- `INSTANCE` — инстанс компонента
- `RECTANGLE`, `ELLIPSE`, `POLYGON`, `STAR`, `TEXT`, `LINE`, `VECTOR`
- `BOOLEAN_OPERATION`
- `SLICE`
