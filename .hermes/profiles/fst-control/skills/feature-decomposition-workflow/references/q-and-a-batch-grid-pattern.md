# Q&A Batch Grid Pattern

When the user signals an **algorithm-heavy sub-item** (multiple thresholds, multiple verdict paths, complex output format), prepare a numbered Q&A grid in ONE message — never drip-feed.

## When to Use

- Sub-item sketch doesn't fully specify: data source, format, thresholds, edge cases
- User says "пошагово", "шаг за шагом" — but for SUB-ITEM delivery, not Q delivery
- More than 3 unknowns about the indicator's logic
- After receiving the sub-item name + brief description

## Real-World Example (2026-09-02, sub-item 6.3)

### What the user said (1 message):

```
Подпункт 6.3
Прогнозы по ресурсам заданы
[image of эскиз]
```

### What I asked (1 message, 8 numbered Q's):

```
Q1: Что считать "полным периодом проекта"?
    Откуда взять дату начала проекта? Из activity.StartPlan?
    Откуда дату окончания? Из activity.FinishPlan? Forecast сначала?

Q2: Точное название специализации "Руководитель проекта"?

Q3: Если прогнозов нет вообще — это "Нет" или ошибка данных?

Q4: Часть месяца с прогнозом считается "закрытым" месяцем?

Q5: Если РП в проекте не назначен — это замечание?

Q6: Подсветка строки — что важнее: красная или жёлтая?

Q7: Формат объединённой строки — как разделять?

Q8: Кеш?
```

### How user answered (1 message):

```
Q1: ... finish по Forecast, иначе Plan, если нет — мин/макс из КТ ...
Q2: Точное название — "Руководитель проекта"
Q3: Нет
Q4: Один день = месяц закрыт
Q5: Да, замечание для каждого месяца
Q6: Как ты предлагаешь
Q7: Без кавычек, запятая между
Q8: Использовать кеш
```

### Why this works

- **8 questions in 1 turn** instead of 8 turns of drip-feeding
- User can think holistically about the indicator before answering
- Some questions reveal **prerequisites** the user didn't think about (e.g. "what if no PM is assigned at all?")
- Batch answers often reveal inconsistencies the user catches themselves

## Anti-Pattern: Drip-Feeding

❌ "What view should I use?" → wait → "What filters?" → wait → "What fields?" → ...
   - 6 turns wasted on micro-questions
   - User can't see the full scope of what's needed

✓ Numbered grid with 5-8 questions → user answers all at once
   - 1 turn to clarity
   - User maintains the big picture

## Anti-Pattern: Assuming Instead of Asking

❌ "I'll use `ProjectResourcePlan` with `filters={ProjectId}` and check `forecast_hours > 0` for each month, with severity priority..."
   - Bakes in assumptions the user might disagree with
   - Hard to refactor when user says "no, I meant X"

✓ "Two open questions: (a) which view to query for прогнозы? (b) what counts as 'закрытый' месяц? Both critical — picking wrong breaks the whole logic."

## When Drip-Feeding Is OK

- User explicitly says "ask me one at a time" (rare, but possible)
- The answer to Q1 determines what Q2 even makes sense
  - Example: Q1 = "what does 'completed' mean?" → answers "FactDate present" → Q2 = "which field?" makes sense
- Sub-item has 10+ questions and answer dependencies are tangled

For 80% of cases, batch the questions.
