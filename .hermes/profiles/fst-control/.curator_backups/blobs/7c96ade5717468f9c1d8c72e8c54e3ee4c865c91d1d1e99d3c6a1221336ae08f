# Bash-обёртка вокруг MCP-extract → consumer

Когда bash-скрипт объединяет шаги «MCP-извлечение» и «сборка отчёта» в одну команду,
несколько подводных камней уже задокументированы в SKILL.md (pitfall #10). Этот файл —
готовая заготовка, которую можно скопировать и адаптировать.

## Шаблон

```bash
#!/usr/bin/env bash
# build_X_from_snapshot.sh
# Цепочка: <mcp-extract>.py --code X [--mode] → <consumer>.py --md <MD> → <artifact>.

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Использование: $0 <project_code> [<project_code> ...]"
    exit 2
fi

# Пути — относительно расположения скрипта, не $PWD.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT_DIR="${SCRIPT_DIR}/../<other-skill>"
CONSUMER="${SCRIPT_DIR}/<consumer>.py"
CACHE_DIR="${HOME}/.hermes/profiles/fst-control/cache/<dir>"

for code in "$@"; do
    echo ""
    echo "=== ${code} ==="

    # 1) Извлечение. stderr подавляем, stdout — не парсим (там ANSI/emoji).
    python3 "${EXTRACT_DIR}/scripts/<extract>.py" \
        --code "${code}" --last --no-log >/dev/null 2>&1 || true

    # 2) Берём самый свежий файл из кэша — НЕ парсим вывод extract'а.
    md_path=$(ls -1t "${CACHE_DIR}/${code}_"*.md 2>/dev/null | head -1 || true)

    if [[ -z "${md_path}" || ! -f "${md_path}" ]]; then
        echo "✗ ${code}: не удалось получить MD"
        continue
    fi

    echo "📥 MD: ${md_path}"

    # 3) Сборка. Явный интерпретатор!
    out_path="/tmp/${code}_$(date +%Y-%m-%d_%H%M%S)_<ext>"
    if python3 "${CONSUMER}" \
            --md "${md_path}" --code "${code}" --output "${out_path}" 2>&1 | tail -5; then
        echo "✅ <artifact>: ${out_path}"
    else
        echo "✗ ${code}: ошибка сборки"
    fi
done
```

## Что здесь критично

1. **`set -euo pipefail`** — падать на неуказанных переменных и сломанных pipe'ах.
2. **`python3 <полный путь>`** — никогда без интерпретатора, иначе `Permission denied` (bash не читает shebang при форке через `${VAR}`).
3. **`>/dev/null 2>&1 || true`** на шаге извлечения — подавляем любой вывод и не падаем, если extract вернул ненулевой код (часто это делают наши `result: {}` transient-ошибки).
4. **`ls -1t "${CACHE_DIR}/${code}_"*.md | head -1`** — самый свежий файл по mtime из КЭША, не из stdout extract'а. Цветные ANSI/emoji ломают regex.
5. **`|| true` после `ls`** — иначе set -e уронит скрипт, если файла нет.
6. **`if python3 ... | tail -5`** — печатаем последние 5 строк вывода consumer'а (он шумит, целиком лог не нужен).

## Типичные ошибки

| Симптом | Причина | Лечение |
|---|---|---|
| `Permission denied` на скрипт | Забыли `python3` | Добавить интерпретатор |
| `set -e: command failed` после `ls` | `ls` упал на empty glob | Добавить `|| true` |
| Парсинг ANSI не работает | `result: {}` в выводе + цвета | Использовать `ls -1t` на кэш |
| Один проект валит весь скрипт | Нет `continue` после ошибки | Оборачивать в `if/then` |
| `Cannot stat: No such file or directory` | Переменная `$EXTRACT_DIR` указывает не туда | Использовать `SCRIPT_DIR` |
