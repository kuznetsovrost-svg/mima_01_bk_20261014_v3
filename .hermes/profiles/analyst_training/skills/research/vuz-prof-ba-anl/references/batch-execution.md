# Batch execution pattern for vuz-prof-ba-anl

Рецепт применения skill'а к N файлам из `Inputs/` последовательно, с отслеживанием статуса и доставкой результатов пользователю.

## Когда применять

- Пользователь дал N ≥ 2 файлов в `Inputs/` и просит «обработай все» / «проанализируй каждый» / «сделай отчёт по каждому».
- В task-файле явно указан список `Outputs/`.
- Каждый отчёт должен быть независим (анализируется отдельный файл, без смешивания с соседними).

## Цикл одного файла

```
1. read_file(Inputs/<имя>)                          # прочитать источник
2. mark per_file_status[имя] = "in_progress"        # в progress.json
   mark per_file_status[имя].started_at = now
3. write_file(Outputs/SANL_<имя>.md, отчёт)         # полный отчёт по 10 разделам
4. mark per_file_status[имя] = "done"               # в progress.json
   mark per_file_status[имя].finished_at = now
   mark per_file_status[имя].report_path = относительный путь
```

Не выполняй шаги 1–4 параллельно через `delegate_task` — skill требует «анализировать независимо, заново», а подзадачи внутри одного аккаунта могут перетянуть контекст между файлами.

## Подготовка перед циклом

### Сверить имена

`os.listdir(Inputs/)` — единственный источник истины для имён файлов. Task-файл может указывать имена с пробелами, а на диске они с подчёркиваниями. Всегда:

```python
inputs = sorted(os.listdir(inputs_dir))
# использовать inputs как список файлов
# итоговое имя отчёта: f"SANL_{name}.md"
```

### Спросить про политику ссылок ДО первого write_file

Правило 5 skill'а требует. Формулировка для `clarify`:

> «Web-поиск [недоступен / доступен]. Если недоступен — применять ссылки из моих знаний (не верифицированы, помечу `[не верифицировано]`) или сократить отчёт до §1–§6 без ссылок?»

Без этого ответа 5-й отчёт уже будет написан по выдуманной политике.

### Создать progress.json

```json
{
  "task_id": "TASK-...",
  "state": "draft",
  "per_file_status": {
    "<file1>": {"state": "pending", "started_at": null, "finished_at": null, "report_path": null},
    ...
  },
  "overall": {"state": "draft", "started_at": null, "finished_at": null}
}
```

Не пиши `state: "done"` заранее — заполняй по мере прохождения цикла.

## Доставка результатов в Telegram

`.md` и `.txt` — нативные attachment-расширения. Синтаксис:

```
📎 MEDIA:/absolute/path/to/file.md
```

Несколько файлов подряд — по одному `MEDIA:` на сообщение, с `sleep 2` между ними, иначе Telegram-клиент может проглотить часть как дубли.

Если пользователь говорит «пришло как текст, а не как файл» — это **не** баг формата. Telegram-клиент в первый раз отрисовал attachment как inline preview. Повторная отправка + явное «это файл, иконка 📎 внизу» решает вопрос. См. `references/messaging.md` (в skill `hermes-agent-skill-authoring`).

## Финальный статус

После последнего файла:

```python
prog["overall"]["state"] = "done"
prog["overall"]["finished_at"] = now
(proj_dir / "progress.json").write_text(...)
```

И **отдельно** записать короткий итоговый отчёт в файл `TASK-<ID>-аббревиатура-агента-NN.md` в корне профиля, не в `Outputs/` (это артефакт агента, а не пользовательский отчёт по программе).

## Восстановление после сбоя

Если цикл оборвался на файле 3 из 5:

```python
prog = json.loads(progress_path.read_text())
for fname, st in prog["per_file_status"].items():
    if st["state"] == "done":
        print(f"skip {fname}")  # уже готов
    elif st["state"] == "in_progress":
        # либо переделать (finished_at = None значит не записано)
        # либо принять как done, если файл в Outputs уже есть
```

Сверять `state == "done"` с реальным наличием файла в `Outputs/`. Файл мог быть записан, а `progress.json` обновиться не успел.

## Чек-лист перед запуском

- [ ] `Inputs/` прочитан, имена сверены с task
- [ ] `Outputs/results/<TASK-ID>/` создан и пуст
- [ ] `progress.json` создан, все per_file_status = "pending"
- [ ] Пользователь подтвердил политику ссылок (если веб недоступен)
- [ ] Plan-файл `plans/<TASK-ID>.md` существует

## Чек-лист после запуска

- [ ] Все per_file_status = "done"
- [ ] overall.state = "done"
- [ ] Кол-во файлов в `Outputs/` = кол-ву в `Inputs/`
- [ ] Итог `TASK-<ID>-аббревиатура-NN.md` записан
- [ ] Plan обновлён разделом «Статус выполнения»