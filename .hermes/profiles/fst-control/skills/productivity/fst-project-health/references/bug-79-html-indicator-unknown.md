# Bug #79: HTML indicator показывает "Нет данных" (status="unknown") — добавлен 2026-08-21, файл создан 2026-08-22

**Live-probe:** 2026-08-21 на 504-314 (пользователь: «Индикатор в заголовке серого цвета, а в нём надпись "Нет данных"»).

**Симптом:** в HTML-отчёте `data-status="unknown"` + текст «Нет данных» на индикаторе, хотя MD имеет «Болен» в разделе 6 (финансы) и вердикт должен быть `sick`.

**Причина:** `compute_verdict()` в `build_html_report.py:261` искал `**Статус раздела:**`:
```python
m = re.search(r"\*\*Статус раздела:\*\*\s*(.+)", sec)
```

Но `run_all.py` пишет `**Вердикт раздела:**`:
```python
text = f"## 3. Замечания по срокам\n\n**Вердикт раздела:** {verdict}\n..."
```

Regex **никогда** не находил → все 4 section_verdicts = Здоров (default) → общий verdict = "Нет данных" → status="unknown".

**Фикс в `build_html_report.py`:**
```python
# ВАЖНО: regex должен принимать ОБА варианта:
# - Старый формат (до run_all.py): **Статус раздела:** Здоров
# - Новый формат (run_all.py): **Вердикт раздела:** Болен
m = re.search(r"\*\*(?:Вердикт|Статус) раздела:\*\*\s*(.+)", sec)
```

**Чек-лист после фикса:**
```bash
# 1. Indicator должен иметь sick/attention/healthy, не unknown
grep 'data-status=' /tmp/project_<code>_report.html
# ❌ data-status="unknown" (BUG!)
# ✅ data-status="sick"

# 2. Текст индикатора — реальный вердикт
grep 'verdict-text' /tmp/project_<code>_report.html
# ❌ "Нет данных" (BUG!)
# ✅ "Проект болен" / "Требует внимания" / "Здоров"
```

**См. также:** Bug #70 (в SKILL.md) — этот баг уже был там, но без отдельного reference-файла. Сейчас (2026-08-22) Bug #70 в SKILL.md уже есть и фикс уже применён.
