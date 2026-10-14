# Multi-view fallback pattern — for `find_*_by_*` scripts

When searching for an entity by user-visible attribute (`Code`, `Name`, etc.),
Foresight exposes **multiple views** that all could contain matches. The naive
pattern «try the first view, return its results» silently drops matches that
happen to live in a different view.

This is the **general fix template** for any `find_*` script in the Foresight
toolkit, not just `find_project_by_code.py`.

## Symptoms of the bug

- `find_project_by_code("503-152")` returns `ProjectNotFoundError`, but the
  project DOES exist (visible in `get_view(Project, AllProject, ...)`).
- `get_user_profile` works, but the user has 0 visible projects.
- Any search script that «finds 0 of N» when manual `get_view` shows the
  record.

## Root cause

Foresight's view system splits records by access path:

- **`My*`** (e.g. `MyProject`) — records where the user has a «participant»
  role (Исполнитель, Руководитель, etc.).
- **`All*`** (e.g. `AllProject`) — records visible to the user in any capacity,
  including «Администратор», «Наблюдатель», «Куратор».

A user on the «Администратор» track of a project may see the project in
`AllProject` but not in `MyProject`. The reverse also happens.

## Fix template

Replace:

```python
def _fetch_records(sid):
    for view_name in ("MyX", "AllX"):
        data = _mcp_call_view(sid, view_name)
        if data is not None:
            return data     # ❌ returns first successful view's data, drops others
    raise NotFound(...)
```

With:

```python
def _fetch_records(sid):
    collected = []
    seen_ids = set()
    errors = []
    for view_name in ("MyX", "AllX"):
        data = _mcp_call_view(sid, view_name)
        if data is None:
            errors.append(f"{view_name}: failed")
            continue
        for record in data:
            rid = record.get("IdFieldName")  # the PK
            if rid not in seen_ids:
                seen_ids.add(rid)
                collected.append(record)
    if not collected:
        raise NotFound(f"ничего не найдено; ошибки: {errors}")
    return collected
```

Key changes:

1. **Collect from every successful view**, not just the first.
2. **Deduplicate by primary key** (`ProjectId`, `InContractId`, etc.) — same
   record can appear in both `MyX` and `AllX`.
3. **Track all errors** for the final exception message — helps debug
   permission issues.

## Apply to other search scripts

The same pattern likely applies to:

- `find_contract_by_code.py` (if it exists) — `MyContract` vs `AllContract`
- `find_user_by_name.py` (if it exists) — `MyUser` vs `AllUser`
- Any future search script — default to «collect + dedup», not «first wins»

## Live test that exposed this bug

```
Project: 503-152 «ФРП - Минпромторг-Развитие 2026»
User role on project: Администратор

MyProject:   7 rows, NO 503-152 (because user is not a «participant»)
AllProject: 109 rows, INCLUDES 503-152

Bug: find_project_by_code('503-152') raised ProjectNotFoundError
     because it returned MyProject's 7 rows and never fell through to AllProject.

Fix: collect from both views, dedup → finds 503-152. ✓
```

Date of fix: 2026-08-06.
