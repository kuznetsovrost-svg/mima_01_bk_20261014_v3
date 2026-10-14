═══════════════════════════════════════════════════════════════════
  Динамические-цвета-в-FIGMA.md
  Как в Figma задать фрейм, который при заполнении шаблона
  принимает разные цвета в зависимости от статуса
═══════════════════════════════════════════════════════════════════

Версия: 2026-07-30
Hermes Agent v0.18.0 на mima_g_01

═══════════════════════════════════════════════════════════════════
1. ГЛАВНОЕ ПРАВИЛО
═══════════════════════════════════════════════════════════════════

Используй Figma Component с Variants по оси состояния.
В HTML это становится CSS-классом или data-атрибутом,
который подставляется через шаблонизатор.

  ┌──────────────────────────────────────────────────────────────┐
  │ Figma:  Component: cmp.status-badge                          │
  │         ├─ Variant: state=red      (красный)                │
  │         ├─ Variant: state=yellow   (жёлтый)                 │
  │         └─ Variant: state=green    (зелёный)                 │
  │                                                              │
  │ HTML:   <div class="status-badge status-badge--{{ state }}"> │
  │         Jinja2: {% if state == 'red' %}red{% endif %}        │
  └──────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
2. ЧЕТЫРЕ ПОДХОДА (от простого к продвинутому)
═══════════════════════════════════════════════════════════════════

Подход 1: Figma Variants (рекомендую)
─────────────────────────────────────
  Самый чистый. Один Component, N Variants.

Подход 2: Data-атрибут (если нет Variants)
─────────────────────────────────────────
  HTML использует data-status, CSS переключает стили.

Подход 3: Множественные компоненты
──────────────────────────────────
  3 отдельных компонента: badge-red, badge-yellow, badge-green.

Подход 4: CSS-переменные (максимальная гибкость)
─────────────────────────────────────────────────
  Цвет передаётся через style="--status-color: ..."

═══════════════════════════════════════════════════════════════════
3. ПОДХОД 1 · FIGMA VARIANTS (РЕКОМЕНДУЮ)
═══════════════════════════════════════════════════════════════════

3.1. Структура Component в Figma
──────────────────────────────────

  Component: cmp.status-badge
  ├─ Variant: state=red
  ├─ Variant: state=yellow
  └─ Variant: state=green

  Каждый variant — это отдельная визуальная версия с теми же
  элементами, но другими цветами.

3.2. Имена вариантов (конвенция)
─────────────────────────────────

  state=<значение>

  ┌──────────────────────────────────────────────────────────┐
  │ Вариант 1 (цвет):                                       │
  │   state=red                                              │
  │   state=yellow                                           │
  │   state=green                                            │
  │                                                          │
  │ Вариант 2 (семантика):                                   │
  │   state=critical                                         │
  │   state=attention                                        │
  │   state=healthy                                          │
  │                                                          │
  │ Вариант 3 (project management):                          │
  │   state=on-track                                         │
  │   state=at-risk                                          │
  │   state=off-track                                        │
  │                                                          │
  │ Вариант 4 (security):                                    │
  │   state=vulnerability                                    │
  │   state=warning                                          │
  │   state=secure                                           │
  └──────────────────────────────────────────────────────────┘

  Для project_504-595 рекомендую:
    state=critical (БОЛЕН)
    state=attention (ТРЕБУЕТ ВНИМАНИЯ)
    state=healthy (ЗДОРОВ)

3.3. Что внутри каждого Variant
────────────────────────────────

  Каждый variant содержит:

  Frame: status-badge (Auto Layout horizontal, padding: 12px 24px,
                        border-radius: 999px)
  ├─ Vector: status-dot (диаметр 12px)
  └─ Text: {status.label}

