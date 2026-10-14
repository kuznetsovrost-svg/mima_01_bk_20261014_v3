═══════════════════════════════════════════════════════════════════
  Плейсхолдеры-FIMA-01
  Конвенция имён для плейсхолдеров в Figma
  при дизайне под экспорт в HTML+CSS
═══════════════════════════════════════════════════════════════════

Версия: 2026-07-23
Hermes Agent v0.18.0 на mima_g_01

═══════════════════════════════════════════════════════════════════
1. ГЛАВНОЕ ПРАВИЛО
═══════════════════════════════════════════════════════════════════

В Текстовом слое Figma пиши только плейсхолдер в фигурных скобках:

    Text: {<category>.<field>}

Не пиши реальный текст внутри скобок. Только имя плейсхолдера.

═══════════════════════════════════════════════════════════════════
2. ПРЯМОЙ ОТВЕТ — ПРИМЕР ДЛЯ ОТЧЁТА О ЗДОРОВЬЕ ПРОЕКТА
═══════════════════════════════════════════════════════════════════

Три строки:
  Отчёт о здоровье проекта <Такой-то проект>
  Подготовлен по базе <Такая-то база>
  Дата и время <Такое-то время и дата>

В Figma должны выглядеть так:

  ┌─ Frame: sec.header (Auto Layout vertical, gap: 8px)
     ├─ Text: {report.title}                 ← Inter Bold 32px
     ├─ Text: {report.subtitle}              ← Inter Regular 18px
     ├─ (gap 16px)
     └─ Frame: grp.meta (Auto Layout vertical, gap: 4px)
        ├─ Text: {report.database}           ← Inter Regular 14px, muted
        ├─ Text: {report.timestamp}          ← Inter Regular 14px, muted
        └─ Text: {report.author}            ← Inter Regular 14px, muted

При экспорте в HTML:

  <h1 class="report__title">Отчёт о здоровье проекта ИС Сириус</h1>
  <p class="report__subtitle">Квартальная сводка</p>
  <div class="report__meta">
    <p>Подготовлен по базе: project_metrics_2026_07</p>
    <p>Дата и время: 2026-07-23 14:30 MSK</p>
    <p>Автор: Hermes Agent</p>
  </div>

═══════════════════════════════════════════════════════════════════
3. ПОЧЕМУ ИМЕННО {category.field}
═══════════════════════════════════════════════════════════════════

✓ Фигурные скобки — однозначный маркер плейсхолдера
✓ Точка как разделитель — НЕ конфликтует с именами слоёв Figma
✓ Lowercase — никаких проблем с регистром
✓ Snake-case для составных имён: {report.project_name}

Когда я вижу в Figma слой `{report.title}`, я понимаю:
  - Это плейсхолдер (не реальный текст)
  - Ключ для подстановки — report.title
  - Семантика — заголовок отчёта

═══════════════════════════════════════════════════════════════════
4. ПОЛНАЯ КОНВЕНЦИЯ ИМЁН ПЛЕЙСХОЛДЕРОВ
═══════════════════════════════════════════════════════════════════

Заголовки:
  {page.title}              ← <h1>
  {page.subtitle}           ← <h2>
  {page.section_title}      ← <h2>, <h3>

Метаинформация:
  {report.title}
  {report.subtitle}
  {report.database}
  {report.timestamp}
  {report.author}
  {report.version}
  {report.id}

Контент:
  {section.title}
  {section.description}
  {section.body}
  {item.label}
  {item.value}
  {item.description}

Метрики:
  {metric.name}
  {metric.value}
  {metric.unit}
  {metric.delta}            ← +/- изменение
  {metric.status}           ← ok/warning/error

Кнопки и действия:
  {button.cta}              ← primary
  {button.secondary}        ← secondary
  {button.ghost}            ← tertiary
  {button.label}
  {button.href}

Изображения:
  {image.src}
  {image.alt}
  {image.title}
  {image.caption}

Навигация:
  {nav.menu[0].label}
  {nav.menu[0].href}
  {nav.menu[1].label}
  ...

Списки и массивы:
  {features[0].title}
  {features[0].body}
  {features[0].icon}
  {features[1].title}
  ...

Дата/время:
  {event.date}
  {event.time}
  {event.timestamp}

URL и контакты:
  {link.href}
  {link.label}
  {contact.email}
  {contact.phone}

═══════════════════════════════════════════════════════════════════
5. КОНВЕНЦИЯ ИМЁН СЛОЁВ И ФРЕЙМОВ В FIGMA
═══════════════════════════════════════════════════════════════════

