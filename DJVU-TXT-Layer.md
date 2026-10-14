# DjVu → TXT — извлечение текстового слоя

> Ответ на вопрос: «А можно выделить текстовый слой DJVU в отдельный файл?»
> Дата: 2026-08-09

---

## Короткий ответ

**Да, можно.** DjVu может содержать **скрытый текстовый слой** (HOCR/Unicode),
и его можно извлечь одной командой. Если текстового слоя нет (только картинки),
нужен **OCR** через tesseract.

---

## 1. Что на mima_g_01 сейчас

| Инструмент | Статус |
|---|---|
| djvulibre-bin (djvused, djvuextract) | НЕ установлен |
| libdjvulibre21 runtime | НЕ установлен |
| tesseract | НЕ установлен |
| tesseract-ocr-rus | НЕ установлен |
| Python djvu lib | НЕТ |
| djview4 (viewer) | НЕТ |

**Ничего нет для DjVu.** Нужно устанавливать.

---

## 2. DjVu — два варианта

### Вариант 1: Embedded text layer (DjVu с OCR)

DjVu может содержать **скрытый текстовый слой** (HOCR / Unicode).
Это бывает, когда документ изначально был отсканирован с распознаванием.

```
DjVu file
  background.jpg (страница)
  foreground.jpg (маска текста)
  text.txt (скрытый текст) — это извлекаем
```

Если текстовый слой есть — извлекается одной командой:

```bash
djvuextract -text document.djvu text.txt
```

### Вариант 2: Только картинки (скан без OCR)

Если DjVu — просто сканы без распознанного текста, нужен **OCR**:

```bash
djvused -e 'select 1; print' document.djvu  # список страниц
# потом через tesseract
```

---

## 3. Что нужно установить

### Минимум (для embedded text)

```bash
sudo apt install djvulibre-bin
```

Размер: ~5 MB. Даёт команды: `djvused`, `djvuextract`, `djvm`, `djvused`.

### Полный (с OCR)

```bash
sudo apt install djvulibre-bin tesseract-ocr tesseract-ocr-rus
```

Размер: ~100 MB. Включает русский язык.

### Языковые пакеты tesseract

| Пакет | Язык |
|---|---|
| tesseract-ocr-eng | английский |
| tesseract-ocr-rus | русский |
| tesseract-ocr-deu | немецкий |
| tesseract-ocr-fra | французский |
| tesseract-ocr-ukr | украинский |
| tesseract-ocr-all | все языки (~2 GB) |

---

## 4. Пошаговый план работы

### Шаг 1. Установить djvulibre

```bash
sudo apt update
sudo apt install -y djvulibre-bin
```

### Шаг 2. Проверить

```bash
which djvused
which djvuextract
djvused --help 2>&1 | head -5
```

### Шаг 3. Попробовать embedded text

```bash
djvuextract -text /path/to/document.djvu /tmp/document_text.txt
```

Если файл создан и в нём текст — готово.

### Шаг 4. Если нет embedded text — установить OCR

```bash
sudo apt install -y tesseract-ocr tesseract-ocr-rus
```

### Шаг 5. Конвертировать DjVu → изображения

```bash
# Установить если нужно
sudo apt install -y djvulibre-bin

# Извлечь страницы в формат PPM
djvused -e 'select 1; print' document.djvu  # показать структуру

# Через ddjvu
ddjvu -format=ppm -page=1 document.djvu page_001.ppm
```

### Шаг 6. OCR каждую страницу

```bash
for i in $(seq 1 100); do
  ddjvu -format=ppm -page=$i document.djvu page_$(printf '%03d' $i).ppm
  tesseract page_$(printf '%03d' $i).ppm page_$(printf '%03d' $i) -l rus+eng
done

# Собрать
cat page_*.txt > /tmp/full_text.txt
```

---

## 5. Альтернативный путь — через PyMuPDF

PyMuPDF (fitz) — у нас **уже установлен**, v1.27.2.3. Он умеет читать
DjVu через MuPDF:

```python
import fitz  # PyMuPDF

doc = fitz.open("document.djvu")
print(f"Pages: {doc.page_count}")

output = []
for page_num, page in enumerate(doc):
    text = page.get_text("text")
    output.append(f"# Page {page_num + 1}

{text}
")

with open("document_text.md", "w", encoding="utf-8") as f:
    f.write("
".join(output))
```

