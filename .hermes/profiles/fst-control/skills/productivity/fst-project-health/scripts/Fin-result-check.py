__version__ = "1.0.19"
# ⚠️ HARDCODED EXAMPLE — захардкожены PROJECT_CODE и PROJECT_ACTIVITY_ID.
#    Это альтернативный fallback-подход к показателю 1 раздела 6
#    (через КТ-оплаты контрактов). Использовать, если ProjectHealthCostMy
#    пуст или недоступен.
#    Основной подход — Forecasted-financial-result.py (через агрегат
#    ProjectHealthCostMy.forecast).
PROJECT_ACTIVITY_ID = 4595  # ActivityId проекта 504-595
PROJECT_CODE = "504-595"
THRESHOLD_PROFITABILITY = 0  # результат < 0 = убыток

# 1. Доходные контракты
in_contracts = []
# Через InContractAll (с фильтром по InContractActivity)
ic_all = mcp__fst_pmpractice__get_view(
    entityName="InContract", viewName="InContractAll", limit=1000
)
for c in ic_all["data"]:
    if str(c.get("Code", "")).startswith("704-724"):  # целевой контракт
        detail = mcp__fst_pmpractice__get_entity_data(
            entityName="InContract", data_id=str(c["InContractId"])
        )
        in_contracts.append(detail)

# 2. Расходные контракты
out_contracts = []
# Аналогично через OutcomeContractAll
oc_all = mcp__fst_pmpractice__get_view(
    entityName="OutcomeContract", viewName="OutcomeContractAll", limit=1000
)
# (для нашего проекта пока 0)

# 3. КТ проекта
points = mcp__fst_pmpractice__get_view(
    entityName="Point", viewName="AllMyPoint", limit=3000
)
project_points = [p for p in points["data"]
                  if str(p.get("ParentCode", "")).strip() == PROJECT_CODE]

# 4. Эффективные суммы
def effective(point_props):
    f = float(point_props.get("FactSum", {}).get("value") or 0)
    fc = float(point_props.get("ForecastSum", {}).get("value") or 0)
    return f if f > 0 else fc

# 5. Суммы (берем КТ с именем "Оплата" — это финансовые проводки)
total_income = 0
total_expense = 0
income_contract_codes = {c["properties"]["Code"]["value"] for c in in_contracts}
expense_contract_codes = {c["properties"]["Code"]["value"] for c in out_contracts}

for p in project_points:
    parent = str(p.get("ParentCode", "")).strip()
    if parent in income_contract_codes:
        # ⚠️ N+1 запросов к MCP (по одному на каждую КТ) — медленно.
        detail = mcp__fst_pmpractice__get_entity_data(
            entityName="Point", data_id=str(p["PointId"])
        )
        name = (detail["properties"].get("Name", {}).get("value") or "").lower()
        if "оплат" in name or "платеж" in name or "платёж" in name:
            total_income += effective(detail["properties"])
    elif parent in expense_contract_codes:
        # аналогично для расходов
        ...

result = total_income - total_expense

# 6. Вердикт
if result < THRESHOLD_PROFITABILITY:
    row_result = "Да"
    detail = f"Прогноз: {result:,.2f} ₽ — это критическое замечание"
else:
    row_result = "Нет"
    detail = f"Прогноз: +{result:,.2f} ₽"
