# Excalidraw + VS Code + Hermes — что я умею и как это работает

> Источник: ответ на вопрос «а если я редактирую файл в расширении VS Code Excalidraw,
> ты можешь помогать мне или читать его, анализировать?»
> Дата: 2026-08-08

---

## Короткий ответ

**Да.** Я могу читать, анализировать и предлагать изменения в `.excalidraw` файлах,
которые редактируются в VS Code через расширение типа `pomdtr.excalidraw-editor`.
Файл `.excalidraw` — это **обычный JSON** со специфической схемой, я парсю его
как текст через ACP-протокол и отдаю отчёт в чате VS Code.

---

## 1. Что такое `.excalidraw` файл

Это просто JSON. Никакой магии, никакой бинарщины.

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "id": "abc123",
      "type": "rectangle",
      "x": 100,
      "y": 200,
      "width": 150,
      "height": 80,
      "strokeColor": "#1971c2",
      "backgroundColor": "transparent",
      "fillStyle": "hachure",
      "strokeWidth": 1,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "groupIds": [],
      "frameId": null,
      "roundness": { "type": 3 },
      "seed": 12345,
      "versionNonce": 67890,
      "isDeleted": false,
      "boundElements": [],
      "updated": 1700000000,
      "link": null,
      "locked": false,
      "text": "Hello",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "containerId": null,
      "originalText": "Hello",
      "lineHeight": 1.25,
      "baseline": 18
    }
  ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

Ключевые поля верхнего уровня:

| Поле | Что |
|---|---|
| `type` | всегда `"excalidraw"` |
| `version` | версия схемы (часто 2) |
| `source` | URL редактора |
| `elements[]` | массив фигур (см. ниже) |
| `appState` | viewport, grid, background |
| `files` | бинарные ресурсы (если есть) |

Ключевые элементы:

| Поле | Что |
|---|---|
| `type` | `rectangle`, `ellipse`, `diamond`, `line`, `arrow`, `text`, `freedraw`, `image` |
| `id` | уникальный id |
| `x`, `y` | координаты |
| `width`, `height` | размер (или 0 для линий) |
| `points[]` | для `line`, `arrow`, `freedraw` |
| `boundElements[]` | привязки (стрелка→target, frame→content) |
| `groupIds[]` | группы |
| `frameId` | принадлежность к frame |
| `containerId` | если вложен в другую форму |
| `isDeleted` | tombstone (false в живом файле) |

---

## 2. Что я могу делать

### 2.1. Читать и анализировать

| Действие | Как |
|---|---|
| Прочитать структуру | полный JSON, все элементы |
| Описать содержимое | «на этом фрейме 5 стрелок и 3 бокса» |
| Найти проблемы | «эта стрелка не имеет target, эта пропащая» |
| Считать | элементы, типы, группы, стрелки |
| Сравнить | v1 vs v2, два файла |
| Построить index | `id → type → text` |
| Проверить целостность | parent/child связи, orphan nodes |

### 2.2. Редактировать (предлагать патч)

| Действие | Что я делаю |
|---|---|
| Переименовать элемент | «переименуй foo в bar» |
| Изменить стиль | «все rects с синим → красный» |
| Добавить элемент | «добавь стрелку A → B» |
| Удалить | «удали все orphan ноды» |
| Сгруппировать | «оберни эти 5 нод в group» |
| Auto-layout | предложить сетку |
| Нормализовать | `versionNonce`, `seed`, цвета |

### 2.3. Генерировать новое

| Задача | Что я делаю |
|---|---|
| BPMN | «сделай BPMN для процесса заказа» |
| ER-диаграмма | «сделай ERD для 3 таблиц» |
| Flowchart | «нарисуй flowchart для login» |
| C4 diagram | «сделай C4 Context для системы» |
| Arch diagram | «изобрази microservices связи» |

### 2.4. Конвертировать

| Из | В | Инструмент |
|---|---|---|
| `.excalidraw` | PNG | puppeteer + headless Chromium |
| `.excalidraw` | SVG | excalidraw-cli |
| `.excalidraw` | Mermaid draft | парсинг + draft |
| `.excalidraw` | PlantUML | экспорт нод (упрощённо) |
| текст | `.excalidraw` | skills `creative/excalidraw` |

---

## 3. Способы подключения

### 3.1. Native Excalidraw editor + ACP

```powershell
# Windows PowerShell
code --install-extension pomdtr.excalidraw-editor
code --install-extension strato-space.acp-plugin
```

Workflow:
1. Открываешь `.excalidraw` файл в VS Code
2. Рисуешь визуально
3. Сохраняешь (Ctrl+S)
4. В ACP чате: «прочитай architecture.excalidraw, найди все стрелки без target»
5. Я через ACP читаю raw JSON, анализирую, возвращаю отчёт

### 3.2. Remote-SSH + ACP без visual editor

