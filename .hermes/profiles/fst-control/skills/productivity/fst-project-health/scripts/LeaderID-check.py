__version__ = "1.0.19"
record = mcp__fst_pmpractice__get_entity_data(
    entityName="Project",
    data_id="4595"
)

leader = record["properties"]["LeaderId"]
val = leader.get("value")
if not val:
    result = "Нет"
    detail = "Руководитель проекта (LeaderId) не назначен"
else:
    first = val[0] if isinstance(val, list) else val
    if isinstance(first, dict) and first.get("display"):
        result = "Да"
        detail = first["display"].strip()
    else:
        result = "Да"
        detail = f"id={first}"