Используй префиксы для типов слоёв:

  Префикс        Что в HTML           Пример
  ────────────   ──────────────       ─────────────────
  sec.           <section>            sec.hero, sec.features
  grp.           <div class="row">    grp.title, grp.meta
  cmp.           компонент            cmp.card, cmp.button
  btn.           <button>             btn.cta, btn.primary
  nav.           <nav>                nav.main
  ico.           <svg>                ico.check, ico.arrow
  img.           <img>                img.hero, img.logo
  ph.            placeholder          ph.avatar, ph.thumb
  txt.           <span>               txt.headline
  txt.           <p>                  txt.body
  fld.           поле формы           fld.email, fld.password

═══════════════════════════════════════════════════════════════════
6. СТРУКТУРА FIGMA-ФАЙЛА ДЛЯ ОТЧЁТА
═══════════════════════════════════════════════════════════════════

📁 Page: Project Health Report
└─ Artboard: Report — Desktop (1280×auto)

  ├─ sec.header (Auto Layout vertical, padding: 32px, gap: 8px)
  │  ├─ Text: {report.title}              (Inter Bold 32px, #1F2937)
  │  ├─ Text: {report.subtitle}           (Inter Regular 18px, #6B7280)
  │  ├─ (gap 16px)
  │  └─ grp.meta (Auto Layout vertical, gap: 4px)
  │     ├─ Text: {report.database}        (Inter Regular 14px, #6B7280)
  │     ├─ Text: {report.timestamp}       (Inter Regular 14px, #6B7280)
  │     └─ Text: {report.author}          (Inter Regular 14px, #6B7280)
  │
  ├─ sec.metrics (Auto Layout grid, 4 columns, gap: 16px)
  │  ├─ cmp.metric-card
  │  │  ├─ Text: {metrics[0].label}        (Inter Regular 14px)
  │  │  ├─ Text: {metrics[0].value}        (Inter Bold 28px)
  │  │  └─ Text: {metrics[0].delta}        (Inter Regular 12px, +green/-red)
  │  ├─ cmp.metric-card
  │  ├─ cmp.metric-card
  │  └─ cmp.metric-card
  │
  ├─ sec.details (Auto Layout vertical, padding: 24px)
  │  ├─ Text: {details.title}             (Inter SemiBold 20px)
  │  ├─ tbl.metrics (Table component)
  │  │  ├─ thead
  │  │  │  ├─ Text: {table[0].column_1}
  │  │  │  ├─ Text: {table[0].column_2}
  │  │  │  └─ Text: {table[0].column_3}
  │  │  └─ tbody
  │  │     ├─ row 1: {row[0].cells[0]} {row[0].cells[1]} ...
  │  │     └─ row N
  │  └─ Text: {details.footer}            (Inter Regular 14px)
  │
  └─ sec.footer (Auto Layout horizontal, padding: 24px)
     ├─ Text: {footer.copyright}          (Inter Regular 12px, #9CA3AF)
     ├─ (gap auto)
     ├─ btn.secondary
     │  └─ Text: {button.secondary}
     └─ btn.primary
        └─ Text: {button.cta}

═══════════════════════════════════════════════════════════════════
7. AUTO LAYOUT — КРИТИЧНО ДЛЯ ЧИСТОГО HTML
═══════════════════════════════════════════════════════════════════

Все секции должны быть Auto Layout. НЕ используй абсолютное
позиционирование (тогда плагин сгенерирует position: absolute мусор).

Плохо (absolute):

  ┌─────────────────┐
  │                 │
  │   Заголовок     │  ← positioned at x=24, y=16
  │                 │
  │   Описание      │  ← positioned at x=24, y=64
  │                 │
  └─────────────────┘

Хорошо (auto layout):

  Auto Layout (vertical)
    └─ padding: 24px
       └─ gap: 40px
          ├─ Text "Заголовок"
          └─ Text "Описание"

Параметры Auto Layout:
  - Direction: horizontal / vertical
  - Padding: top/right/bottom/left
  - Gap (itemSpacing)
  - Primary axis align: min/center/max/space-between
  - Counter axis align: min/center/max/stretch

═══════════════════════════════════════════════════════════════════
8. FIGMA STYLES — ДЛЯ CSS-ПЕРЕМЕННЫХ
═══════════════════════════════════════════════════════════════════

Создай Figma Styles для всех повторяющихся значений:

Color Styles:
  📁 Colors
  ├─ primary          → CSS --color-primary
  ├─ primary-hover    → CSS --color-primary-hover
  ├─ secondary        → CSS --color-secondary
  ├─ accent           → CSS --color-accent
  ├─ text             → CSS --color-text (#1F2937)
  ├─ text-muted       → CSS --color-text-muted (#6B7280)
  ├─ bg               → CSS --color-bg (#FFFFFF)
  ├─ bg-alt           → CSS --color-bg-alt (#F9FAFB)
  ├─ border           → CSS --color-border (#E5E7EB)
  ├─ success          → CSS --color-success (#10B981)
  ├─ warning          → CSS --color-warning (#F59E0B)
  └─ danger           → CSS --color-danger (#EF4444)

Text Styles:
  📁 Typography
  ├─ h1               → CSS .h1 (Inter Bold 32px)
  ├─ h2               → CSS .h2 (Inter Bold 24px)
  ├─ h3               → CSS .h3 (Inter SemiBold 20px)
  ├─ body             → CSS .body (Inter Regular 16px)
  ├─ body-sm          → CSS .body-sm (Inter Regular 14px)
  ├─ caption          → CSS .caption (Inter Regular 12px)
  └─ code             → CSS .code (JetBrains Mono 14px)

Effects:
  📁 Shadows
  ├─ shadow-sm        → CSS --shadow-sm
  ├─ shadow-md        → CSS --shadow-md
  └─ shadow-lg        → CSS --shadow-lg

Border Radius:
  📁 Radius
  ├─ radius-sm        → CSS --radius-sm (4px)
  ├─ radius-md        → CSS --radius-md (8px)
  └─ radius-lg        → CSS --radius-lg (16px)

═══════════════════════════════════════════════════════════════════
9. BREAKPOINTS — ОБЯЗАТЕЛЬНО ДЕЛАЙ ТРИ
═══════════════════════════════════════════════════════════════════

Создай 3 артборда для адаптивности:

  Artboard: Report — Mobile (375 × auto)
  Artboard: Report — Tablet (768 × auto)
  Artboard: Report — Desktop (1280 × auto)

Имена должны отражать breakpoint:
  - Report — Mobile
  - Report — Tablet
  - Report — Desktop

Плагин сгенерирует CSS с @media:

  /* Mobile (default) */
  .report__metrics { display: grid; gap: 8px; }

  /* Tablet */
  @media (min-width: 768px) {
    .report__metrics { grid-template-columns: repeat(2, 1fr); gap: 12px; }
  }

  /* Desktop */
  @media (min-width: 1024px) {
    .report__metrics { grid-template-columns: repeat(4, 1fr); gap: 16px; }
  }

═══════════════════════════════════════════════════════════════════
10. КОМПОНЕНТЫ — ДЛЯ ПЕРЕИСПОЛЬЗУЕМОГО HTML
═══════════════════════════════════════════════════════════════════

Создавай Figma Components для повторяющихся элементов:

cmp.metric-card (с variants):
  - default
  - warning
  - danger

  Внутри:
  ├─ Icon: ico.{metric.icon}
  ├─ Text: {metrics[N].label}
  ├─ Text: {metrics[N].value}
  └─ Text: {metrics[N].delta}

cmp.button:
  - primary
  - secondary
  - ghost

  Внутри:
  └─ Text: {button.label}

cmp.table-row:
  ├─ Text: {row[N].cell_1}
  ├─ Text: {row[N].cell_2}
  └─ Text: {row[N].cell_3}

Плагин сгенерирует переиспользуемые CSS-классы:

  .metric-card { ... }
  .metric-card--warning { background: var(--color-warning-bg); }
  .button { ... }
  .button--primary { ... }

═══════════════════════════════════════════════════════════════════
11. ЧТО НЕ ПИСАТЬ В FIGMA
═══════════════════════════════════════════════════════════════════

Плохо                                         Почему
──────────────────────────────────────         ────────────────────────
Text: "Отчёт о здоровье проекта ИС Сириус"   Реальный текст — не плейсхолдер
Text: отчёт о здоровье                        Без {} — не плейсхолдер
Text: Report Title                            Похоже на имя слоя, не placeholder
Text: {{report.title}}                        Двойные скобки — парсер может сломаться
Text: report.title                            Без скобок — точка путает с именами
Text: {REPORT.TITLE}                          Заглавные — нестандартно
Text: {отчёт.заголовок}                       Кириллица — может конфликтовать
Frame: Frame 1                                Без префикса sec./grp./cmp.
Frame: Rectangle 12                           Без префикса
Layer: Group 5                                Без префикса

═══════════════════════════════════════════════════════════════════
12. СРАВНЕНИЕ — ХОРОШО vs ПЛОХО
═══════════════════════════════════════════════════════════════════

Хорошо:
  Frame: sec.hero (Auto Layout vertical, padding: 64px, gap: 24px)
  ├─ Text: {hero.title}              (Inter Bold 56px)
  ├─ Text: {hero.subtitle}           (Inter Regular 20px)
  └─ Frame: btn.primary
     └─ Text: {hero.cta}

  → Экспортируется в:
    <section class="hero">
      <h1>Заголовок</h1>
      <p>Подзаголовок</p>
      <a class="btn btn--primary">Кнопка</a>
    </section>

Плохо:
  Rectangle: Hero Background        (без auto layout)
  Text: "Привет!"                   (реальный текст)
  Rectangle: CTA                    (без имени)

  → Экспортируется в:
    <div style="position:absolute;top:24px;left:24px;">
      Привет!
      <div style="position:absolute;top:80px;left:24px;"></div>
    </div>

═══════════════════════════════════════════════════════════════════
13. WORKFLOW ОТ FIGMA ДО HTML
═══════════════════════════════════════════════════════════════════

Шаг 1: Дизайн в Figma
  - Соблюдай конвенцию выше
  - Auto Layout везде
  - Плейсхолдеры в {}
  - Figma Styles для повторяющихся значений
  - 3 breakpoints (mobile/tablet/desktop)

Шаг 2: Экспорт через плагин
  - "Figma to HTML" by Builder.io
  - или Anima
  - или Locofy
  - или TeleportHQ
  Получишь ZIP с .html, .css, изображениями

Шаг 3: Передача агенту
  Пришли:
    - ZIP с экспортом
    - Скриншот артборда (для контроля)
    - Текстовое ТЗ (если есть особые требования)

Шаг 4: Агент переписывает
  Я перепишу в чистый семантический HTML:
    - Уберу wrapper-div'ы
    - Заменю абсолюты на flexbox/grid
    - Добавлю адаптивность (CSS Grid + @media)
    - Добавлю тёмную тему (prefers-color-scheme)
    - Добавлю accessibility (aria-*, alt, <label>)
    - Соберу CSS-переменные из Figma Styles

Шаг 5: Проверка
  - Открыть в браузере
  - Проверить mobile/tablet/desktop
  - Проверить тёмную тему
  - Проверить accessibility (Lighthouse)

═══════════════════════════════════════════════════════════════════
14. ЧАСТЫЕ ОШИБКИ
═══════════════════════════════════════════════════════════════════

❌ Ошибка 1: Реальный текст вместо плейсхолдера
   "Отчёт о здоровье проекта ИС Сириус" вместо {report.title}
   → При экспорте получишь статичный текст, не шаблон

❌ Ошибка 2: Абсолютное позиционирование
   Плагин не сможет сделать адаптивность
   → Используй Auto Layout

❌ Ошибка 3: Без префиксов в именах
   "Frame 1", "Rectangle 12"
   → Нечитаемые CSS-классы

❌ Ошибка 4: Inline-цвета в каждом слое
   Разные оттенки одного цвета в разных местах
   → Используй Figma Color Styles

❌ Ошибка 5: Только desktop
   Без mobile/tablet версий
   → Адаптив будет угадывать

❌ Ошибка 6: Слишком много wrapper'ов
   Rectangle > Group > Frame > Section
   → Плагин сгенерирует 5 уровней <div>

❌ Ошибка 7: Реальные длинные тексты
   Полный Lorem ipsum в макете
   → Замени короткими плейсхолдерами

═══════════════════════════════════════════════════════════════════
15. ШПАРГАЛКА
═══════════════════════════════════════════════════════════════════

Текст → плейсхолдер:
  ✓ {category.field}
  ✓ {category.subcategory.field}
  ✗ "реальный текст"

Слой/фрейм:
  ✓ sec.section_name
  ✓ grp.group_name
  ✓ cmp.component_name
  ✗ "Frame 1"

Структура:
  ✓ Auto Layout vertical/horizontal
  ✓ Padding + gap вместо absolute
  ✓ 3 breakpoints
  ✗ Только absolute positions

Стили:
  ✓ Figma Color Styles → CSS variables
  ✓ Figma Text Styles → CSS classes
  ✓ Figma Effects → CSS shadows
  ✗ Inline значения в каждом слое

═══════════════════════════════════════════════════════════════════
Конец документа.
Версия: 2026-07-23
Hermes Agent v0.18.0 на mima_g_01
═══════════════════════════════════════════════════════════════════