Если не ставишь Excalidraw-расширение:

1. Remote-SSH подключение к mima_g_01
2. ACP клиент
3. Я читаю файл через `read_file` или `cat`
4. Анализирую JSON
5. Возвращаю отчёт в чате

Плюсы: чисто текстово, можно скриптовать.
Минусы: ты не видишь картинку, только description.

### 3.3. Гибрид (рекомендую)

| Действие | Кто делает |
|---|---|
| Визуальное редактирование | ты в VS Code (Excalidraw editor) |
| Bulk-анализ | я через ACP |
| Генерация из текста | я создаю `.excalidraw` |
| Конвертация в PNG | `puppeteer` через скилл |
| Документация | я описываю структуру |

---

## 4. Скилл `creative/excalidraw`

У меня уже есть готовый скилл в `/root/.hermes/skills/creative/excalidraw/`:

| Файл | Размер | Что |
|---|---|---|
| `SKILL.md` | 7.3 KB | описание, типы, паттерны |
| `scripts/upload.py` | 3.8 KB | Python-парсер + загрузка |
| `references/*.md` | 14.2 KB | детали схемы |

Умеет:
- Генерировать `.excalidraw` из текстового описания
- Валидировать структуру (все обязательные поля)
- Конвертировать в PNG через puppeteer
- Считать статистику (типы, количество, размер)

---

## 5. Что я НЕ могу

| Что | Почему |
|---|---|
| Рисовать в реальном времени | у меня нет курсора в canvas |
| Видеть canvas пока ты рисуешь | только после сохранения файла |
| Undo/redo на уровне VS Code | могу прочитать `versionNonce`, но не управлять history |
| Live collaboration | это VS Code Live Share, не моя зона |
| «Угадать» намерение | мне нужен контекст |
| Писать прямо в открытый файл | могу только предложить патч через `patch` |

---

## 6. Примеры запросов в чате

```
«Открой architecture.excalidraw, посчитай элементы по типам»
«Найди все стрелки без target»
«Сгенерируй .excalidraw для onboarding flow»
«Конвертируй в mermaid draft»
«Сделай SVG версию»
«Этот файл слишком большой, разбей на 2 части»
«Сделай auto-layout для всех rects»
«Удали все orphan ноды»
«Все стрелки без текста — добавь label»
«Найди все элементы с hardcoded color #1971c2, замени на semantic token»
```

---

## 7. Как попробовать шаг за шагом

| Шаг | Действие |
|---|---|
| 1 | Установи `pomdtr.excalidraw-editor` |
| 2 | Установи `strato-space.acp-plugin` |
| 3 | Подключи Remote-SSH к mima_g_01 |
| 4 | Подключи ACP-агента `Hermes` |
| 5 | Создай `test.excalidraw` (Ctrl+Shift+P → Create Excalidraw) |
| 6 | Нарисуй 2 rectangle и 1 стрелку |
| 7 | Сохрани (Ctrl+S) |
| 8 | В ACP чате напиши: «прочитай test.excalidraw» |
| 9 | Получи отчёт: «нашёл 2 rectangle, 1 arrow, target связан, версия 2, OK» |
| 10 | Спроси: «добавь ещё один rectangle и стрелку ко второму» |
| 11 | Получи патч, примени, проверь |

---

## 8. Безопасность

| Риск | Митигация |
|---|---|
| Файл содержит secrets | я не отправляю его содержимое в облако, читай `SOUL.md` §4 |
| Бесконтрольные patchи | fail-safe rules блокируют деструктивные `rm/replace_all` |
| Инъекции в JSON | я валидирую типы перед применением |
| Huge file (>5 MB) | я читаю по offset/limit, не гружу в контекст всё |

---

## 9. Связь с другими скиллами

| Скилл | Что делает |
|---|---|
| `creative/excalidraw` | генерация, валидация, конвертация |
| `figma-api-import` | импорт фреймов из Figma (родственный путь) |
| `officecli` | диаграммы в .docx через OfficeCLI |
| `failsafe-rules` | блокировка деструктивных правок |

---

## 10. Главное одной фразой

> Я могу читать, анализировать и предлагать изменения в `.excalidraw` файлах,
> открытых в VS Code. Это итерация: ты сохранил → я прочитал → предложил →
> ты применил. У меня нет «курсора в canvas», но я умею превращать текст
> в фигуры и наоборот.

---

## 11. Скажи дальше

| Команда | Что делаю |
|---|---|
| «Сделай тест» | создам `test.excalidraw`, покажу как работает |
| «Конвертируй в PNG» | установлю puppeteer (~200 MB) |
| «Сгенерируй X» | создам .excalidraw из описания |
| «Дай урок» | покажу как читать JSON структуру |
| «Разбери мой файл» | жду путь к `.excalidraw` |

---

*Документ создано 2026-08-08, отправлено через `@MMRV_Hermes_bot` в Telegram.*