| Плюс | Минус |
|---|---|
| Уже установлен | Может не работать со старыми DjVu |
| Простой API | OCR сам не делает |
| Один файл = результат | |

---

## 6. Готовый скрипт — djvu_to_text.py

```python
#!/usr/bin/env python3
"""
Извлечение текста из DjVu файла.
- Если есть embedded text layer — извлекает
- Если нет — делает OCR через tesseract
"""

import sys
import subprocess
import os
from pathlib import Path

def try_djvuextract(djvu_path: str, output_path: str) -> bool:
    """Попробовать извлечь embedded text."""
    try:
        result = subprocess.run(
            ["djvuextract", "-text", djvu_path, output_path],
            capture_output=True, text=True, timeout=60
        )
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            if size > 100:
                print(f"Extracted via djvuextract: {size} bytes")
                return True
    except FileNotFoundError:
        print("djvuextract not found")
    except Exception as e:
        print(f"djvuextract failed: {e}")
    return False


def ocr_djvu(djvu_path: str, output_path: str, lang: str = "rus+eng") -> bool:
    """OCR через ddjvu + tesseract."""
    try:
        # Получить количество страниц
        info = subprocess.run(
            ["djvused", "-e", "select 1; print", djvu_path],
            capture_output=True, text=True, timeout=30
        )
        # Простой способ: попробовать страницы
        all_text = []
        for page in range(1, 1000):  # safety limit
            ppm = f"/tmp/page_{page:04d}.ppm"
            result = subprocess.run(
                ["ddjvu", "-format=ppm", f"-page={page}", djvu_path, ppm],
                capture_output=True, text=True, timeout=30
            )
            if not os.path.exists(ppm) or os.path.getsize(ppm) == 0:
                break
            txt = f"/tmp/page_{page:04d}.txt"
            subprocess.run(
                ["tesseract", ppm, txt.replace(".txt", ""), "-l", lang],
                capture_output=True, text=True, timeout=120
            )
            if os.path.exists(txt):
                all_text.append(f"\n--- Page {page} ---\n{txt}")
            os.remove(ppm)
            os.remove(txt)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(all_text))
        return True
    except FileNotFoundError as e:
        print(f"OCR tool not found: {e}")
    except Exception as e:
        print(f"OCR failed: {e}")
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: djvu_to_text.py <input.djvu> [output.txt]")
        sys.exit(1)

    djvu_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.txt"

    if not os.path.exists(djvu_path):
        print(f"File not found: {djvu_path}")
        sys.exit(1)

    # Способ 1: embedded text
    if try_djvuextract(djvu_path, output_path):
        print(f"Done: {output_path}")
        return

    # Способ 2: OCR
    print("No embedded text, trying OCR...")
    if ocr_djvu(djvu_path, output_path):
        print(f"Done via OCR: {output_path}")
        return

    print("All methods failed")
    sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 7. Что мне нужно от тебя

| Что | Зачем |
|---|---|
| Путь к DjVu файлу | где лежит |
| Знаешь ли про embedded text | не знаешь? попробуем сначала без OCR |
| Язык документа | русский, английский? |
| Куда сохранить | формат .txt, .md, .docx |

---

## 8. Команды для старта

| Команда | Что делаю |
|---|---|
| «Установи djvulibre-bin» | поставлю через apt |
| «Установи с OCR» | djvulibre + tesseract + rus |
| «У меня DjVu файл — вот путь» | буду работать |
| «Это скан без текста» | сразу OCR |

---

## 9. Что я НЕ делал

| Действие | Статус |
|---|---|
| Устанавливал djvulibre | не делал |
| Устанавливал tesseract | не делал |
| Жду от тебя путь к файлу | ожидание |

---

## 10. Маршрут

| Шаг | Действие |
|---|---|
| 1 | Скажи путь к файлу |
| 2 | Установлю djvulibre-bin |
| 3 | Попробую djvuextract -text |
| 4 | Если нет текста — установлю tesseract |
| 5 | Сделаю OCR |
| 6 | Сохраню в /tmp или в /root |

---

## 11. Главная мысль

> Да, могу. Сначала установлю djvulibre-bin (~5 MB) и попробую
> извлечь embedded text. Если DjVu — скан без текста, поставлю
> tesseract и сделаю OCR. Скажи путь к файлу — начну.

---

*Документ создан 2026-08-09, отправлено через @MMRV_Hermes_bot в Telegram.*
