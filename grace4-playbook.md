# GRACE 4 — Playbook по использованию

> Подробный гайд по методологии **GRACE (Graph-RAG Anchored Code Engineering)**, версия 4.
> Источник: репозиторий [osovv/grace-marketplace](https://github.com/osovv/grace-marketplace) (текущая стабильная 4.0.x; packaged 4.0.4). Гайд собран из `SKILL.md` всех 15 скиллов, шаблонов инициализации, reference-документов и реальных XML-шаблонов change-spec/change-plan.
>
> Цель — дать вам **необходимый и достаточный** объём знаний, чтобы спроектировать свой аналогичный процесс на базе скиллов (без копирования XML-формата — структура важнее формы).

---

## 0. Ориентация за 60 секунд

**GRACE — это не фреймворк и не библиотека.** Это методология + набор из 15 AI-скиллов + опциональный CLI (`@osovv/grace-cli`), которая превращает кодовую базу в структуру, **навигируемую LLM-агентом между сессиями**. Решает четыре проблемы AI-кодинга:

| Проблема | Решение GRACE |
|---|---|
| Агент не знает, какие модули есть и как связаны | `.grace/graph/` — единственный источник истины о структуре |
| Агент пишет код без понимания, что от него хотят | `MODULE_CONTRACT` в каждом файле + `GraceChangeSpec` (что) → `GraceChangePlan` (как) |
| Агент теряет нить внутри больших файлов | `START_BLOCK_* / END_BLOCK_*` — семантические блоки ≈500 токенов |
| Агент не оставляет доказательств, что код корректен | `.grace/verification/` с `V-M-*` записями + обязательные лог-маркеры |

**Главный принцип: process-first, not prompt-first.** Цель — сделать хорошее исполнение *скучным*: определить контракт, назвать поверхности, спланировать верификацию, выдать воркеру ограниченный пакет, попросить выполнить.

**PCAM (Governed Autonomy) = Purpose, Constraints, Autonomy, Metrics:**
- **Purpose** — из контракта (что строим)
- **Constraints** — из плана и графа (что нельзя трогать)
- **Autonomy** — воркер сам решает, *как* реализовать
- **Metrics** — `OUTPUTS` контракта + verification evidence показывают, что готово

Свобода в «как», но не в «что». Если контракт неверен — предложите изменение, не дрейфуйте.

---

## 1. Шесть базовых принципов

1. **Никогда не писать код без контракта.** До генерации/правки модуля — `MODULE_CONTRACT` с `PURPOSE / SCOPE / INPUTS / OUTPUTS`. Контракт — источник истины, код его реализует.
2. **Семантическая разметка — это не комментарии.** Маркеры `// START_BLOCK_X` / `// END_BLOCK_X` — навигационные якоря и точки внимания для LLM-контекста, не документация.
3. **Knowledge graph всегда актуален.** Добавил модуль — добавь в граф. Добавил зависимость — добавь `<CrossLink>`. Граф не должен дрейфовать.
4. **Top-down синтез.** Строгий конвейер: `Requirements → Technology → Development Plan → Verification Plan → Module Contracts → Code + Tests`. Нельзя перескакивать.
5. **Верификация — это архитектура.** Тесты, трассы и лог-маркеры — часть чертежа, а не уборка. Если другой агент не может проверить/отладить модуль по оставленным следам — модуль не готов.
6. **Top-down плюс governed autonomy.** См. PCAM выше.

---

## 2. Карта артефактов и каталог скиллов

### 2.1 Где что лежит (после `$grace-init`)

```
project/
├── AGENTS.md                           # протокол проекта для агента
├── .grace/
│   ├── context/                        # что и зачем строим
│   │   ├── requirements.xml
│   │   ├── technology.xml
│   │   ├── principles.xml
│   │   ├── deployment.xml
│   │   └── ux-guidelines.xml
│   ├── graph/                          # текущая карта модулей
│   │   ├── index.xml                   # роутинг GD-* документов
│   │   └── main.xml (и др.)            # сами GD-* документы с M-*, DF-*
│   ├── verification/                   # текущий projection верификации
│   │   ├── index.xml                   # роутинг VD-* документов
│   │   └── main.xml (и др.)            # VD-* документы с V-M-* записями
│   └── changes/
│       ├── active/C-*/                 # текущие спек и план
│       │   ├── spec.xml
│       │   ├── design-context.xml      # опционально, ненормативно
│       │   └── plan.xml
│       └── archive/C-*/                # завершённые/отменённые
└── src/, tests/                        # код с file-local разметкой
```

### 2.2 Каталог 15 скиллов и роли

| Скилл | Когда вызывать | Что делает |
|---|---|---|
| `grace-init` | Новый проект | Создаёт скелет `.grace/` из шаблонов, заполняет плейсхолдеры |
| `grace-spec` | Новая фича / изменение | Создаёт `GraceChangeSpec` (C-*) в `changes/active/`. Задаёт вопросы по одному. Статус `draft` → `approved` только по явному одобрению |
| `grace-plan` | После одобрения spec | Создаёт `GraceChangePlan` (C-*) с `BaselineAssertions`, `TargetAssertions`, `DurableScope`, `ObservedWriteScope`, `ImplementationPlan` с `T-*` задачами |
| `grace-execute` | Утверждённый plan | Последовательное исполнение с компактными execution-пакетами, scoped review, level-based verification, коммитами |
| `grace-multiagent-execute` | Параллельная работа | То же, но волнами с профилями `safe / balanced / fast`, контроллер-менеджер синхронизирует shared-артефакты |
| `grace-verification` | Модулю нужна верификация | Строит/обновляет `V-M-*` записи: команды, сценарии, обязательные лог-маркеры, evidence |
| `grace-refactor` | Rename / move / split / merge / extract | Безопасно правит код + синхронно правит `.grace/graph/`, `.grace/verification/`, `LINKS:`, контракты |
| `grace-fix` | Баг | Двигается от failure → `.grace/graph` → `.grace/verification` → file-local контракты → минимальный фикс |
| `grace-refresh` | Подозрение на дрейф | Сравнивает код с `.grace/context`, `.grace/graph`, `.grace/verification`, активными change-скоупами; предлагает reconciliation change |
| `grace-reviewer` | Code review | Проверяет семантическую целостность, консистентность графа, качество верификации |
| `grace-status` | Любой момент | `grace status --path .` — снимок здоровья проекта и «следующее безопасное действие» |
| `grace-ask` | Вопросы по проекту | Отвечает по `.grace/`, цитирует артефакты, различает durable state и active change |
| `grace-cli` | Работа с CLI | Шпаргалка по командам `grace lint / status / module / verification / file` |
| `grace-explainer` | Объяснить GRACE | Сам — то, что вы сейчас читаете, в формате скилла |
| `grace-setup-subagents` | Настройка пресетов воркеров/ревьюеров | Скаффолдит shell-специфичные пресеты для воркер-агентов |
| `grace-migrate` | С GRACE 3 на 4 | Применяется агентом, валидируется CLI; НЕ молча конвертирует docs/ |

### 2.3 Lifecycle (главный цикл)

```
$grace-init                    ← один раз на проект
   ↓
$grace-spec  → (draft) → утверждение → status="approved"
   ↓
$grace-plan  → (draft) → утверждение → status="approved"
   ↓
grace lint --assertions current    ← active-baseline preflight
grace lint --change C-XXX --assertions baseline --run-commands   ← перед записью
   ↓
$grace-execute (или $grace-multiagent-execute)
   ↓
grace lint --change C-XXX --assertions final --run-commands      ← apply/archive gate
$grace-status
```

**Золотое правило:** утверждённый plan — неизменяемое execution evidence. Если надо изменить baseline/target/scopes/tasks/verification gates — создаётся **заменяющий** C-* bundle, старый помечается `superseded`. Не правьте approved plan in place.

---

## 3. Пошаговый playbook: от пустого репо до merge

### Шаг 1. Bootstrap: `$grace-init`

Запускается первым. Скилл задаёт 9 вопросов (имя проекта, аннотация, ключевые слова, язык/рантайм/фреймворк, тестовый стек, observability, deployment, UX-применимость, известные модули) и создаёт 10 файлов из шаблонов:

| Шаблон | Целевой файл |
|---|---|
| `assets/AGENTS.md.template` | `AGENTS.md` |
| `assets/.grace/context/requirements.xml.template` | `.grace/context/requirements.xml` |
| `assets/.grace/context/technology.xml.template` | `.grace/context/technology.xml` |
| `assets/.grace/context/principles.xml.template` | `.grace/context/principles.xml` |
| `assets/.grace/context/deployment.xml.template` | `.grace/context/deployment.xml` |
| `assets/.grace/context/ux-guidelines.xml.template` | `.grace/context/ux-guidelines.xml` |
| `assets/.grace/graph/index.xml.template` | `.grace/graph/index.xml` |
| `assets/.grace/graph/main.xml.template` | `.grace/graph/main.xml` |
| `assets/.grace/verification/index.xml.template` | `.grace/verification/index.xml` |
| `assets/.grace/verification/main.xml.template` | `.grace/verification/main.xml` |

**Hard rules:**
- Все XML — `graceVersion="4.0"`.
- Семантические якоря — XML-теги, не атрибуты (это recurring тема, см. §5).
- Не создавать фиктивные C-* бандлы.
- Если `.grace/` уже есть — **стоп и спросить** (keep / merge / overwrite каждого файла). Никогда не перезаписывать молча.
- Если есть legacy `docs/*.xml` (GRACE 3) — **не конвертировать и не удалять**, направить на `$grace-migrate`.

### Шаг 2. Спецификация: `$grace-spec`

Скилл **задаёт по одному фокусному вопросу**, пока не станут ясны: цель, scope, ограничения, non-goals, acceptance criteria, затронутые области, ожидания по верификации. Затем предлагает краткий design summary + явные assumptions → ждёт approval → создаёт bundle.

**Структура bundle (`.grace/changes/active/C-ADD-AUTH/`):**

```
spec.xml              ← нормативный GraceChangeSpec (status: draft → approved)
design-context.xml    ← ненормативный, опционально (rationale, alternatives, scenarios)
plan.xml              ← создаётся позже $grace-plan, не здесь
```

**Жёсткий контракт spec.xml:** ровно один осмысленный блок `Summary / Goals / Constraints / NonGoals / AcceptanceCriteria / AffectedAreas / VerificationIntent`. Пустые контейнеры — не approval-ready.

**Шаблон spec.xml** (реальный, из `plugins/grace/skills/grace/grace-spec/references/change-spec-template.xml`):

```xml
<GraceChangeSpec graceVersion="4.0" status="draft">
  <C-CHANGE-ID>
    <Summary>$SUMMARY</Summary>
    <Problem>$PROBLEM</Problem>
    <Goals>
      <Goal>$GOAL</Goal>
    </Goals>
    <Constraints>
      <Constraint>$CONSTRAINT</Constraint>
    </Constraints>
    <NonGoals>
      <NonGoal>$NON_GOAL</NonGoal>
    </NonGoals>
    <AcceptanceCriteria>
      <Criterion>$ACCEPTANCE_CRITERION</Criterion>
    </AcceptanceCriteria>
    <AffectedAreas>
      <M-AFFECTED-MODULE />
    </AffectedAreas>
    <VerificationIntent>
      <ExpectedCommand>$EXPECTED_COMMAND</ExpectedCommand>
      <ExpectedEvidence>$EXPECTED_EVIDENCE</ExpectedEvidence>
    </VerificationIntent>
    <Assumptions>
      <Assumption>$ASSUMPTION</Assumption>
    </Assumptions>
  </C-CHANGE-ID>
</GraceChangeSpec>
```

**Hard rules:** spec — нормативен, design-context — только пояснительная память. Не имплементировать код, не мутировать текущее состояние графа/верификации, не делать ретроактивных change-бандлов.

### Шаг 3. Планирование: `$grace-plan`

Превращает одобренный spec в план. Пререквизиты: `requirements.xml` (минимум один UseCase), `technology.xml` (решения по стеку), `verification-plan.xml` (должен существовать как минимум шаблон).

**Архитектурные принципы плана:**

- **Contract-first design.** Каждый модуль получает `MODULE_CONTRACT` (PURPOSE / SCOPE / DEPENDS / LINKS) **до** любого кода.
- **Module taxonomy.** Каждый модуль классифицируется: `ENTRY_POINT | CORE_LOGIC | DATA_LAYER | UI_COMPONENT | UTILITY | INTEGRATION`.
- **Semantic anchoring.** Имена должны нести доменный смысл, не абстрактные ID.
- **Reliability-first stack.** В `technology.xml` явно назвать предпочтительные рантайм-библиотеки, тестовые инструменты, логирование, фреймворки; пометить discouraged-варианты.
- **Knowledge graph design.** Уникальный `M-xxx NAME="..." TYPE="..."` ID; функции `fn-name`, типы `type-Name`; `CrossLink` между зависимыми модулями; в shared XML — только публичный контракт, без приватных хелперов.
- **Verification-aware planning.** Для каждого значимого модуля задать `verification-ref` вида `V-M-xxx`, candidate source/test targets, критичные сценарии.

**Шаблон plan.xml** (реальный, из `plugins/grace/skills/grace/grace-plan/references/change-plan-template.xml`):

```xml
<GraceChangePlan graceVersion="4.0" status="draft">
  <C-CHANGE-ID>
    <IntentSummary>$INTENT_SUMMARY</IntentSummary>
    <BaselineAssertions>
      <MustExist>
        <Value>M-EXISTING-MODULE</Value>
      </MustExist>
    </BaselineAssertions>
    <TargetAssertions>
      <MustVerify>
        <Module>M-TARGET-MODULE</Module>
      </MustVerify>
      <MustPassCommand>
        <Command>bun run check</Command>
      </MustPassCommand>
    </TargetAssertions>
    <DurableScope>
      <GraphAnchors>
        <M-TARGET-MODULE />
      </GraphAnchors>
      <VerificationAnchors>
        <V-M-TARGET-MODULE />
      </VerificationAnchors>
      <ContextArtifact>requirements.xml</ContextArtifact>
    </DurableScope>
    <ObservedWriteScope>
      <File>src/path/to/file.ts</File>
      <Glob>tests/**/*.test.ts</Glob>
    </ObservedWriteScope>
    <ImplementationPlan>
      <T-001>
        <Title>$TASK_TITLE</Title>
        <!-- comma-separated: T-001, T-002. Только реальные зависимости. -->
        <DependsOn></DependsOn>
        <AcceptanceCriteria>
          <Criterion>$TASK_ACCEPTANCE</Criterion>
        </AcceptanceCriteria>
        <Verification>
          <Command>$TASK_VERIFICATION_COMMAND</Command>
        </Verification>
      </T-001>
    </ImplementationPlan>
  </C-CHANGE-ID>
</GraceChangePlan>
```

**Ключевые понятия:**
- `BaselineAssertions` — что должно быть true до начала работы (existing modules, etc).
- `TargetAssertions` — что должно стать true после (`MustVerify` для модулей, `MustPassCommand` для тестов — это **единственный** путь реально запустить команду в verification gate).
- `DurableScope` — какие anchors в `.grace/` будут тронуты (graph/verification/context).
- `ObservedWriteScope` — какие файлы будут реально меняться.
- `T-XXX` — задачи имплементации, могут зависеть друг от друга через `<DependsOn>T-001, T-002</DependsOn>` (CSV).

**Четыре evidence-момента плановых assertion'ов:**
- `current` — active-baseline preflight, **только до** наблюдаемых записей
- `baseline` (selected) — должен пройти сразу перед правкой
- `target` (selected) — доказывает состояние после правки
- `final` (selected) — внешний apply/archive gate

`MustPassCommand` — leaf project evidence (tests, typecheck, build, format). **Запрещено** вкладывать `grace lint`/`grace status`/другие lifecycle-команды внутрь plan assertions.

### Шаг 4. Preflight gates

```bash
# 1. Active-baseline integrity check — ДО первой записи
grace lint --path . --assertions current

# 2. Перед началом правки — baseline должен пройти
grace lint --path . --change C-ADD-AUTH --assertions baseline --run-commands

# 3. Снимок здоровья
grace status --path . --json
```

Если `grace status` показывает `needs-plan`, `needs-plan-approval`, `stale-plan`, `integrity-issues` — не идти в execute. Решать через spec/plan/refresh сначала.

### Шаг 5. Исполнение: `$grace-execute` или `$grace-multiagent-execute`

**Выбор между ними:**

| Ситуация | Что использовать |
|---|---|
| Зависимостный риск > выигрыш от параллелизма, осталось мало модулей | `grace-execute` |
| Модули независимы, есть module-local verification, нужна скорость | `grace-multiagent-execute` |
| Несколько агентов трогают один модуль / shared XML / tightly-coupled slice | **Не multiagent**. Использовать `grace-execute` |

**Принцип multiagent:** параллелизируем **имплементацию модулей**, а не **архитектурную истину**. Один контроллер владеет shared-артефактами, воркеры — только своими файлами и тестами. Скорость — за счёт лучшей упаковки контекста, батчинга shared-работы и scoped review, а не за счёт разрешения воркерам выдумывать архитектуру.

**Профили multiagent (по умолчанию `balanced`):**

- `safe` — спрашивать одобрения волн до запуска; contract + verification review для каждого модуля; targeted graph sync после каждой волны, full refresh на phase boundary. Для новых/рискованных модулей.
- `balanced` — один approval на расписание в начале; компактные execution-пакеты; module-local verification на воркера, scoped gate review на модуль, batched integrity checks на волну/фазу; targeted sync после волны, full refresh только на phase boundary, при подозрении на дрейф или при wrap-up.
- `fast` — минимум трения. (В тексте SKILL.md виден, но не полностью выгружен в этом исследовании; см. raw файл в репо для деталей.)

**Алгоритм execute (шаги):**

1. **Load & parse plan once.** Контроллер один раз читает `development-plan.xml`, `knowledge-graph.xml`, `verification-plan.xml` и строит execution queue. С CLI: `grace module show M-XXX --with verification` для shared/public части пакета, `grace file show --contracts --blocks` для local/private.
2. **Собрать execution queue:** `Phase-N` где `status="pending"` → внутри `step-N` в порядке.
3. **Построить execution packet на каждый шаг** (контроллер владеет): module ID + purpose; точные пути и write scope; preferred stack excerpt; module contract excerpt; graph entry excerpt; dependency contract summaries; verification excerpt с module-local командой и обязательными маркерами.
4. **Шагнуть.** Воркер получает пакет → пишет код в семантических блоках с контрактами → запускает module-local verification → оставляет checkpoint-отчёт.
5. **Scoped review** наименьшего безопасного объёма.
6. **Уровни верификации (не повторять весь-репо после каждого шага):**
   - **Module level** — быстрые проверки, воркер запускает один
   - **Wave level** — только для merged surfaces, тронутых волной
   - **Phase level** — более широкий regression + integrity
7. **Retry budget per step.** Когда пакет или контракт неверны — **стоп и replan**, не дрейфовать.
8. **Коммит** после валидированного sequential-шага.

**Контроллерные чекпоинты важнее чат-интервенций в полёте.** Пакеты пересматриваются между волнами, не надеждой что воркер самокорректируется от расплывчатых подсказок.

### Шаг 6. Финальный gate

```bash
# Перед apply/archive — финальный gate
grace lint --path . --change C-ADD-AUTH --assertions final --run-commands

# Применяем change bundle
mv .grace/changes/active/C-ADD-AUTH .grace/changes/archive/C-ADD-AUTH

# Обновляем durable state (graph, verification) если менялись якоря
# Снимок для истории
grace status --path . --json > docs/status/C-ADD-AUTH.json
```

---

## 4. Семантическая разметка кода (что в каждом файле)

**Главное:** маркеры — **load-bearing structure**, не комментарии. Никогда не удалять «как лишний комментарий». Они — навигационные якоря для RAG-агента и точки внимания для LLM-контекста.

### 4.1 Шапка файла (модуль)

Синтаксис комментария — по языку (`#` для Python, `//` для Dart/Go/TS/Java, `--` для SQL). Поля — **точные, канонические**, не переименовывать `PURPOSE / SCOPE / DEPENDS / LINKS / INPUTS / OUTPUTS / SIDE_EFFECTS`.

```ts
// FILE: src/auth/login.ts
// VERSION: 1.0.0
// START_MODULE_CONTRACT
//   PURPOSE: Authenticate a user by email and password and issue a session token.
//   SCOPE: Credential validation, password hashing, session token issuance, login audit log.
//   DEPENDS: [M-USER-STORE, M-HASHER, M-SESSION, M-LOGGER]
//   LINKS: [V-M-AUTH-LOGIN, fn-authenticate, fn-issueSession]
//   ROLE: RUNTIME          // RUNTIME | TEST | BARREL | CONFIG | TYPES | SCRIPT
//   MAP_MODE: EXPORTS      // EXPORTS | LOCALS | SUMMARY | NONE
// END_MODULE_CONTRACT
//
// START_MODULE_MAP
//   authenticate - validate credentials and return auth result
//   issueSession - mint a session token for an authenticated user
//   revokeSession - terminate an active session
// END_MODULE_MAP
```

**Lint-specific поля:** `ROLE` говорит CLI, что это за файл. `MAP_MODE` — как интерпретировать `MODULE_MAP`.

Рекомендуемые дефолты:

| ROLE | MAP_MODE | Когда |
|---|---|---|
| `RUNTIME` | `EXPORTS` | Обычный source-модуль |
| `TEST` | `LOCALS` | Большие тестовые файлы |
| `BARREL` | `SUMMARY` | Re-export агрегаторы |
| `CONFIG` | `NONE` | Tool/build config |
| `TYPES` | `EXPORTS` | Чисто типы/интерфейсы |
| `SCRIPT` | `LOCALS` | CLI / bootstrap / smoke |

**Граничный rule:** `.grace/graph/` и `.grace/verification/` описывают **только** публичный контракт и публичный интерфейс. Внутренние хелперы, локальные типы — остаются в file header и локальных контрактах, не в shared XML.

**Grep-stable naming rule:**
- `M-*` — exact uppercase kebab: `M-AUTH`, `M-USER-STORE`
- `V-M-*` — exact derived: `V-M-AUTH`, `V-M-USER-STORE`
- Field labels — exact: `PURPOSE`, `SCOPE`, `DEPENDS`, `LINKS`, `INPUTS`, `OUTPUTS`, `SIDE_EFFECTS`
- Block names — uppercase snake: `START_BLOCK_VALIDATE_INPUT`
- В `LINKS:` предпочитать точные anchors: `M-*`, `V-M-*`, `fn-*`, `type-*`, `class-*`, `export-*`, `const-*`

### 4.2 Контракт экспортируемой функции/компонента

```ts
// START_CONTRACT: authenticate
//   PURPOSE: Validate email+password and return an auth result or a typed error.
//   INPUTS: { email: string - normalized email; password: string - plaintext (never logged) }
//   OUTPUTS: { AuthResult - { userId, sessionId, issuedAt } }
//   SIDE_EFFECTS: [increments M-LOGGER audit counter, writes [M-AUTH][authenticate][BLOCK_VERIFY_CRED] log line]
//   LINKS: [M-USER-STORE, M-HASHER, V-M-AUTH-LOGIN]
// END_CONTRACT: authenticate
export async function authenticate(email: string, password: string): Promise<AuthResult> {
  // ...
}
```

### 4.3 Семантические блоки внутри функций

```ts
// START_BLOCK_VALIDATE_INPUT
const normalizedEmail = normalizeEmail(email);
if (!isWellFormedEmail(normalizedEmail)) {
  logger.warn('[M-AUTH][authenticate][BLOCK_VALIDATE_INPUT] malformed email', { correlationId });
  return { ok: false, reason: 'invalid_email' };
}
// END_BLOCK_VALIDATE_INPUT
```

**Правила гранулярности:**
1. **≈500 токенов на блок.** Слишком большой — теряется локальность. Слишком маленький — шум.
2. Block names — канонические uppercase snake, **уникальны** внутри файла.
3. Каждый `START_BLOCK_X` обязан иметь matching exact `END_BLOCK_X`. Orphan / crossed / malformed / mismatched = integrity error.
4. Имена описывают **WHAT**, не HOW.

### 4.4 Логирование (обязательное для критических путей)

```ts
logger.info('[M-AUTH][authenticate][BLOCK_VERIFY_CRED] credential check passed', {
  userId,
  correlationId,
  stableField: 'value',
});
```

Формат: `[ModuleName][functionName][BLOCK_NAME] message`. Это создаёт прямую ссылку из рантайм-логов обратно в блок кода.

### 4.5 CHANGE_SUMMARY

```ts
// START_CHANGE_SUMMARY
//   LAST_CHANGE: v1.2.0 - Added audit counter for failed logins; tightened input validation
// END_CHANGE_SUMMARY
```

---

## 5. Knowledge Graph: уникальные теги как семантические аккумуляторы

Это отдельный большой принцип, потому что в нём — половина навигируемости GRACE для LLM.

### 5.1 Проблема closing-tag polysemy

```xml
<!-- ПЛОХО: непонятно, какой </Module> что закрывает -->
<Module ID="M-CONFIG">...</Module>
<Module ID="M-DB">...</Module>
<Module ID="M-AUTH">...</Module>
```

LLM, видя `</Module>`, вынужден откатываться и угадывать. С ростом числа модулей — attention errors.

### 5.2 Решение: уникальное имя тега

```xml
<!-- ХОРОШО: closing tag несёт полную идентичность -->
<M-CONFIG NAME="Config" TYPE="UTILITY">...</M-CONFIG>
<M-DB NAME="Database" TYPE="DATA_LAYER">...</M-DB>
<M-AUTH NAME="Authentication" TYPE="CORE_LOGIC">...</M-AUTH>
```

`</M-CONFIG>` однозначен. Уникальные токены работают как семантические аккумуляторы: они собирают и несут смысл через контекстное окно, а закрывающий тег реактивирует все ассоциации, накопленные с момента открытия.

### 5.3 Таблица конвенций

| Entity | Анти-паттерн | Правильно |
|---|---|---|
| Module | `<Module ID="M-CONFIG">` | `<M-CONFIG NAME="Config" TYPE="UTILITY">` |
| Phase | `<Phase number="1">` | `<Phase-1 name="Foundation">` |
| Flow (data-flow) | `<Flow ID="DF-SEARCH">` | `<DF-SEARCH .../>` |
| Route | `<route api .../>` | `<route-api .../>` |
| File | `<file name="Dockerfile" .../>` | `<file-Dockerfile .../>` |
| Rule | `<rule>text</rule>` | `<rule-errors>text</rule-errors>` |

### 5.4 Что НЕ менять

- **CrossLinks** — self-closing (`<CrossLink ... />`), без вложенности, без polysemy.
- **Структурные обёртки**, появляющиеся один раз на родителя: `<annotations>`, `<interface>`, `<contract>`, `<inputs>`, `<outputs>`, `<errors>`, `<notes>`, `<purpose>`, `<path>`, `<depends>`.
- **Code-level markup** (`// START_BLOCK_...`) — уже использует уникальные имена, остаётся как есть.

### 5.5 Типы модулей (TYPE атрибут)

| TYPE | Описание |
|---|---|
| `ENTRY_POINT` | Точка входа (CLI, HTTP handler, event listener) |
| `CORE_LOGIC` | Бизнес-правила и доменная логика |
| `DATA_LAYER` | Persistence, queries, caching |
| `UI_COMPONENT` | UI-элементы |
| `UTILITY` | Общие хелперы, конфигурация, логирование |
| `INTEGRATION` | Адаптеры к внешним сервисам |

### 5.6 Аннотационные теги

| Тег | Назначение |
|---|---|
| `<fn-name>` | Публичная функция в external contract |
| `<type-Name>` | Публичный тип/интерфейс |
| `<class-Name>` | Публичный класс |
| `<export-name>` | Публичный именованный экспорт |
| `<const-NAME>` | Публичная константа |

**Не** зеркалить в `<annotations>` каждый приватный хелпер. Приватные оркестраторы, локальные utility-функции и implementation-only типы — остаются в file header и локальных контрактах.

### 5.7 Структура `.grace/graph/`

```xml
<!-- .grace/graph/index.xml -->
<GraceGraphIndex graceVersion="4.0">
  <GraphDocuments>
    <GD-MAIN>
      <Path>graph/main.xml</Path>
      <Owns>
        <M-CONFIG />
        <M-DB />
      </Owns>
    </GD-MAIN>
  </GraphDocuments>
</GraceGraphIndex>
```

```xml
<!-- .grace/graph/main.xml -->
<GraceGraphDocument graceVersion="4.0">
  <GD-MAIN>
    <M-CONFIG>
      <Summary>Application configuration and environment management</Summary>
      <Path>src/config/index.ts</Path>
      <M-DB />   <!-- link to M-DB -->
    </M-CONFIG>
    <M-DB>
      <Summary>Database connection and query layer</Summary>
      <Path>src/db/index.ts</Path>
    </M-DB>
  </GD-MAIN>
</GraceGraphDocument>
```

**Maintenance rules:**
1. Всегда актуален. Добавил модуль — добавь в граф.
2. Сомневаешься — `$grace-refresh`.
3. Инкрементируй индекс при структурных изменениях.
4. `<annotations>` матчат публичный интерфейс.
5. Verification refs валидны (V-M-*) — деривация механическая: заменить leading `M-` на `V-M-`.
6. **Нет orphans.** Удалил модуль — удалил graph entry и все ссылки.

---

## 6. Verification как архитектура

### 6.1 Три слоя доказательств

Верификация в GRACE — это **не «совпало ли значение»**, а:

1. **Детерминированные assertions** для точных outcomes
2. **Trace / log assertions** для execution trajectory
3. **Phase-level / integration checks** для merged surfaces

Для долгих автономных запусков верификация — это **autonomy gate**. Должна доказывать, что другой агент может продолжить или отладить по видимым следам, а не по скрытому reasoning.

### 6.2 Структура `.grace/verification/`

- `index.xml` — роутинг VD-* документов
- `main.xml` и др. — VD-* документы, содержащие V-M-* записи

`V-M-*` запись может содержать:
- `<Cwd>` — один contained project-relative working directory
- `<TestFiles><File>...</File></TestFiles>` — точные project-root-relative пути к тестам
- `<Command>` — module-local verification команда
- `<Scenario>` — именованное success/failure поведение
- `<Marker>` — обязательные лог-маркеры для trace assertions

**Пример V-M-* записи** (из reference-документа):

```xml
<V-M-CHATS>
  <Cwd>apps/server</Cwd>
  <TestFiles>
    <File>apps/server/src/chat/index.test.ts</File>
  </TestFiles>
  <Command>bun test src/chat/index.test.ts</Command>
  <Scenario>Generated title is assigned only when the chat is still untitled.</Scenario>
  <Scenario>Ownership failure rejects the mutation.</Scenario>
  <Marker>[ChatDomain][setGeneratedTitleIfEmpty][BLOCK_ASSIGN_GENERATED_TITLE]</Marker>
</V-M-CHATS>
```

### 6.3 Правила дизайна тестов

1. Сначала детерминированные assertions.
2. Добавляй trace/log assertions, когда простой return-value check недостаточен.
3. Держи module-local тесты близко к модулю.
4. Узкие fakes/stubs вместо гигантских opaque mocks.
5. Если баг проскочил — усиль ближайшую V-M-* запись и тесты **до** закрытия петли.

### 6.4 Уровни верификации

- **Module level** — быстрые проверки, воркер запускает один
- **Wave level** — только для merged surfaces, тронутых волной
- **Phase level** — более широкий regression + integrity

Execution packets в `grace-execute` должны **переиспользовать** эти уровни, а не выдумывать новые проверки ad hoc.

### 6.5 Autonomy gate — чек-лист перед долгим автономным запуском

1. Есть V-M-* запись для модуля
2. Минимум одна module-local команда
3. Success и failure сценарии именованы
4. Обязательные лог-маркеры / trace assertions делают divergence наблюдаемой
5. Wave-level / phase-level follow-up именован, когда module-local checks недостаточно
6. GraceChangePlan scope определяет DurableScope и ObservedWriteScope

### 6.6 Failure Packets

Когда верификация падает, захвати:
- scenario, который упал
- expected evidence
- observed evidence
- первый divergent function/block
- next suggested action

Это ускоряет `$grace-fix` и снижает потери.

---

## 7. Grep-First Navigation (как воркеры читают проект)

Предпочтительный порядок сужения scope:

1. `.grace/graph/index.xml` → routed graph documents (M-*, DF-*)
2. `.grace/verification/index.xml` → routed verification documents (V-M-*)
3. `.grace/changes/active/C-*` — in-flight specs/plans
4. Source/test files: `LINKS:`, `START_MODULE_CONTRACT`, `START_CONTRACT:`, `START_BLOCK_*`

**Общие якоря:**
- `GD-*` — graph document wrappers
- `M-*` — module IDs
- `DF-*` — data-flow IDs
- `VD-*` — verification document wrappers
- `V-M-*` — verification IDs
- `C-*` — change bundles
- `T-*` — implementation plan tasks

**Только после сужения** — читать целые файлы.

---

## 8. CLI cheatsheet (`@osovv/grace-cli`)

Установка: `bun add -g @osovv/grace-cli`. Требует `bun` на `PATH`. Скиллы вызывают установленный `grace` напрямую, не `bunx`/`npx`.

| Команда | Что делает |
|---|---|
| `grace lint --path .` | Fast integrity snapshot по semantic markup, XML, export/map drift |
| `grace lint --profile autonomous --path .` | Pre-flight для долгих автономных запусков (operational packets, verification, evidence) |
| `grace lint --path . --assertions current` | Active-baseline preflight — **только** до observed writes |
| `grace lint --path . --change C-XXX --assertions baseline [--run-commands]` | Перед имплементацией; команды запускаются только с `--run-commands` |
| `grace lint --path . --change C-XXX --assertions target --run-commands` | Пост-имплементационная проверка target assertions |
| `grace lint --path . --change C-XXX --assertions final [--run-commands]` | Apply/archive gate |
| `grace lint --path . --parallel-preflight` | Coexistence gate для parallel-safe execution |
| `grace status --path .` | Durable health, stale plans, scope conflicts, explained/unexplained drift |
| `grace status --path . --with modules` | + per-module health |
| `grace module find <query> --path .` | Поиск модулей по id/path/text/dep/verif id |
| `grace module show <id> --path .` | Shared/public контекст модуля |
| `grace module show <id> --with verification --path .` | + verification excerpt |
| `grace module health <id> --path .` | Implementation coverage, verification health, autonomy readiness, blockers, next action |
| `grace verification find <query> --path .` | Поиск V-M-* |
| `grace verification show <id> --path .` | Одна запись + linked module context |
| `grace file show <path> --path .` | File-local MODULE_CONTRACT, MODULE_MAP, CHANGE_SUMMARY |
| `grace file show <path> --contracts --blocks --path .` | + function/type contracts + semantic block navigation |

**Output modes:** `grace lint/status/module/verification/file` → `text` или `json`. `grace module find` / `grace verification find` → `table` или `json`.

**Fail-closed:** invalid options, invalid grammar, malformed active assertions/scopes, duplicate ownership, missing routed files, ambiguous targets → structured results или nonzero error envelope. JSON failures: `{"schemaVersion":"1.0.0","ok":false,"error":{...}}` на stdout. Text failures: одна actionable строка без stack trace.

---

## 9. Минимальный пример end-to-end: «C-ADD-AUTH»

### 9.1 Файл 1: `.grace/changes/active/C-ADD-AUTH/spec.xml`

```xml
<GraceChangeSpec graceVersion="4.0" status="approved">
  <C-ADD-AUTH>
    <Summary>Add password-based authentication module with session token issuance.</Summary>
    <Problem>Current API has no user authentication; all routes are anonymous.</Problem>
    <Goals>
      <Goal>Authenticate email+password against M-USER-STORE.</Goal>
      <Goal>Issue a signed session token on success.</Goal>
      <Goal>Reject and log invalid attempts without leaking which field was wrong.</Goal>
    </Goals>
    <Constraints>
      <Constraint>Preserve existing public session APIs.</Constraint>
      <Constraint>Hash with argon2id; never log plaintext password.</Constraint>
    </Constraints>
    <NonGoals>
      <NonGoal>Replace the user store.</NonGoal>
      <NonGoal>Implement OAuth / SSO.</NonGoal>
    </NonGoals>
    <AcceptanceCriteria>
      <Criterion>Protected requests reject requests with missing or invalid session tokens.</Criterion>
      <Criterion>Successful auth issues a session token valid for 24h.</Criterion>
    </AcceptanceCriteria>
    <AffectedAreas>
      <M-AUTH />
      <M-SESSION />
    </AffectedAreas>
    <VerificationIntent>
      <ExpectedCommand>bun test src/auth</ExpectedCommand>
      <ExpectedEvidence>V-M-AUTH-LOGIN passes; required log marker [M-AUTH][authenticate][BLOCK_VERIFY_CRED] emitted on success path.</ExpectedEvidence>
    </VerificationIntent>
    <Assumptions>
      <Assumption>M-USER-STORE exists and exposes findByEmail.</Assumption>
    </Assumptions>
  </C-ADD-AUTH>
</GraceChangeSpec>
```

### 9.2 Файл 2: `.grace/changes/active/C-ADD-AUTH/plan.xml`

```xml
<GraceChangePlan graceVersion="4.0" status="approved">
  <C-ADD-AUTH>
    <IntentSummary>Implement M-AUTH with password auth, session issuance, and full verification coverage.</IntentSummary>
    <BaselineAssertions>
      <MustExist>
        <Value>M-USER-STORE</Value>
      </MustExist>
      <MustExist>
        <Value>M-HASHER</Value>
      </MustExist>
    </BaselineAssertions>
    <TargetAssertions>
      <MustVerify>
        <Module>M-AUTH</Module>
      </MustVerify>
      <MustVerify>
        <Module>M-SESSION</Module>
      </MustVerify>
      <MustPassCommand>
        <Command>bun test src/auth</Command>
      </MustPassCommand>
    </TargetAssertions>
    <DurableScope>
      <GraphAnchors>
        <M-AUTH />
        <M-SESSION />
      </GraphAnchors>
      <VerificationAnchors>
        <V-M-AUTH-LOGIN />
        <V-M-SESSION-ISSUE />
      </VerificationAnchors>
      <ContextArtifact>requirements.xml</ContextArtifact>
    </DurableScope>
    <ObservedWriteScope>
      <File>src/auth/login.ts</File>
      <File>src/auth/login.test.ts</File>
      <File>src/session/issue.ts</File>
      <File>src/session/issue.test.ts</File>
    </ObservedWriteScope>
    <ImplementationPlan>
      <T-001>
        <Title>Implement M-AUTH.authenticate with input validation, password verify, audit log</Title>
        <DependsOn></DependsOn>
        <AcceptanceCriteria>
          <Criterion>Returns AuthResult on success, typed error on failure.</Criterion>
          <Criterion>Emits required log marker on success path.</Criterion>
          <Criterion>Never logs plaintext password.</Criterion>
        </AcceptanceCriteria>
        <Verification>
          <Command>bun test src/auth/login.test.ts</Command>
        </Verification>
      </T-001>
      <T-002>
        <Title>Implement M-SESSION.issueSession minting 24h signed token</Title>
        <DependsOn>T-001</DependsOn>
        <AcceptanceCriteria>
          <Criterion>Token includes userId, issuedAt, expiresAt.</Criterion>
        </AcceptanceCriteria>
        <Verification>
          <Command>bun test src/session/issue.test.ts</Command>
        </Verification>
      </T-002>
    </ImplementationPlan>
  </C-ADD-AUTH>
</GraceChangePlan>
```

### 9.3 Файл 3: `.grace/graph/main.xml` (добавляем M-AUTH, M-SESSION)

```xml
<GraceGraphDocument graceVersion="4.0">
  <GD-MAIN>
    <M-USER-STORE>
      <Summary>User persistence and lookup</Summary>
      <Path>src/user-store/index.ts</Path>
    </M-USER-STORE>
    <M-HASHER>
      <Summary>Password hashing (argon2id)</Summary>
      <Path>src/hasher/index.ts</Path>
    </M-HASHER>
    <M-AUTH>
      <Summary>Password-based authentication with audit logging</Summary>
      <Path>src/auth/login.ts</Path>
      <M-USER-STORE />
      <M-HASHER />
      <M-SESSION />
    </M-AUTH>
    <M-SESSION>
      <Summary>Session token issuance and verification</Summary>
      <Path>src/session/issue.ts</Path>
      <M-AUTH />
    </M-SESSION>
  </GD-MAIN>
</GraceGraphDocument>
```

### 9.4 Файл 4: `.grace/verification/main.xml` (добавляем V-M-AUTH-LOGIN, V-M-SESSION-ISSUE)

```xml
<GraceVerificationDocument graceVersion="4.0">
  <VD-MAIN>
    <V-M-AUTH-LOGIN>
      <Cwd>.</Cwd>
      <TestFiles>
        <File>src/auth/login.test.ts</File>
      </TestFiles>
      <Command>bun test src/auth/login.test.ts</Command>
      <Scenario>Valid credentials return AuthResult with userId and sessionId.</Scenario>
      <Scenario>Invalid email format returns typed error without DB call.</Scenario>
      <Scenario>Wrong password returns generic auth_failed; does not leak which field was wrong.</Scenario>
      <Scenario>Success path emits [M-AUTH][authenticate][BLOCK_VERIFY_CRED] log marker.</Scenario>
    </V-M-AUTH-LOGIN>
    <V-M-SESSION-ISSUE>
      <Cwd>.</Cwd>
      <TestFiles>
        <File>src/session/issue.test.ts</File>
      </TestFiles>
      <Command>bun test src/session/issue.test.ts</Command>
      <Scenario>Issued token contains userId, issuedAt, expiresAt = issuedAt + 24h.</Scenario>
      <Scenario>Token is signed; tampering invalidates signature.</Scenario>
    </V-M-SESSION-ISSUE>
  </VD-MAIN>
</GraceVerificationDocument>
```

### 9.5 Файл 5: `src/auth/login.ts` — размеченный код

```ts
// FILE: src/auth/login.ts
// VERSION: 1.0.0
// START_MODULE_CONTRACT
//   PURPOSE: Authenticate a user by email and password, emit audit log, and return a typed result.
//   SCOPE: Credential validation, password hash verification, audit logging. No token issuance here.
//   DEPENDS: [M-USER-STORE, M-HASHER, M-LOGGER]
//   LINKS: [M-SESSION, V-M-AUTH-LOGIN, fn-authenticate]
//   ROLE: RUNTIME
//   MAP_MODE: EXPORTS
// END_MODULE_CONTRACT
//
// START_MODULE_MAP
//   authenticate - validate credentials and return auth result or typed error
// END_MODULE_MAP
//
// START_CHANGE_SUMMARY
//   LAST_CHANGE: v1.0.0 - Initial implementation under C-ADD-AUTH
// END_CHANGE_SUMMARY

import { findByEmail, type UserRecord } from '../user-store';
import { verifyPassword } from '../hasher';
import { logger } from '../logger';
import type { CorrelationId } from '../correlation';

// START_CONTRACT: authenticate
//   PURPOSE: Validate email+password against M-USER-STORE; return AuthResult or typed error.
//   INPUTS: { email: string - normalized email; password: string - plaintext, never logged; correlationId: CorrelationId - request trace id }
//   OUTPUTS: { AuthResult - { ok: true, userId: string } | { ok: false, reason: 'invalid_input' | 'auth_failed' } }
//   SIDE_EFFECTS: [increments M-LOGGER audit counter; writes [M-AUTH][authenticate][BLOCK_*] log lines]
//   LINKS: [M-USER-STORE, M-HASHER, M-SESSION, V-M-AUTH-LOGIN]
// END_CONTRACT: authenticate
export async function authenticate(
  email: string,
  password: string,
  correlationId: CorrelationId,
): Promise<AuthResult> {
  // START_BLOCK_VALIDATE_INPUT
  const normalized = email.trim().toLowerCase();
  if (!isWellFormedEmail(normalized) || password.length === 0) {
    logger.warn('[M-AUTH][authenticate][BLOCK_VALIDATE_INPUT] rejected malformed input', {
      correlationId,
      reason: 'invalid_input',
    });
    return { ok: false, reason: 'invalid_input' };
  }
  // END_BLOCK_VALIDATE_INPUT

  // START_BLOCK_LOOKUP_USER
  const user: UserRecord | null = await findByEmail(normalized);
  if (!user) {
    // Constant-time-ish path: still hash to avoid timing oracle
    await verifyPassword(password, DUMMY_HASH);
    logger.info('[M-AUTH][authenticate][BLOCK_LOOKUP_USER] no such user', {
      correlationId,
      outcome: 'auth_failed',
    });
    return { ok: false, reason: 'auth_failed' };
  }
  // END_BLOCK_LOOKUP_USER

  // START_BLOCK_VERIFY_CRED
  const ok = await verifyPassword(password, user.passwordHash);
  if (!ok) {
    logger.info('[M-AUTH][authenticate][BLOCK_VERIFY_CRED] wrong password', {
      correlationId,
      userId: user.id,
      outcome: 'auth_failed',
    });
    return { ok: false, reason: 'auth_failed' };
  }
  logger.info('[M-AUTH][authenticate][BLOCK_VERIFY_CRED] credential check passed', {
    correlationId,
    userId: user.id,
  });
  // END_BLOCK_VERIFY_CRED

  return { ok: true, userId: user.id };
}

// START_BLOCK_HELPERS
function isWellFormedEmail(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}
const DUMMY_HASH = '$argon2id$v=19$m=65536,t=3,p=4$ZHVtbXk$ZHVtbXk'; // generated once, never corresponds to a real password
// END_BLOCK_HELPERS

export type AuthResult =
  | { ok: true; userId: string }
  | { ok: false; reason: 'invalid_input' | 'auth_failed' };
```

### 9.6 Файл 6: `src/auth/login.test.ts` — тест, который ссылается на V-M-*

```ts
// FILE: src/auth/login.test.ts
// VERSION: 1.0.0
// START_MODULE_CONTRACT
//   PURPOSE: Verify V-M-AUTH-LOGIN scenarios for M-AUTH.authenticate.
//   SCOPE: Unit tests with narrow fakes for M-USER-STORE, M-HASHER, M-LOGGER.
//   DEPENDS: [M-AUTH, M-USER-STORE, M-HASHER, M-LOGGER]
//   LINKS: [V-M-AUTH-LOGIN]
//   ROLE: TEST
//   MAP_MODE: LOCALS
// END_MODULE_CONTRACT
//
// START_MODULE_MAP
//   setupFakeUserStore - in-memory M-USER-STORE fake
//   setupFakeHasher - deterministic M-HASHER fake
//   captureLogs - test logger sink that records markers
// END_MODULE_MAP

import { describe, test, expect, beforeEach } from 'bun:test';
import { authenticate } from './login';
import { setupFakeUserStore, setupFakeHasher } from './fakes';
import { captureLogs, hasLogMarker } from '../test-utils/log-capture';

describe('M-AUTH.authenticate (V-M-AUTH-LOGIN)', () => {
  let logs: ReturnType<typeof captureLogs>;
  beforeEach(() => {
    setupFakeUserStore([{ id: 'u-1', email: 'a@b.c', passwordHash: 'HASH_a@b.c' }]);
    setupFakeHasher({ 'a@b.c': true });
    logs = captureLogs();
  });

  test('valid credentials return ok with userId and emit success marker', async () => {
    const r = await authenticate('A@B.C', 'pw', 'corr-1');
    expect(r).toEqual({ ok: true, userId: 'u-1' });
    expect(hasLogMarker(logs, 'info', '[M-AUTH][authenticate][BLOCK_VERIFY_CRED]')).toBe(true);
  });

  test('malformed email returns invalid_input without DB call', async () => {
    const r = await authenticate('not-an-email', 'pw', 'corr-2');
    expect(r).toEqual({ ok: false, reason: 'invalid_input' });
  });

  test('wrong password returns generic auth_failed and does not leak field', async () => {
    setupFakeHasher({ 'a@b.c': false });
    const r = await authenticate('a@b.c', 'wrong', 'corr-3');
    expect(r).toEqual({ ok: false, reason: 'auth_failed' });
  });

  test('plaintext password is never logged', async () => {
    await authenticate('a@b.c', 'super-secret-pw', 'corr-4');
    expect(logs.allText).not.toContain('super-secret-pw');
  });
});
```

---

## 10. Contract-driven dev: сводка правил

1. **Читать перед правкой** — всегда `MODULE_CONTRACT` перед редактированием файла.
2. **Обновить MODULE_MAP** — если поменялись public/local symbols, релевантные для lint mode.
3. **Обновить `.grace/graph`** — если добавил/удалил модули или зависимости, обнови соответствующий GD-* документ.
4. **Обновить `.grace/verification`** — если поменялись тесты, обязательные маркеры или verification commands, обнови VD-* документ.
5. **Трекать изменения** — после фикса багов добавляй `CHANGE_SUMMARY`.
6. **Никогда не удалять разметку** — semantic markup anchors = load-bearing structure.
7. **Предлагай, не отклоняйся** — если контракт неверен, предложи изменение пользователю. Не молча реализуй что-то другое.
8. **Якори intent** — предпочитай meaningful names и конкретный PURPOSE text, а не generic placeholders.

---

## 11. Развитие, поддержка, отладка

### `$grace-status` — снимок здоровья

Сообщает (через `grace status --path . --json`):
- Project kind: GRACE 4, legacy GRACE 3 migration candidate, или missing GRACE; context completeness
- Graph/verification projection integrity, routed coverage, module counts
- Active/archive bundle statuses и derived states
- `needs-plan`, `needs-plan-approval`, `stale-plan`, `integrity-issues`, `ready-to-execute` (mutually exclusive от stale/integrity)
- Route-aware explained/unexplained drift, scope coexistence warnings, parallel blockers
- Module-health load failure как integrity/degraded, не crash
- **Следующее безопасное действие**: lint / migrate / specify / plan / execute

### `$grace-refresh` — поиск дрейфа

Не молча мутирует state. Workflow:
1. `grace lint` + `grace status`
2. `.grace/graph/index.xml` и routed — stale / missing / orphaned `M-*` и `DF-*`
3. `.grace/verification/index.xml` и routed — missing deterministic `V-M-*`, stale commands, missing markers
4. Сравнить file-local `LINKS:`, контракты, тесты, лог-маркеры с durable anchors
5. Рeport drift как findings + proposed reconciliation scope
6. Если изменения нужны — направлять через `$grace-spec` / `$grace-plan`, не direct mutation

### `$grace-fix` — отладка

Investigation path:
1. Начать от failure (вставленная ошибка, failing command, user report)
2. Загрузить релевантные `.grace/graph` и `.grace/verification`
3. Проверить активные `.grace/changes` на overlap / stale work
4. Прочитать file-local контракты и семантические блоки до правки
5. Identify root cause → present findings → smallest safe fix
6. Verification: specific `V-M-*` commands или ближайшие deterministic tests. Если expectations stale — update или propose changes через lifecycle.

### `$grace-refactor` — переименования / перемещения

Scope: rename, move, split, merge, extraction, boundary cleanup. **Не** использовать для greenfield feature work (→ spec/plan/execute).

Must_do:
- Resolve affected `M-*`, `DF-*`, `V-M-*` через `.grace/graph/index.xml` и `.grace/verification/index.xml`
- Проверить active `.grace/changes` на scope overlap
- Сохранить или обновить file-local `LINKS:`, контракты, семантические блоки
- Обновить durable graph/verification только когда refactor намеренно меняет boundaries/paths/evidence
- Targeted tests + `grace lint`

### `$grace-reviewer` — ревью

Проверяет: semantic integrity, graph consistency, verification quality.

### `$grace-ask` — вопросы по проекту

Context order: `.grace/context/*.xml` → `.grace/graph/index.xml` → routed graph documents → `.grace/verification/index.xml` → routed verification → active changes → file-local markup.

Answer rules: cite artifact/anchor, distinguish durable state от active change intent, не выдумывай missing facts, GRACE 3 legacy → мигрировать, не «правда».

---

## 12. Anti-patterns (как НЕ надо)

1. **Перескакивать через уровни** — писать код без утверждённого spec/plan. Прямой фикс — только для мелких явных багов, не для фич.
2. **Молча перезаписывать `.grace/`** — при наличии существующих артефактов **стоп и спросить**.
3. **Удалять semantic markup** как «лишние комментарии». Это **load-bearing structure**.
4. **Зеркалить private helpers** в shared `.grace/graph/annotations`. Приватное остаётся в file header и локальных контрактах.
5. **Использовать generic Module tag** (`<Module ID="M-X">`) вместо unique tag (`<M-X>`) — это closing-tag polysemy.
6. **Гонять весь-репо verification после каждого шага.** Использовать module / wave / phase уровни.
7. **Менять approved plan in place** — создавать replacement C-* bundle, старый → superseded.
8. **Пускать multiagent на tightly coupled slice** — это уже не multiagent wave.
9. **Прятать reasoning в чат вместо пакетов** — пересматривать пакеты между волнами.
10. **Дрейфовать от контракта** — если контракт неверен, предложи изменение, не дрейфуй.
11. **Складывать `grace lint`/`grace status` внутрь `MustPassCommand`** — это запрещено. `MustPassCommand` = leaf project evidence.
12. **Контракты с generic placeholders** (`<Module>` без NAME, бессмысленные ID) — purpose теряется.

---

## 13. Что это значит для проектирования ваших скиллов

Ниже — сжатая выжимка принципов, на которые стоит опираться, чтобы спроектировать **свой** процесс на базе скиллов (не копируя XML-формат GRACE). Структура важнее формата.

| Принцип GRACE | Что взять за основу в своём дизайне |
|---|---|
| **Process-first, not prompt-first** | Цель — сделать хорошее исполнение *скучным*: контракт → план → пакет → выполнение → evidence |
| **PCAM (Purpose / Constraints / Autonomy / Metrics)** | Для каждой задачи явно определять: что, что нельзя, свобода воркера, метрики готовности |
| **Контракт — источник истины** | Перед кодом — `MODULE_CONTRACT` с PURPOSE / SCOPE / INPUTS / OUTPUTS / SIDE_EFFECTS / LINKS. Контракт описывает WHAT, а не HOW |
| **Уникальные теги как семантические аккумуляторы** | Дайте своим YAML/JSON-артефактам уникальные ключи (`M-AUTH`, `V-M-AUTH`, `C-ADD-AUTH`, `T-001`) — это резко улучшает навигацию для LLM |
| **≈500 токенов на семантический блок** | Делите длинные функции на блоки с именованными якорями. Имена — WHAT, не HOW |
| **Grep-first navigation** | Определите «где искать что» как первый шаг для воркера. Порядок от coarse (graph) к fine (block) |
| **Верификация — архитектура, не уборка** | Доказательства корректности: deterministic assertions, trace/log assertions, integration checks. Уровни: module / wave / phase |
| **Стабильные лог-маркеры** | Формат `[ModuleName][functionName][BLOCK_NAME]` — трассировка от рантайма обратно в код |
| **Top-down synthesis** | Конвейер: Requirements → Technology → Plan → Verification → Contracts → Code. Не перескакивать |
| **Governed autonomy через scope** | Разделяйте `DurableScope` (что в долговременной модели) и `ObservedWriteScope` (какие файлы трогаем). Воркер свободен в HOW, ограничен в WHAT |
| **Approved plan — immutable evidence** | Чтобы изменить утверждённый план, создаётся replacement bundle, старый → superseded. Не правьте in place |
| **Lifecycle gates** | `current` (preflight) → `baseline` (перед записью) → `target` (после) → `final` (apply gate). Этот цикл заставляет задуматься перед каждым переходом |
| **Drift detection** | Отдельный ритуал: сравнить долговременную модель (graph/verification) с реальным кодом; не молча мутировать, а предлагать reconciliation change |
| **Module taxonomy** | Классифицируйте модули: ENTRY_POINT / CORE_LOGIC / DATA_LAYER / UI_COMPONENT / UTILITY / INTEGRATION. Это помогает воркеру понять, что от него ждут |
| **Reliability-first stack** | В Technology-артефакте явно назвать предпочтительные библиотеки, тестовые инструменты, observability. Пометить discouraged-варианты |
| **Failure packets** | Когда что-то падает — захватывать: сценарий / expected / observed / первый divergent function/block / next action |

### Минимальный набор скиллов, эквивалентный по духу GRACE

Для своей системы (не копируя XML) хватит ~7-8 ритуалов:

1. **`init`** — bootstrap project model (context, technology, stack, naming rules)
2. **`spec`** — interview, записать change intent: summary, goals, constraints, non-goals, acceptance criteria, affected areas, verification intent
3. **`plan`** — разложить spec на tasks с deps, scopes, verification gates
4. **`execute`** — последовательно: пакет → код с контрактами → module-level verification → checkpoint report → коммит
5. **`multiagent-execute`** — то же волнами с профилями safe/balanced/fast
6. **`verification`** — построить/обновить V-M-* записи: команды, сценарии, маркеры
7. **`reviewer`** — проверить integrity, graph consistency, verification quality
8. **`status` / `refresh` / `fix`** — снимок здоровья, поиск дрейфа, отладка

**Опорные артефакты (заменяют GRACE XML):**
- `PROJECT.md` (аналог requirements.xml) — цели, users, constraints
- `STACK.md` (аналог technology.xml) — предпочтительные библиотеки, инструменты, observability
- `GRAPH.yaml` или `GRAPH.md` (аналог knowledge-graph.xml) — модули, типы, зависимости
- `VERIFICATION.yaml` (аналог verification-plan.xml) — V-M-* записи
- `CHANGES/` (аналог changes/active/C-*) — spec.md + plan.md per change

**Опорные соглашения в коде (заменяют GRACE markup):**
- `// contract: <NAME> { purpose, scope, depends, links }` или `/// <summary>` doc-comment
- `# region: <BLOCK_NAME>` ... `# endregion: <BLOCK_NAME>` (или эквивалент для вашего языка)
- Стабильные лог-маркеры: `[ModuleName][functionName][blockName]`

Формат вторичен. Главное — **разделение на long-lived durable model и ephemeral execution state**, и **явные гейты** между ними.

---

## Приложение A. Где что лежит в репо

- **Канонические скиллы**: `skills/grace/*` (например, `skills/grace/grace-explainer/SKILL.md`)
- **Packaged mirror** для Claude marketplace: `plugins/grace/skills/grace/*`
- **Marketplace metadata**: `.claude-plugin/marketplace.json`
- **Plugin manifest**: `plugins/grace/.claude-plugin/plugin.json`
- **CLI исходники**: `src/grace.ts` (entrypoint), `src/grace4/*` (GRACE 4 model: detection, XML parsing, grammar, projections, assertions, scopes), `src/lint/*`, `src/query/*`
- **Init-шаблоны**: `plugins/grace/skills/grace/grace-init/assets/.grace/{context,graph,verification}/*.template` + `assets/AGENTS.md.template`
- **Spec / plan шаблоны**: `plugins/grace/skills/grace/grace-spec/references/{change-spec-template.xml, design-context-template.xml}`, `plugins/grace/skills/grace/grace-plan/references/change-plan-template.xml`
- **Reference-документы** (объясняют принципы): `plugins/grace/skills/grace/grace-explainer/references/{semantic-markup, contract-driven-dev, knowledge-graph, verification-driven-dev, unique-tag-convention}.md`

## Приложение B. Quick reference: тэги и ID

| Тэг / ID | Где | Назначение |
|---|---|---|
| `M-*` | `.grace/graph/*.xml` | Module ID |
| `DF-*` | `.grace/graph/*.xml` | Data-flow ID |
| `GD-*` | `.grace/graph/*.xml` | Graph document wrapper |
| `V-M-*` | `.grace/verification/*.xml` | Verification entry для модуля |
| `VD-*` | `.grace/verification/*.xml` | Verification document wrapper |
| `C-*` | `.grace/changes/{active,archive}/` | Change bundle (spec + plan) |
| `T-*` | `plan.xml` ImplementationPlan | Implementation plan task |
| `CrossLink` | `.grace/graph/*.xml` | Edge между модулями (self-closing) |
| `fn-*`, `type-*`, `class-*`, `export-*`, `const-*` | annotations в `<M-*>` | Аннотации публичного интерфейса |
| `START_MODULE_CONTRACT` | file header | Контракт модуля |
| `START_MODULE_MAP` | file header | Карта экспортов/locals |
| `START_CONTRACT: <fn>` | перед функцией | Контракт функции |
| `START_BLOCK_*` / `END_BLOCK_*` | внутри функции | Семантический блок (≈500 токенов) |
| `START_CHANGE_SUMMARY` | file header | История изменений |

---

*Конец playbook. Скиллы и артефакты в этом гайде — выжимка из публичных источников `osovv/grace-marketplace` (MIT). Цитаты из `SKILL.md` и reference-документов — с сохранением ключевых формулировок.*
