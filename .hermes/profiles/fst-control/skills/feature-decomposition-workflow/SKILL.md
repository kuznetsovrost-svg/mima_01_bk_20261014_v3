---
name: feature-decomposition-workflow
description: "Build the SKELETON first when user proposes a non-trivial feature (e.g. 'add 16 new sub-items to section 6'). Ask 5-7 questions in Phase 0 batch. Then iterate sub-item-by-sub-item: live-probe MCP, write 4-section docstring, register in INDICATORS list, update spec table, test. After all sub-items: wire into run_all.py + build_html_report.py + report.css. Version bump (major for new sections, minor for new indicators). Use two-registry pattern (internal taxonomy + MCP allowed_values). State lifecycle: model levels (0=initial, 1=intermediate, 2=final). describe_entity(show_allowed_values=['__all__']) for enum discovery. Re-scope immediately on user correction. Use STEP-BY-STEP MODELING when user provides cases one-by-one ('Шаг 1: ...'). Each step adds minimal logic; verify previous steps don't regress."
version: 1.3.0
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
changelog:
  - "1.3.0 (2026-09-02): Lessons from sub-item 6.3 (Прогнозы по ресурсам) — second iterative indicator. Added: (1) Q&A BATCH GRID — when user signals an algorithm-heavy sub-item, prepare 5-8 numbered Q's in ONE turn (not drip-feed): data source, view/filter, thresholds, output format, edge cases; user answers in bulk; (2) MULTIPLE-VARIANT FORMAT — when user gives format alternatives like '{Да/Нет/Вопросы} {NN часов/-}', emit ALL variants in the spec; the user's final form often combines them ('Вопросы, N ч'); (3) COMMA-AS-SEPARATOR — for Russian number output, comma between word and number (not space, not dash); (4) ABSENCE-FORCING CHECKS — for Q5 'no PM at all': emit a per-month line in inner table EVEN IF PM-not-assigned is the only signal; the absence itself is a problem worth reporting monthly; (5) FALLBACK CHAIN FOR DATES — when entity has no StartPlan/FinishPlan, fall back to plan_dates.min/forecast_dates.max; only then to plan_dates.max; documented as a 3-level priority; (6) NESTED APPROVAL STEP — sub-item can be the AUTHORITY for the parent (e.g. forecast_hours > 0 + pm forecast_hours > 0 = OK; not partial = partial); encode as boolean composition, not separate checks; (7) MERGED-CELLS LOGIC — when multiple pathologies hit the same month (no forecast AND no PM forecast), emit ONE row with comma-separated remarks and ESCALATE severity (red beats yellow), not duplicate rows; (8) PROTOTYPE FIRST — for complex aggregations (months, sums, period lists), write the algorithm in a 5-line throwaway script with raw MCP data BEFORE putting it inside the indicator function — easier to iterate than embedded inside an IndicatorResult construction."
  - "1.2.0 (2026-09-02): Lessons from sub-item 6.2 steps 1-6 (iterative modeling of one indicator). Added: (1) STEP-BY-STEP MODELING pattern — when user provides cases one-by-one ('Шаг 1: ...'), DO NOT build the full heuristic at once; wait for each case and verify the previous one still passes; (2) SUPERPOTITION — multiple pathologies co-exist (e.g. some KTs created + some missing, some overdue + some unconfirmed); emit ALL matching issues in one pass with severity priority; (3) STRICT NAMESPACE RULE — 'Не выдумывать!' = if KT is not created, never write 'просрочена'; if not executed, never write 'не подтверждена'; (4) USER STEPPING PROTOCOL — user gives шаг N → build minimal logic for шаг N → verify no regression on шаги 1..N-1 → wait for шаг N+1; (5) SCRIPT-LEVEL EVIDENCE — when user provides a fact ('in 504-595 KT 104-708 has status Согласовано'), immediately write it as a live-probe test before building the general rule; (6) ALGORITHM-FIRST RULE — when debugging a wrong verdict, ask 'what does the user's algorithm say' BEFORE proposing a new approach; (7) AUTHORITATIVE STATE SOURCE — discover allowed_values on the SPECIFIC entityName (Point), not on a parent/derived entity (PointTemplate), or you get foreign entities' states mixed in. The 4-state point lifecycle (В работе → Выполнена → Подтверждена + Отменено) is the only correct one."
  - "1.1.0 (2026-09-02): Lessons from second sub-item (6.2 «Актуальность состояния ЖЦ»). Added: (1) question batching discipline — ask 5-7 questions in one shot when user signals iterative work, then iterate as answers come in; (2) two-registry pattern — when you need a registry that's both your domain taxonomy AND something MCP has as allowed_values, keep them separate and write is_X() helpers to bridge; (3) state lifecycle model — when implementing verdicts over state machines, model levels (0=initial, 1=intermediate, 2=final) and add get_level() helper; (4) describe_entity has show_allowed_values parameter that returns the actual values array; (5) user correction re-scope — when user says 'stop, you confused X with Y', drop everything, acknowledge, re-anchor to the right concept; (6) semantic wording — 'выполнена' (FactDate present) vs 'закрыта' (state-confirmed) is a meaningful distinction in user domain language, get it right in user-facing messages."
  - "1.0.0 (2026-09-02): Initial release. Pattern extracted from adding «Показатели проекта» (16 indicators) to `fst-project-health`."