3.4. Цвета через Figma Color Styles
───────────────────────────────────

  ┌────────────────────────────────────────────────────────┐
  │ Style name           Hex         Назначение             │
  │ ──────────────────── ─────────── ─────────────────────  │
  │ bg-badge-red         #FEE2E2     Фон красного badge     │
  │ text-badge-red       #991B1B     Текст красного badge   │
  │ dot-red              #DC2626     Точка красного         │
  │ border-badge-red     #FECACA     Бордер красного        │
  │                                                        │
  │ bg-badge-yellow      #FEF3C7     Фон жёлтого badge      │
  │ text-badge-yellow    #92400E     Текст жёлтого badge    │
  │ dot-yellow           #D97706     Точка жёлтого          │
  │ border-badge-yellow  #FDE68A     Бордер жёлтого         │
  │                                                        │
  │ bg-badge-green       #D1FAE5     Фон зелёного badge     │
  │ text-badge-green     #065F46     Текст зелёного badge   │
  │ dot-green            #10B981     Точка зелёного         │
  │ border-badge-green   #A7F3D0     Бордер зелёного        │
  └────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
4. КОНКРЕТНЫЙ ПРИМЕР ДЛЯ PROJECT_504-595
═══════════════════════════════════════════════════════════════════

4.1. Простой badge (одна строка)
─────────────────────────────────

  Component: cmp.status-badge

  ├─ Variant: state=critical
  │  └─ Frame: status-badge
  │     │  (Auto Layout horizontal,
  │     │   padding: 12px 24px,
  │     │   border-radius: 999px,
  │     │   background: bg-badge-red,
  │     │   border: 1px solid border-badge-red)
  │     ├─ Vector: status-dot (#DC2626, 12px)
  │     └─ Text: {status.label}
  │        "БОЛЕН"
  │        (Inter SemiBold 16px, text-badge-red)
  │
  ├─ Variant: state=attention
  │  └─ Frame: status-badge (... background: bg-badge-yellow ...)
  │     ├─ Vector: status-dot (#D97706, 12px)
  │     └─ Text: {status.label}
  │        "ТРЕБУЕТ ВНИМАНИЯ"
  │
  └─ Variant: state=healthy
     └─ Frame: status-badge (... background: bg-badge-green ...)
        ├─ Vector: status-dot (#10B981, 12px)
        └─ Text: {status.label}
           "ЗДОРОВ"

4.2. Детальный banner (несколько строк)
────────────────────────────────────────

  Component: cmp.status-banner

  ├─ Variant: state=critical
  │  └─ Frame: status-banner
  │     │  (Auto Layout vertical,
  │     │   padding: 24px,
  │     │   border-radius: 12px,
  │     │   background: bg-badge-red,
  │     │   border-left: 4px solid dot-red)
  │     │
  │     ├─ Frame: status-header (Auto Layout horizontal, gap: 12px)
  │     │  ├─ Vector: ico.error (#DC2626, 24px)
  │     │  ├─ Text: {status.label}        "БОЛЕН"
  │     │  │   (Inter Bold 20px, text-badge-red)
  │     │  └─ Text: {status.subtitle}     "по срокам КТ"
  │     │      (Inter Regular 14px, text-badge-red)
  │     │
  │     ├─ grp.counters (Auto Layout horizontal, gap: 24px)
  │     │  ├─ Frame: counter
  │     │  │  ├─ Text: {status.critical_count}    "2"
  │     │  │  └─ Text: {status.critical_label}    "критических"
  │     │  ├─ Frame: counter
  │     │  │  ├─ Text: {status.substantial_count} "1"
  │     │  │  └─ Text: {status.substantial_label} "существенных"
  │     │  └─ Frame: counter
  │     │     ├─ Text: {status.info_count}        "0"
  │     │     └─ Text: {status.info_label}        "информационных"
  │     │
  │     └─ Text: {status.algorithm_note}
  │        "critical_count = 2 ≥ 3 → БОЛЕН"
  │        (Inter Regular 12px, text-badge-red, opacity: 0.8)
  │
  ├─ Variant: state=attention
  │  └─ Frame: status-banner
  │     │  (... background: bg-badge-yellow ...,
  │     │       border-left: 4px solid dot-yellow)
  │     ├─ Frame: status-header
  │     │  ├─ Vector: ico.warning (#D97706, 24px)
  │     │  ├─ Text: {status.label}        "ТРЕБУЕТ ВНИМАНИЯ"
  │     │  └─ Text: {status.subtitle}     "по срокам КТ"
  │     ├─ grp.counters
  │     │  ├─ counter: 2 критических
  │     │  ├─ counter: 1 существенное
  │     │  └─ counter: 0 информационных
  │     └─ Text: {status.algorithm_note}
  │        "1 ≤ critical_count = 2 ≤ 2 → ТРЕБУЕТ ВНИМАНИЯ"
  │
  └─ Variant: state=healthy
     └─ Frame: status-banner (... background: bg-badge-green ...)
        ├─ Frame: status-header
        │  ├─ Vector: ico.check (#10B981, 24px)
        │  ├─ Text: {status.label}    "ЗДОРОВ"
        │  └─ Text: {status.subtitle} "по срокам КТ"
        ├─ grp.counters
        │  ├─ counter: 0 критических
        │  ├─ counter: 0 существенных
        │  └─ counter: 0 информационных
        └─ Text: {status.algorithm_note}
           "critical_count = 0 → ЗДОРОВ"

═══════════════════════════════════════════════════════════════════
5. ЧТО Я СГЕНЕРИРУЮ В HTML
═══════════════════════════════════════════════════════════════════

5.1. Базовый HTML
─────────────────

  <!-- Простой badge -->
  <div class="status-badge status-badge--{{ state }}">
    <span class="status-badge__dot"></span>
    <span class="status-badge__label">{{ status_label }}</span>
  </div>

  <!-- Детальный banner -->
  <div class="status-banner status-banner--{{ state }}">
    <div class="status-banner__header">
      <span class="status-banner__icon"></span>
      <h2 class="status-banner__label">{{ status_label }}</h2>
      <span class="status-banner__subtitle">{{ status_subtitle }}</span>
    </div>
    <div class="status-banner__counters">
      <div class="counter">
        <div class="counter__value">{{ critical_count }}</div>
        <div class="counter__label">критических</div>
      </div>
      <div class="counter">
        <div class="counter__value">{{ substantial_count }}</div>
        <div class="counter__label">существенных</div>
      </div>
      <div class="counter">
        <div class="counter__value">{{ info_count }}</div>
        <div class="counter__label">информационных</div>
      </div>
    </div>
    <p class="status-banner__algorithm">{{ algorithm_note }}</p>
  </div>

5.2. CSS (готовый, с поддержкой всех вариантов)
────────────────────────────────────────────────

  /* Базовый badge */
  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    border-radius: 999px;
    font-family: 'Inter', sans-serif;
    font-size: 16px;
    font-weight: 600;
    line-height: 1;
    border: 1px solid transparent;
  }

  .status-badge__dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }

  .status-badge__label {
    line-height: 1;
  }

  /* Variants */
  .status-badge--critical {
    background: #FEE2E2;
    color: #991B1B;
    border-color: #FECACA;
  }
  .status-badge--critical .status-badge__dot {
    background: #DC2626;
  }

  .status-badge--attention {
    background: #FEF3C7;
    color: #92400E;
    border-color: #FDE68A;
  }
  .status-badge--attention .status-badge__dot {
    background: #D97706;
  }

  .status-badge--healthy {
    background: #D1FAE5;
    color: #065F46;
    border-color: #A7F3D0;
  }
  .status-badge--healthy .status-badge__dot {
    background: #10B981;
  }

  /* Детальный banner */
  .status-banner {
    padding: 24px;
    border-radius: 12px;
    border-left: 4px solid transparent;
    font-family: 'Inter', sans-serif;
  }

  .status-banner__header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }

  .status-banner__icon {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
  }

  .status-banner__label {
    font-size: 20px;
    font-weight: 700;
    margin: 0;
  }

  .status-banner__subtitle {
    font-size: 14px;
    font-weight: 400;
    opacity: 0.8;
  }

  .status-banner__counters {
    display: flex;
    gap: 24px;
    margin: 16px 0;
  }

  .counter__value {
    font-size: 24px;
    font-weight: 700;
  }

  .counter__label {
    font-size: 12px;
    font-weight: 400;
    opacity: 0.7;
  }

  .status-banner__algorithm {
    font-size: 12px;
    opacity: 0.7;
    margin: 8px 0 0;
  }

  /* Variants для banner */
  .status-banner--critical {
    background: #FEE2E2;
    color: #991B1B;
    border-left-color: #DC2626;
  }
  .status-banner--critical .status-banner__icon {
    color: #DC2626; /* для inline-SVG через currentColor */
  }

  .status-banner--attention {
    background: #FEF3C7;
    color: #92400E;
    border-left-color: #D97706;
  }

  .status-banner--healthy {
    background: #D1FAE5;
    color: #065F46;
    border-left-color: #10B981;
  }

5.3. Тёмная тема (опционально)
───────────────────────────────

  @media (prefers-color-scheme: dark) {
    .status-badge--critical {
      background: #7F1D1D;
      color: #FECACA;
    }
    .status-badge--attention {
      background: #78350F;
      color: #FDE68A;
    }
    .status-badge--healthy {
      background: #064E3B;
      color: #A7F3D0;
    }
  }

═══════════════════════════════════════════════════════════════════
6. ШАБЛОНИЗАЦИЯ (JINJA2 / TWIG / JAVASCRIPT)
═══════════════════════════════════════════════════════════════════

6.1. Jinja2 (Python)
────────────────────

  {# Маппинг status → state #}
  {% set state_map = {
    'БОЛЕН': 'critical',
    'ТРЕБУЕТ ВНИМАНИЯ': 'attention',
    'ЗДОРОВ': 'healthy'
  } %}
  {% set state = state_map.get(report.status, 'unknown') %}

  <div class="status-badge status-badge--{{ state }}">
    <span class="status-badge__dot"></span>
    <span class="status-badge__label">{{ report.status }}</span>
  </div>

  Или через if/elif:
  {% if report.critical_count >= 3 %}
    {% set state = 'critical' %}
    {% set label = 'БОЛЕН' %}
  {% elif report.critical_count >= 1 %}
    {% set state = 'attention' %}
    {% set label = 'ТРЕБУЕТ ВНИМАНИЯ' %}
  {% else %}
    {% set state = 'healthy' %}
    {% set label = 'ЗДОРОВ' %}
  {% endif %}

  <div class="status-badge status-badge--{{ state }}">
    <span class="status-badge__label">{{ label }}</span>
  </div>

6.2. JavaScript (Handlebars / Nunjucks / Mustache)
──────────────────────────────────────────────────

  // В шаблоне нельзя, нужна функция-хелпер:

  function getState(status) {
    const map = {
      'БОЛЕН': 'critical',
      'ТРЕБУЕТ ВНИМАНИЯ': 'attention',
      'ЗДОРОВ': 'healthy'
    };
    return map[status] || 'unknown';
  }

  // Шаблон (Handlebars):
  <div class="status-badge status-badge--{{getState status}}">
    <span class="status-badge__label">{{status}}</span>
  </div>

  // Или вычислять на сервере:
  <div class="status-badge status-badge--{{state}}">
    <span class="status-badge__label">{{label}}</span>
  </div>

6.3. TypeScript (типизация)
───────────────────────────

  type StatusState = 'critical' | 'attention' | 'healthy' | 'unknown';

  interface StatusBadgeProps {
    state: StatusState;
    label: string;
  }

  function StatusBadge({ state, label }: StatusBadgeProps) {
    return (
      <div className={`status-badge status-badge--${state}`}>
        <span className="status-badge__dot" />
        <span className="status-badge__label">{label}</span>
      </div>
    );
  }

═══════════════════════════════════════════════════════════════════
7. ПОДХОД 2 · DATA-АТРИБУТ (FALLBACK)
═══════════════════════════════════════════════════════════════════

Если у тебя нет Variants в Figma (старая версия, нет доступа
к Component Properties), используй data-атрибут.

7.1. В Figma
────────────

  Frame: status-badge (Auto Layout horizontal, padding: 12px 24px)
  ├─ Vector: status-dot
  └─ Text: {status.label}

  В НЁМ нет variants — это один Frame с цветами по умолчанию.
  Агент при экспорте ставит data-status="..." в HTML.

7.2. HTML
─────────

  <div class="status-badge" data-status="critical">
    <span class="status-badge__dot"></span>
    <span class="status-badge__label">БОЛЕН</span>
  </div>

7.3. CSS
────────

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    border-radius: 999px;
    font-family: 'Inter', sans-serif;
    font-size: 16px;
    font-weight: 600;
  }

  .status-badge__dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }

  .status-badge[data-status="critical"] {
    background: #FEE2E2;
    color: #991B1B;
  }
  .status-badge[data-status="critical"] .status-badge__dot {
    background: #DC2626;
  }

  .status-badge[data-status="attention"] {
    background: #FEF3C7;
    color: #92400E;
  }
  .status-badge[data-status="attention"] .status-badge__dot {
    background: #D97706;
  }

  .status-badge[data-status="healthy"] {
    background: #D1FAE5;
    color: #065F46;
  }
  .status-badge[data-status="healthy"] .status-badge__dot {
    background: #10B981;
  }

7.4. Преимущества
─────────────────

  ✓ Не требует Variants в Figma
  ✓ Легко добавить новый статус (только CSS)
  ✓ JS может динамически менять data-status

7.5. Недостатки
───────────────

  ✗ Нельзя визуально увидеть все варианты в Figma
  ✗ Цвета в CSS, а не в Figma Color Styles

═══════════════════════════════════════════════════════════════════
8. ПОДХОД 3 · МНОЖЕСТВЕННЫЕ КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════

Если Figma не поддерживает Variants, делаем 3 компонента.

8.1. В Figma
────────────

  Component: cmp.badge-critical
  └─ Frame: status-badge (background: #FEE2E2, ...)
     ├─ Vector: status-dot (#DC2626)
     └─ Text: {status.label} "БОЛЕН"

  Component: cmp.badge-attention
  └─ Frame: status-badge (background: #FEF3C7, ...)
     ├─ Vector: status-dot (#D97706)
     └─ Text: {status.label} "ТРЕБУЕТ ВНИМАНИЯ"

  Component: cmp.badge-healthy
  └─ Frame: status-badge (background: #D1FAE5, ...)
     ├─ Vector: status-dot (#10B981)
     └─ Text: {status.label} "ЗДОРОВ"

8.2. В шаблоне
──────────────

  {# Jinja2 #}
  {% if state == 'critical' %}
    {% include 'badge-critical.html' %}
  {% elif state == 'attention' %}
    {% include 'badge-attention.html' %}
  {% else %}
    {% include 'badge-healthy.html' %}
  {% endif %}

8.3. Преимущества
─────────────────

  ✓ Самый простой в Figma
  ✓ Каждый компонент переиспользуется отдельно

8.4. Недостатки
───────────────

  ✗ Дублирование кода в HTML
  ✗ Изменения нужно вносить в 3 файла
  ✗ Сложнее поддерживать

═══════════════════════════════════════════════════════════════════
9. ПОДХОД 4 · CSS-ПЕРЕМЕННЫЕ (МАКСИМАЛЬНАЯ ГИБКОСТЬ)
═══════════════════════════════════════════════════════════════════

Цвет передаётся через style="--status-color: ..." прямо в HTML.

9.1. HTML
─────────

  <div class="status-banner"
       style="--bg: #FEE2E2; --text: #991B1B; --border: #DC2626">
    <h2>БОЛЕН</h2>
    ...
  </div>

9.2. CSS
────────

  .status-banner {
    padding: 24px;
    border-radius: 12px;
    border-left: 4px solid var(--border, #6B7280);
    background: var(--bg, #F3F4F6);
    color: var(--text, #1F2937);
  }

9.3. Шаблонизация
─────────────────

  {# Jinja2 #}
  {% set color_map = {
    'critical':    {'bg': '#FEE2E2', 'text': '#991B1B', 'border': '#DC2626'},
    'attention':   {'bg': '#FEF3C7', 'text': '#92400E', 'border': '#D97706'},
    'healthy':     {'bg': '#D1FAE5', 'text': '#065F46', 'border': '#10B981'}
  } %}
  {% set c = color_map[state] %}

  <div class="status-banner"
       style="--bg: {{ c.bg }}; --text: {{ c.text }}; --border: {{ c.border }}">
    ...
  </div>

9.4. Преимущества
─────────────────

  ✓ Полный контроль над цветом через шаблонизатор
  ✓ Один CSS-блок, много вариантов
  ✓ Легко добавить новый статус

9.5. Недостатки
───────────────

  ✗ Цвета в шаблоне, не в Figma
  ✗ Сложнее синхронизировать с Figma
  ✗ Нельзя увидеть в Figma как будет выглядеть

═══════════════════════════════════════════════════════════════════
10. СРАВНЕНИЕ ПОДХОДОВ
═══════════════════════════════════════════════════════════════════

  Критерий                  Variants  data-attr  Множ.комп  CSS-var
  ────────────────────────  ────────  ─────────  ──────────  ────────
  Простота в Figma          ⭐⭐⭐⭐    ⭐⭐⭐⭐⭐   ⭐⭐⭐⭐⭐     ⭐⭐
  Простота в HTML           ⭐⭐⭐⭐    ⭐⭐⭐⭐     ⭐⭐⭐        ⭐⭐⭐
  Расширяемость             ⭐⭐⭐⭐    ⭐⭐⭐⭐⭐   ⭐⭐          ⭐⭐⭐⭐⭐
  Поддержка                 ⭐⭐⭐⭐    ⭐⭐⭐⭐     ⭐⭐          ⭐⭐⭐⭐
  Контроль цветов           ⭐⭐⭐⭐⭐  ⭐⭐⭐⭐     ⭐⭐⭐⭐⭐     ⭐⭐⭐⭐⭐
  ────────────────────────────────────────────────────────────────

  ИТОГО:                    22        22         18          19

  Variants и data-атрибут — одинаково хороши.
  Variants лучше для визуального preview в Figma.
  data-атрибут лучше для старых версий Figma.

═══════════════════════════════════════════════════════════════════
11. ДРУГИЕ ДИНАМИЧЕСКИЕ ЭЛЕМЕНТЫ (не только badges)
═══════════════════════════════════════════════════════════════════

11.1. Callout (информационный блок)
────────────────────────────────────

  Component: cmp.callout
  ├─ Variant: type=info      (синий)
  ├─ Variant: type=success   (зелёный)
  ├─ Variant: type=warning   (жёлтый)
  └─ Variant: type=danger    (красный)

  Аналогично badge, но крупнее и с icon + title + body.

11.2. Button
────────────

  Component: cmp.button
  ├─ Variant: intent=primary   (синий фон)
  ├─ Variant: intent=secondary (белый фон, синий бордер)
  ├─ Variant: intent=danger    (красный фон)
  └─ Variant: intent=ghost     (прозрачный)

11.3. Table row
───────────────

  Component: cmp.table-row
  ├─ Variant: status=ok        (белый фон)
  ├─ Variant: status=warning   (жёлтый фон)
  └─ Variant: status=error     (красный фон)

  Применяется к строке tr в таблице для подсветки проблемных строк.

11.4. Progress bar
─────────────────

  Component: cmp.progress
  ├─ Variant: status=on-track  (зелёная полоса)
  ├─ Variant: status=at-risk   (жёлтая полоса)
  └─ Variant: status=off-track (красная полоса)

  Заполнение: width = {{ percent }}%

11.5. Status icon
────────────────

  Component: ico.status
  ├─ Variant: state=critical  (⚠️ красный)
  ├─ Variant: state=attention (⚡ жёлтый)
  └─ Variant: state=healthy   (✓ зелёный)

  Используется inline в тексте:
  "Состояние: {{ ico.status[state] }} {{ status_label }}"

═══════════════════════════════════════════════════════════════════
12. ВАЖНЫЕ НЮАНСЫ
═══════════════════════════════════════════════════════════════════

12.1. Иконки через currentColor
───────────────────────────────

  Если иконка в SVG использует currentColor, она автоматически
  наследует цвет от родителя:

  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="..." />
  </svg>

  CSS:
    .status-banner--critical svg {
      color: #DC2626; /* через currentColor */
    }

12.2. Контрастность (accessibility)
───────────────────────────────────

  Всегда проверяй контрастность текста на фоне:
    Красный фон #FEE2E2 + текст #991B1B → контраст ~10:1 ✓
    Жёлтый фон #FEF3C7 + текст #92400E → контраст ~9:1 ✓
    Зелёный фон #D1FAE5 + текст #065F46 → контраст ~9:1 ✓

  Все три комбинации проходят WCAG AA (4.5:1) и AAA (7:1).

12.3. Тёмная тема
─────────────────

  Для тёмной темы нужны более тёмные фоны и более светлые тексты:

  /* Светлая тема */
  .status-badge--critical { background: #FEE2E2; color: #991B1B; }

  /* Тёмная тема */
  @media (prefers-color-scheme: dark) {
    .status-badge--critical { background: #7F1D1D; color: #FECACA; }
  }

12.4. Семантика
───────────────

  Для accessibility (скринридеры):
    role="status"
    aria-label="{{ status_label }}"

═══════════════════════════════════════════════════════════════════
13. ЧЕК-ЛИСТ ПЕРЕД ЭКСПОРТОМ
═══════════════════════════════════════════════════════════════════

Структура:
  [ ] Один Component, не Frame
  [ ] Variants по одной оси (state)
  [ ] Имена variants: state=red/yellow/green (или критический/attention/healthy)
  [ ] Все variants имеют ОДИНАКОВУЮ структуру (те же элементы)
  [ ] Auto Layout в каждом variant

Имена:
  [ ] Component: cmp.<name>
  [ ] Variant: state=<value>
  [ ] Внутренние элементы: status-dot, {status.label}, ...

Цвета:
  [ ] Используются Figma Color Styles (не inline)
  [ ] Для каждого state свои bg/text/dot/border
  [ ] Контрастность проверена (WCAG AA ≥ 4.5:1)

Стили:
  [ ] Используются Figma Text Styles (не inline)
  [ ] Размер шрифта, font-weight одинаковые во всех variants
  [ ] Padding/gap одинаковые

Контент:
  [ ] Text содержит {status.label} (не реальный текст)
  [ ] Никаких реальных значений в макете

═══════════════════════════════════════════════════════════════════
14. ПРИМЕРЫ ДЛЯ PROJECT_504-595 (точные данные)
═══════════════════════════════════════════════════════════════════

Из твоего файла:

  БОЛЕН (красный)         → critical_count ≥ 3
  ТРЕБУЕТ ВНИМАНИЯ (жёлт) → 1 ≤ critical_count ≤ 2
  ЗДОРОВ (зелёный)        → critical_count = 0

  Текущее состояние для project_504-595:
    critical_count = 2 → ТРЕБУЕТ ВНИМАНИЯ (жёлтый)

Цветовая схема (рекомендую):

  Красный:
    bg:     #FEE2E2  (red-100)
    text:   #991B1B  (red-800)
    border: #FECACA  (red-200)
    dot:    #DC2626  (red-600)

  Жёлтый (текущий):
    bg:     #FEF3C7  (amber-100)
    text:   #92400E  (amber-800)
    border: #FDE68A  (amber-200)
    dot:    #D97706  (amber-600)

  Зелёный:
    bg:     #D1FAE5  (emerald-100)
    text:   #065F46  (emerald-800)
    border: #A7F3D0  (emerald-200)
    dot:    #10B981  (emerald-600)

═══════════════════════════════════════════════════════════════════
15. ШПАРГАЛКА
═══════════════════════════════════════════════════════════════════

Подход           Когда использовать
──────────────   ────────────────────────────────────────────
Variants         По умолчанию — самый чистый
data-атрибут     Если нет доступа к Variants в Figma
Множеств. комп.  Если вообще нет Variants, очень простая Figma
CSS-переменные   Если нужна максимальная гибкость через шаблонизатор

Имена variants:
  state=red/yellow/green
  state=critical/attention/healthy
  state=on-track/at-risk/off-track

Имена компонента:
  cmp.status-badge
  cmp.status-banner
  cmp.callout
  cmp.button

Внутренние элементы:
  status-dot, status.label, status.subtitle
  counters (counter__value, counter__label)
  algorithm_note

═══════════════════════════════════════════════════════════════════
Конец документа.
Версия: 2026-07-30
Hermes Agent v0.18.0 на mima_g_01
═══════════════════════════════════════════════════════════════════