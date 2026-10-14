# Skill Candidate Review — Report Template

Use this skeleton for the report you deliver to the user. Number each WARN
(W1, W2, ...) and substance observation (S1, S2, ...) so the user can refer
back to specific items in chat ("fix W3 and W5, ignore the rest").

---

```
============================================================
ОТЧЁТ О ВАЛИДАЦИИ ФАЙЛА КАК КАНДИДАТА В SKILL
============================================================

Файл:       <name>.md
Размер:     <N> символов
Frontmatter: <N> байт (до закрывающего ---)
Body:       <N> символ
Дата проверки: <YYYY-MM-DD>, профиль <profile>

============================================================
1. ИТОГОВЫЙ ВЕРДИКТ
============================================================

<PASS | WARN | BLOCKER> — one-line summary.
<1-3 sentences: what passes, what blocks, recommended next step.>

============================================================
2. BLOCKER-ПРОВЕРКИ (то, что ломает загрузку skill)
============================================================

[OK]   File starts with '---' at byte 0 (no leading blank/BOM)
[OK]   Closing '\n---\n' present
[OK]   YAML in frontmatter parses cleanly
[OK]   'name' and 'description' fields present
[OK]   'description' length = <N> chars (limit 1024)
[OK]   File length = <N> chars (limit 100000)
[OK]   Body after closing --- non-empty
[FAIL] <if any: state which check failed>

Блокеров: <count>. Файл <загрузится | не загрузится>.

============================================================
3. WARN-ЗАМЕЧАНИЯ (peer-convention, не критично)
============================================================

W1. <WARN> <category> — <observation>
    Текущее:  <value>
    Конвенция: <peer convention>
    Рекомендация: <fix>

W2. ...

W3. ...

============================================================
4. SUBSTANCE-ЗАМЕЧАНИЯ (содержание, не валидатор)
============================================================

S1. <SUBSTANCE> <completion criteria missing on step N>
S2. <SUBSTANCE> <no-op prose detected: "be careful", ...>
S3. <SUBSTANCE> <trigger too narrow — describes task, not class>
S4. <SUBSTANCE> <missing "Don't use for:" counter-triggers>

============================================================
5. ОПЕЧАТКИ В ТЕЛЕ (таблица)
============================================================

| # | Опечатка     | Правильно       | Контекст / строка            |
|---|--------------|-----------------|------------------------------|
| 1 | ...          | ...             | L<N>: ...                    |
| 2 | ...          | ...             | L<N>: ...                    |

<Mark false positives explicitly so the user doesn't waste time.>

============================================================
6. ИТОГОВЫЙ ЧЕКЛИСТ ПЕРЕД СОЗДАНИЕМ SKILL
============================================================

Перед skill_manage(action='create', ...) исправить:

[ ] W<n> — <concrete edit>
[ ] W<n> — <concrete edit>
[ ] S<n> — <concrete edit>
[ ] Опечатки #<n>, #<n>, ... (false positives отметить как ОК)

Не критично, но рекомендуется:
[ ] <optional improvement>

============================================================
КОНЕЦ ОТЧЁТА
============================================================
```

## Delivery rules

- **Chat-only review**: send the report inline. Do NOT write to disk.
- **File review** ("пришли файл"): write to `<candidate-stem>-rep01.txt`
  next to the source. Increment `rep01` → `rep02` if a prior report exists.
  Send via `MEDIA:/absolute/path` so Telegram ships it as an attachment.

## Tone

- BLOCKER findings: direct, no hedging ("Файл не загрузится, потому что...").
- WARN findings: matter-of-fact ("не критично, но peer-конвенция требует...").
- Substance findings: one observation per item, no padding.
- Typos: tabulated, with line numbers so the user can find-fix in one pass.

Never open with apologies or restate what the user asked. They asked for a
review; deliver the review.