metadata:
  hermes:
    tags: [workflow, feature-development, decomposition, indicators, docstring-driven, live-probe, batching, state-machine, two-registry, step-by-step-modeling, qa-batch-grid]
    related_skills: [hermes-agent, test-driven-development, plan, simplify-code]
---

# Feature Decomposition Workflow

## Overview

When the user proposes a **non-trivial feature** with multiple sub-items (e.g. "add 16 indicators", "add 3 new sections", "redesign the output"), don't ask for ALL details upfront. Build the skeleton first, then iterate.

## When to Use

Trigger phrases:
- «добавим N новых [пунктов / секций / фич]»
- «новый раздел отчёта»
- «расширим скилл»
- «новая версия major»
- «пошагово добавим»

**NOT for:**
- Trivial single-line changes (just do them)
- Completely new skills (use `hermes-agent` + `skill-design-spec` workflow)
- Bug fixes (use `systematic-debugging`)

---

## Pattern: Skeleton-First, Then Iterate

### Phase 0: Discovery (BATCH questions)

**Critical: ask clarifying questions in BATCHES of 5-7 at a time.** When the user signals iterative work («пошагово», «один за другим», «шаг за шагом»), they mean BOTH directions: they iterate sub-items AND you iterate questions. Don't drip-feed one question at a time.

Categories of questions to ask in Phase 0:
- **Architecture** — where in the structure does it go? renumber downstream sections?
- **Output format** — table / list / cards? column widths? expand/collapse behavior?
- **Verdict model** — per-item verdict or only section-level? threshold sources?
- **Data sources** — known up-front, or per-sub-item?
- **Naming** — display name conventions, prefix format
- **Edge cases** — what counts as "missing data"? how to handle errors?

For each sub-item later, you'll still ask 2-3 specific questions — but those are scoped, not architectural. **For algorithm-heavy sub-items, see `references/q-and-a-batch-grid-pattern.md` — a numbered Q&A grid beats drip-feeding.**

### Phase 1: Skeleton (always do this FIRST)

1. **Spec file** — `references/<feature>-spec.md` with:
   - Overview / structure of sub-items
   - Empty table with placeholders (`_ждём определения_`)
   - "Формат подпункта" template (e.g. Назначение / Получение / Интерпретация / Вывод)
   - "Прогресс разработки" section with todo list

2. **Module stub** — `scripts/<feature>.py` with:
   - `IndicatorResult` dataclass (number, name, result, detail, verdict, table, table_title)
   - `SectionVerdict` (verdict + counts dict)
   - `INDICATORS: List[Any] = []` (empty, will be filled)
   - Cache helpers if needed (`fetch_with_cache` from MCP, TTL configurable)
   - `run_all_<feature>(project, sid)` aggregator
   - `compute_section_verdict(results)` aggregation logic

3. **Thresholds module** — `scripts/<feature>_thresholds.py` with:
   - `INDICATOR_THRESHOLDS: Dict[str, Dict[str, Any]] = {}` (empty)
   - `interpret_indicator(key, result, detail)` function
   - Priority order: critical → substantial → informational → normal

4. **Tests still pass** — `cd tests && python3 run_all_tests.py`

### Phase 2: Iterate sub-item-by-sub-item

For EACH sub-item from the user:

1. **Receive** the sub-item sketch (4 sections: Назначение / Получение / Интерпретация / Вывод)
2. **Live-probe MCP** (if data source is an MCP view) — find the right view/field
3. **Implement** the check function with 4-section docstring
4. **Register** in `INDICATORS` list
5. **Update spec** — replace `_ждём_` row in the table with the actual data
6. **Test** — `python3 run_all_tests.py`

### Phase 3: Wire-up

After ALL sub-items are done:

1. **run_all.py** — add `build_section_<feature>(project)` function, call from `run()`
2. **build_html_report.py** — add render logic for the new section
3. **report.css** (templates) — add styles for new classes
4. **Tests** — add tests for new render path AND for new section being in the output
5. **Version bump**:
   - Major (X.Y.Z → (X+1).0.0) if new section / new report shape
   - Minor (X.Y.Z → X.(Y+1).0) if only new indicators
   - Patch (X.Y.Z → X.Y.(Z+1)) if only bug fixes
6. **Renumber** — if inserting a new section in the middle, all subsequent section numbers shift

### Phase 4: Archive

1. `tar czf <skill>.tar.gz <skill>/` (excluding `__pycache__`, `*.pyc`)
2. Verify portability: `cp -r <skill> /tmp/test-portability/ && cd /tmp/test-portability/<skill>/tests && python3 run_all_tests.py`
3. Send archive as Telegram file

---

## Pitfall: Don't Over-Engineer Phase 1

The skeleton must be **functional but minimal**:
- ❌ Don't implement all 16 indicators at once
- ❌ Don't write tests for unimplemented indicators
- ❌ Don't add CLI flags for partial features
- ✅ DO make the dataclass + aggregator + 1 working example
- ✅ DO get the empty registration list working
- ✅ DO update the spec table incrementally

## Pitfall: Live-Probe BEFORE Writing Code

When the sub-item depends on MCP data:
1. **First**: probe the view, confirm field names exist, check sample values
2. **Then**: write the check function with confidence
3. **Not**: write the function based on documentation, then debug when it 500s

## Pitfall: Cache Multipliers

If 5 indicators all call `fetch_with_cache(sid, ..., view_name="X", filters={...})`:
- They share the SAME cache key → ONE MCP call → 4 hits from cache
- This is fine for correctness
- But it can mask a code smell: are 5 indicators really needing the SAME data?

**Fix:** if 3+ indicators use the same view, consider factoring out a `preload_<view>(sid, project)` that fetches once and passes the rows to each indicator.

## Pitfall: 4-Section Docstring is a Contract

The 4-section docstring (`Назначение / Получение / Интерпретация / Вывод`) is not just documentation — it's a **structured handoff** to the spec file and to the next developer. Keep them in sync:

- Indicator 6.X's docstring → section 3 row of `references/<feature>-spec.md`
- When you change thresholds → update BOTH `indicator_thresholds.py` AND the docstring

## Pitfall: Question Drip-Feeding

When the user signals iterative work («пошагово», «шаг за шагом»), they do NOT mean "ask me one question at a time and wait". They mean:
- They will provide sub-item details one at a time
- They expect YOU to ask any upfront clarifying questions in BATCH (5-7 at once)
- Then iterate sub-item-by-sub-item with focused micro-questions

**Anti-pattern:** Ask Q1 → wait → Q2 → wait → ... wastes turns and annoys the user.
**Right pattern:** Ask Q1+Q2+Q3+Q4+Q5 in one message → user answers several → iterate.

## Pitfall: Two Registries, Two Purposes

When you have BOTH:
- An internal taxonomy (your domain rules)
- An external registry (MCP allowed_values)

Don't try to merge them. Keep them as TWO separate dicts/constants:

```python
# Internal — your domain logic
MANDATORY_KT_BY_STAGE = {"Пресейл": [...], "Инициирование": [...]}

# External — from MCP (via describe_entity + show_allowed_values)
POINT_STATES_REGISTRY = {40024: "Пресейл", 40067: "В работе", ...}

# Bridge — is_X() helpers that normalize naming variants
def is_point_confirmed(state: str) -> bool:
    return state.lower() in ("подтверждено", "согласован", "согласовано", "выполнено")
```

Bridge functions handle: variant spellings (ё/е), synonyms (Согласован/Подтверждено), case-insensitive matching.

## Pitfall: State Lifecycle Model

When verdicts depend on a state machine (KT lifecycle, document approval, workflow step), model the states explicitly with **levels**:

```python
LEVEL_INITIAL = 0       # not done (no FactDate)
LEVEL_INTERMEDIATE = 1 # done (FactDate present), not confirmed
LEVEL_FINAL = 2        # confirmed by approver

def get_level(state: str) -> int:
    if is_final(state): return 2
    if is_intermediate(state): return 1
    if is_initial(state): return 0
    return -1
```

Then verdict rules can be: "if level < N for required KT, escalate".

This generalizes: "уровень состояния КТ" / "approval level" / "completion stage" — same pattern.

## Pitfall: describe_entity with show_allowed_values

MCP has a `describe_entity` tool that returns the full entity schema. **Many people miss the `show_allowed_values` parameter**:

```python
# Just schema, no enum values
r = mcp_call("describe_entity", {"entityName": "ActivityPhase"})
# allowed_values: {} (empty!)

# Schema WITH enum values (the correct call)
r = mcp_call("describe_entity", {
    "entityName": "ActivityPhase",
    "show_allowed_values": ["__all__"]  # or specific field names
})
# allowed_values: {<field>: [{"value": 40024, "title": "Пресейл"}, ...]}
```

Special value `"__all__"` loads enums for all fields. Specific field names (e.g. `["PointTemplateActivityPhase", "Name"]`) load only those.

**Critical sub-case:** The enum you want often belongs to a DIFFERENT entity than the parent. For example, "point states" come from `describe_entity("Point", show_allowed_values=["ActivityPhaseId"])`, NOT from `describe_entity("PointTemplate", show_allowed_values=["PointTemplateActivityPhase"])`. The parent template view aggregates 100+ states across many entity types (vacations, security info, procurement), and using those will pollute your logic with foreign entity states. **Always pull from the specific entity the state belongs to.**

## Pitfall: User Correction = Immediate Re-Scope

When the user says «Подожди», «Я не говорил про X», «Ты путаешь», «Это не то» — STOP immediately. Don't argue, don't defend, don't try to fit it back into your previous framing.

Pattern:
1. "Принял!" or "Понял, извиняюсь за путаницу"
2. State the corrected understanding
3. Ask what they meant (only if still unclear)
4. Resume from the corrected baseline

Don't waste a turn on "are you sure?" — they are sure.

---

## Worked Example (2026-09-02: `fst-project-health` section 6)

| Phase | Time | What |
|-------|-----:|------|
| 0 Discovery | 7 questions in 1 turn | "where does it go? output format? verdict model? widths? columns? expansion? edge cases?" |
| 1 Skeleton | 5 min | `references/project-indicators-spec.md` + `scripts/project_indicators.py` (dataclass + SectionVerdict + cache) + `scripts/indicator_thresholds.py` |
| 2 Indicator 6.1 (Юрлицо) | 10 min | User sketch → live-probe `Project/ProjectParameter.ProjectCompanyNames` → implement `check_jurlico()` → register → test |
| 3 Indicator 6.2 (ЖЦ) | 30 min | User sketch → live-probe → discovered state lifecycle (initial/intermediate/confirmed) → 4-level model → two registries → `lc_stage_kt_registry.py` + `check_lifecycle_stage()` |
| 3-15 (planned) | 1-2h | 13 more indicators same pattern |

Result at end of phase 3: 2 working indicators, 6/6 tests pass, spec table 2/16 rows filled. **No regressions, no broken syntax, ready to keep iterating.**

Key sub-item 6.2 milestones:
- Discovered 4-state KT lifecycle (NOT just "done/not done")
- Two registries needed: our MANDATORY_KT_BY_STAGE + MCP's POINT_STATES_REGISTRY
- `describe_entity(..., show_allowed_values=["__all__"])` to discover state enums
- `_format_kt_remark()` with 5 issue types (overdue_kt, kt_missing, not_confirmed, stage_not_advanced, no_transition_command)
- User correction: "выполнена" (FactDate present) ≠ "закрыта" (state confirmed). Got wording right in user-facing messages.

---

## Anti-Pattern: "I'll do it all in one go"

The instinct to write all 16 indicators at once is wrong because:
- Each live-probe might reveal the field doesn't exist or is named differently
- The user might want to refine the verdict logic after seeing the first 2-3
- You accumulate unreviewed code that gets harder to debug
- The skeleton never gets exercised until everything is done

**Right approach:** 1 indicator → user reviews → 1 more → user reviews → ...

## Anti-Pattern: "Ask one question at a time"

Equally wrong: "one sub-item means one question". When the user says «пошагово», they're talking about SUB-ITEM delivery, not question delivery. Batch your architectural questions in Phase 0, then iterate with focused micro-questions per sub-item.

## Anti-Pattern: "I assumed you meant X"

When you're not sure whether the user means X or Y, **don't pick one and proceed**. State the ambiguity, propose both interpretations, let user pick. Especially risky when:
- The user's domain has specific terminology (e.g. «выполнена» vs «закрыта» vs «согласована»)
- Multiple registries could apply (your taxonomy vs MCP's enum)
- The data flow has multiple candidate sources (Activity vs Point view)

Pattern: "Я вижу два варианта: A и B. Если A — поле X. Если B — поле Y. Что вы имели в виду?"

---

## Pattern: Step-by-Step Modeling (when user provides cases one-by-one)

When the user says «Шаг 1: пустой проект → норма», «Шаг 2: ...», «Шаг 3: ...» — they are **modeling a complex heuristic case by case**. Each step adds a new logical clause or tightens an existing one.

### Protocol

1. **Wait for one step at a time.** Don't pre-build for step N+1, N+2.
2. **Build minimal logic for the new step only.** Patch `heuristic_evaluate()` (or equivalent) with one new `if`-block or one new severity rule.
3. **Verify no regression on previous steps.** Re-run the cases for шаги 1..N-1 mentally or via test. They must still pass.
4. **Run `python3 tests/run_all_tests.py`** — must be 6/6 PASS.
5. **Show the user the result for the new step** (verdict + issues list) so they can correct the next step if their mental model is off.
6. **Wait for the next step.**

### Anti-Pattern: "I'll build all steps at once"

Tempting because the algorithm "feels complete" after 2-3 cases. But:
- User's mental model often becomes precise only after seeing concrete outputs
- A late correction (step 5+) can invalidate everything you built for steps 2-4
- User loses confidence if they have to debug a wall of logic instead of "step 1 = OK, step 2 = OK, step 3 = fix this"

### What "not invented" means in practice

When the user says «Не выдумывать! Не писать что КТ просрочена, если она не создана» — they're enforcing a **namespace rule**: each issue type applies only to entities that exist in a state where the issue is well-defined.

Implement this as preconditions:
```python
# Шаг 3: просрочена — только если КТ существует и не выполнена
if fact_date:
    continue  # КТ выполнена → не просрочена (Шаг 3 не применяется)

# Шаг 4: не подтверждена — только если КТ выполнена
if not fact_date:
    continue  # КТ не выполнена → не подтверждена (Шаг 4 не применяется)
```

When in doubt about a precondition, ask: «когда это правило НЕ должно срабатывать?» — the user will spell out the negative case.

### Superposition: multiple pathologies in one project

When the user says «на практике может быть наложение (суперпозиция) неадекватных состояний шагов 2,3,4» — they mean one project can exhibit several pathologies at once. **The implementation must handle them all in one pass**:

```python
def heuristic_evaluate(actual_stage, kt_names, ...):
    issues = []

    # Step 2 check
    if ...:
        issues.append({"type": "missing_kt", "severity": "substantial"})

    # Step 3 check (independent of step 2!)
    if ...:
        issues.append({"type": "overdue_kt", "severity": "critical"})

    # Step 4 check (independent of steps 2 and 3!)
    if ...:
        issues.append({"type": "unconfirmed_kt", "severity": "informational"})

    # Severity priority: critical > substantial > informational > normal
    if any(i["severity"] == "critical" for i in issues):
        verdict = "Критическое"
    elif ...
```

Each `if`-block is independent. Don't make step 4 contingent on "step 2 fired" or similar.

### Worked Example: 6.2 (6 steps over ~2 hours)

| Step | What was added | Lines of code |
|------|----------------|---------------:|
| 1 | Пустой проект → Норма (skip missing for Пресейл) | ~10 |
| 2 | Не все обязательные КТ → Существенное | ~15 |
| 3 | Просрочены обязательные КТ → Критическое (FactDate required!) | ~30 |
| 4 | Выполнены, не подтверждены → Информационное (FactDate required, confirmed=False) | ~20 |
| 5 | Суперпозиция — все шаги вместе (no regression) | (no code) |
| 6 | Все КТ подтверждены, стадия не переведена → Информационное | ~15 |

After each step: `python3 tests/run_all_tests.py` → 6/6 PASS, no regression.

**User corrections that came up during this:**
- "Опять неправильно! КТ просрочена если НЕ выполнена, а не НЕ подтверждена!" → fix precondition (fact_date required for overdue, not confirmed)
- "Должно быть И НЕ Выполнена! А не И не подтверждена!" → same fix, different wording
- "ЕСЛИ КТ обязательная для текущей стадии" → only check CURRENT stage, not previous ones

Each correction was a 1-line edit to `heuristic_evaluate()`. Because of step-by-step, no earlier logic had to be thrown away.
