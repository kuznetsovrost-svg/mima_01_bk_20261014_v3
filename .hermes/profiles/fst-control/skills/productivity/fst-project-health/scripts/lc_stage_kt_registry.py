__version__ = "1.0.19"
"""
lc_stage_kt_registry.py — справочник обязательных КТ по стадиям ЖЦ.

Используется индикатором 6.2 «Актуальность состояния ЖЦ» для проверки
соответствия указанной стадии ЖЦ реальному наличию обязательных КТ.

Структура:
- LC_STAGES: список стадий ЖЦ в порядке (от ранней к поздней)
- MANDATORY_KT_BY_STAGE: dict {стадия: [список обязательных КТ]}
- POINT_STATES_REGISTRY: справочник состояний КТ (из MCP allowed_values)
- UTILITY: функции для работы со справочниками

ДВА РАЗНЫХ СПРАВОЧНИКА (не путать!):
1. MANDATORY_KT_BY_STAGE — наш внутренний справочник обязательных КТ по стадиям ЖЦ
2. POINT_STATES_REGISTRY — справочник состояний КТ (из MCP describe_entity)

ШАГИ ПРОВЕРКИ ДЛЯ ИНДИКАТОРА 6.2 (применяются на КАЖДОЙ стадии ЖЦ):

Шаг 1. Пустой проект (только Пресейл, нет КТ в плане) → НОРМА
       На других стадиях Шаг 1 невозможен (если стадия > Пресейл, КТ предыдущих стадий должны быть).
       Это означает что мы неявно считаем что Шаг 1 срабатывает ТОЛЬКО когда actual_stage == "Пресейл".

Шаг 2. Обязательные КТ текущей стадии (из MANDATORY_KT_BY_STAGE[actual_stage]):
       - Если ВСЕ созданы → НОРМА (для текущего шага)
       - Если НИ ОДНОЙ нет, но в плане есть другие КТ → СУЩЕСТВЕННОЕ + замечания по отсутствующим
       - Если ЧАСТЬ создана → СУЩЕСТВЕННОЕ + замечания по отсутствующим

Шаг 3. Обязательная КТ текущей стадии:
       - КТ создана, ForecastDate < today, НЕ выполнена (нет FactDate)
       - → КРИТИЧЕСКОЕ + "Просрочена обязательная КТ '<X>', N дн."

Шаг 4. Обязательная КТ текущей стадии:
       - КТ выполнена (есть FactDate), НЕ подтверждена
       - → ИНФОРМАЦИОННОЕ + "КТ '<X>' выполнена, но не подтверждена N дн."

Шаг 5. Суперпозиция (несколько шагов одновременно):
       - Шаги 2+3+4 могут срабатывать одновременно
       - Verdict = максимум из всех шагов (Критическое > Существенное > Информационное > Норма)
       - Все замечания выводятся одновременно
       - НЕ выдумывать: если КТ не создана → не пишем "просрочена"/"не подтверждена"

Шаг 6. Все обязательные КТ текущей стадии:
       - ВСЕ созданы + ВСЕ выполнены + ВСЕ подтверждены
       - → ИНФОРМАЦИОННОЕ + "Не выполнен переход на следующую стадию ЖЦ"
       - Причина: пользователь забыл нажать кнопку перехода в UI

Эта совокупность шагов позволяет определить, соответствует ли состояние ЖЦ
проекта требованиям к управлению, на ЛЮБОЙ стадии.
"""
from typing import List, Dict, Optional

# Импортируем единый источник истины о состояниях КТ
from point_states import (
    PointState, POINT_STATE_IDS, POINT_STATE_TO_ID,
    is_confirmed as ps_is_confirmed,
    is_initial as ps_is_initial,
    is_cancelled as ps_is_cancelled,
    blocks_transition as ps_blocks_transition,
    state_by_id, id_by_state, get_state_level,
)


# ============================================================================
# Справочник 1: Стадии ЖЦ проекта (наш внутренний)
# ============================================================================

LC_STAGES: List[str] = [
    "Пресейл",
    "Инициирование",
    "Подготовка",
    "Реализация",
    "Завершение",
    "Архив",  # архивная (после Завершения)
]

MANDATORY_KT_BY_STAGE: Dict[str, List[str]] = {
    "Пресейл": [
        "Пресейл открыт",
        "Пресейл закрыт",
        "Направлено предложение Заказчику",
    ],
    "Инициирование": [
        "Проект открыт",
    ],
    "Подготовка": [
        "Рабочий план утвержден",
        "Договор подписан",
    ],
    "Реализация": [
        "Результаты работ приняты",
    ],
    "Завершение": [
        "Маркетинговые материалы предоставлены",
        "Выполнены все финансовые обязательства",
        "Карточка проекта заполнена корректно",
        "Итоговый отчет утвержден",
    ],
    "Архив": [],
}


# ============================================================================
# Справочник 2: Состояния КТ (из MCP)
# ============================================================================
#
# Источник: describe_entity(PointTemplate, show_allowed_values=['PointTemplateActivityPhase'])
# Live-probe 2026-09-02: получено 106 значений (52 уникальных названия).
#
# Здесь — КРАТКИЙ справочник, используемый в 6.2 для определения статуса КТ.
# Полный список — в MCP. Этот список — подмножество для быстрого доступа.

# ============================================================================
# Справочник 2: Состояния КТ (из MCP — ТОЛЬКО для Point, не для других сущностей!)
# ============================================================================
#
# Источник (ПРАВИЛЬНЫЙ):
#   describe_entity(entityName="Point", show_allowed_values=["ActivityPhaseId"])
#
# Live-probe 2026-09-02: получено РОВНО 4 состояния (не 106 как в PointTemplate):
#   - В работе (10012)        — КТ не выполнена, начальное
#   - Выполнена (10018)       — КТ выполнена, но НЕ подтверждена согласующим
#   - Отменено (40031)        — КТ отменена (не блокирует переход)
#   - Подтверждена (40041)    — КТ закрыта и подтверждена согласующим
#
# НЕ ПУТАТЬ с PointTemplateActivityPhase — тот справочник содержит 106 значений
# (включая специфичные для других сущностей: отпуска, ЗИ, конкурсы).
# Для КТ используем ТОЛЬКО эти 4 состояния.

POINT_STATES_REGISTRY: Dict[int, str] = {
    # ID → название состояния КТ (только для Point!)
    10012: "В работе",       # initial — КТ ещё не выполнена
    10018: "Выполнена",      # intermediate — есть факт.дата, но не подтверждена
    40031: "Отменено",       # cancelled — КТ отменена
    40041: "Подтверждена",   # final — КТ закрыта и согласована
}


# ============================================================================
# ЖИЗНЕННЫЙ ЦИКЛ СОСТОЯНИЯ КТ (по убыванию "продвинутости")
# ============================================================================
#
# 1. "Подтверждена" — КТ закрыта И согласующий подтвердил. Финальное состояние.
#    КТ НЕ блокирует переход на следующую стадию ЖЦ.
#
# 2. "Выполнена" — указана фактическая дата выполнения, НО согласующий
#    ещё не подтвердил. КТ блокирует переход на следующую стадию.
#
# 3. "В работе" — КТ ещё не выполнена (нет фактической даты).
#    КТ блокирует переход.
#
# 4. "Отменено" — КТ отменена (не влияет на переход).
#
# ПОРЯДОК ПРОВЕРКИ:
# 1. Сначала проверяем что КТ в состоянии "Подтверждена"
# 2. Если нет, но есть "Выполнена" → выполнена, но не подтверждена
# 3. Иначе если "В работе" → не выполнена
# 4. Если "Отменено" → игнорируем (не блокирует)
# ============================================================================

# Состояния берутся ТОЛЬКО из point_states.py (PointState enum).
# НЕ дублировать! Только алиасы для обратной совместимости.

# Алиасы для обратной совместимости (используются в lc_stage_kt_registry и др.)
POINT_STATE_FINAL = PointState.CONFIRMED.value
POINT_STATE_INTERMEDIATE = (PointState.COMPLETED.value,)
POINT_STATE_INITIAL = (PointState.IN_PROGRESS.value,)
POINT_STATE_CANCELLED = (PointState.CANCELLED.value,)


# Универсальные функции проверки состояния — все используют point_states.py.
# Это гарантирует что мы НЕ используем "похожие" слова, а только точные значения.

def is_point_confirmed(state: str) -> bool:
    """Проверяет что КТ подтверждена согласующим (только 'Подтверждена').

    Делегирует в point_states.ps_is_confirmed.
    """
    return ps_is_confirmed(state)


def is_point_intermediate(state: str) -> bool:
    """Проверяет что КТ выполнена, но НЕ подтверждена (только 'Выполнена').

    Делегирует в point_states.is_completed_but_not_confirmed.
    """
    return state and PointState.from_name(state) == PointState.COMPLETED


def is_point_cancelled(state: str) -> bool:
    """Проверяет что КТ отменена (только 'Отменено')."""
    return ps_is_cancelled(state)


def is_point_completed(state: str) -> bool:
    """Проверяет что КТ закрыта (выполнена ИЛИ подтверждена)."""
    if not state:
        return False
    ps = PointState.from_name(state)
    return ps is not None and ps in (PointState.COMPLETED, PointState.CONFIRMED)


def is_point_initial(state: str) -> bool:
    """Проверяет что КТ ещё не выполнена (только 'В работе')."""
    return ps_is_initial(state)


def get_point_stage_level(state: str) -> int:
    """Возвращает уровень состояния КТ (0=initial, 1=intermediate, 2=final, -1=cancelled).

    Делегирует в point_states.get_state_level.
    """
    return get_state_level(state)

# Канонические статусы КТ (только 4, согласно справочнику MCP)
POINT_STATE_CONFIRMED = "Подтверждена"     # КТ закрыта и согласована
POINT_STATE_COMPLETED = "Выполнена"         # КТ выполнена, но не подтверждена
POINT_STATE_IN_PROGRESS = "В работе"        # КТ в работе (не выполнена)
POINT_STATE_CANCELLED = "Отменено"          # КТ отменена


def is_point_overdue(state: str) -> bool:
    """DEPRECATED. КТ "Просрочено" больше не существует в справочнике MCP.

    Используйте is_point_initial() — КТ может быть в работе и при этом
    иметь просроченный ForecastDate. Само состояние "Просрочено"
    исключено из справочника состояний Point.
    """
    return False


# ============================================================================
# Утилиты
# ============================================================================

def get_stage_index(stage: str) -> Optional[int]:
    """Возвращает индекс стадии в LC_STAGES или None если не найдена."""
    try:
        return LC_STAGES.index(stage)
    except ValueError:
        return None


def get_mandatory_kt_for_stage(stage: str) -> List[str]:
    """Возвращает список обязательных КТ для стадии (только этой стадии)."""
    return MANDATORY_KT_BY_STAGE.get(stage, [])


def get_all_mandatory_kt_until_stage(stage: str) -> List[tuple]:
    """Возвращает ВСЕ обязательные КТ для всех стадий ДО и ВКЛЮЧАЯ указанную.

    Returns:
        Список кортежей [(стадия, кт), ...]
    """
    stage_idx = get_stage_index(stage)
    if stage_idx is None:
        return []

    result = []
    for i in range(stage_idx + 1):
        s = LC_STAGES[i]
        for kt in MANDATORY_KT_BY_STAGE.get(s, []):
            result.append((s, kt))
    return result


def compare_actual_with_expected(
    actual_kt_names: List[str],
    expected_stage: str,
) -> Dict[str, list]:
    """Сравнивает фактические КТ с ожидаемыми для указанной стадии.

    Args:
        actual_kt_names: список названий фактических КТ проекта
        expected_stage: стадия, на которой проект сейчас (из карточки)

    Returns:
        {
            "present": [(стадия, кт), ...],  # обязательные КТ которые ЕСТЬ
            "missing": [(стадия, кт), ...],  # обязательные КТ которых НЕТ
            "expected_stage": ожидаемая_стадия,
        }
    """
    expected = get_all_mandatory_kt_until_stage(expected_stage)
    actual_lower = [kt.lower().strip() for kt in actual_kt_names]

    present = []
    missing = []
    for stage, kt in expected:
        # Проверяем наличие КТ (case-insensitive, по подстроке)
        found = any(kt.lower() in actual_kt for actual_kt in actual_lower)
        if found:
            present.append((stage, kt))
        else:
            missing.append((stage, kt))

    return {
        "present": present,
        "missing": missing,
        "expected_stage": expected_stage,
    }


# ============================================================================
# Эвристики (правила if-then)
# ============================================================================
#
# Три варианта несоответствия данных проекта стадиям ЖЦ:
#
# 1) Не закрыта (просрочена) обязательная КТ, контролирующая переход
#    между стадиями ЖЦ. → стадия ЖЦ не завершилась вовремя, нужно закрыть КТ.
#
# 2) Все КТ данного этапа выполнены, но одна или несколько из них
#    НЕ подтверждены согласующим. → блокировка перехода.
#
# 3) Все КТ данного этапа выполнены и подтверждены, но не была отдана
#    команда на перевод проекта в следующее состояние ЖЦ. → стадия ЖЦ
#    "застряла", нужно перевести.
#
# Дополнительно (для индикатора 6.2):
# 4) Препятствий к переходу нет (все КТ закрыты и подтверждены), но
#    команда на перевод в UI не нажата. → замечание "Не отдана команда
#    на переход в следующую стадию ЖЦ".
#


def heuristic_evaluate(
    actual_stage: str,
    actual_kt_names: List[str],
    kt_with_fact_dates: Optional[List[dict]] = None,
    kt_with_approvers: Optional[List[dict]] = None,
) -> Dict[str, any]:
    """Оценить соответствие стадии ЖЦ фактическому наличию КТ.

    Три варианта несоответствия (по убыванию серьёзности):
    1. КТ просрочена (стадия не завершилась вовремя) → Критическое
    2. КТ выполнена но не подтверждена → Существенное
    3. КТ выполнена и подтверждена, но стадия не переведена → Информационное

    Args:
        actual_stage: стадия из карточки проекта (ActivityPhaseName)
        actual_kt_names: список названий КТ проекта (Name из Point view)
        kt_with_fact_dates: список dict с полями name, FactDate, ForecastDate
                           (для определения просрочки — вариант 1)
        kt_with_approvers: список dict с полями name, ApproverConfirmed
                           (для варианта 2 — не подтверждено)

    Returns:
        {
            "verdict": "Норма" / "Информационное" / "Существенное" / "Критическое",
            "issues": [список замечаний для вложенной таблицы],
            "recommended_stage": рекомендуемая стадия (или None),
            "comparison": {
                "present": [(stage, kt), ...],
                "missing": [(stage, kt), ...],
                "expected_stage": str,
            },
        }
    """
    # Базовое сравнение: какие КТ есть, каких нет
    comparison = compare_actual_with_expected(actual_kt_names, actual_stage)
    issues = []

    # ========================================================================
    # ШАГ 2: Обязательные КТ текущей стадии - проверка создания
    # ========================================================================
    # Если в плане есть хоть одна КТ, но обязательные для текущей стадии
    # не все созданы → СУЩЕСТВЕННОЕ (нарушение правил ведения проекта).
    # Проверяем ТОЛЬКО КТ текущей стадии (не предыдущих/следующих).
    # Есть КТ в календарном плане, но НЕ ВСЕ обязательные КТ для текущей
    # стадии созданы. Это нарушение правил ведения проекта: прежде чем вводить
    # "второстепенные" КТ, нужно задать сроки обязательных.
    #
    # Срабатывает даже если хоть одна обязательная КТ есть, но другие нет.
    # В замечаниях показываем ТОЛЬКО отсутствующие обязательные КТ.
    if actual_stage in MANDATORY_KT_BY_STAGE and actual_kt_names:
        mandatory = MANDATORY_KT_BY_STAGE.get(actual_stage, [])
        if mandatory:
            # Какие обязательные КТ присутствуют
            present_mandatory = set()
            for m in mandatory:
                if any(m.lower() in n.lower() for n in actual_kt_names):
                    present_mandatory.add(m)

            # Шаг 2: НЕ ВСЕ обязательные КТ есть (при наличии других КТ в плане)
            # В замечаниях показываем только отсутствующие
            missing_mandatory = [m for m in mandatory if m not in present_mandatory]
            if missing_mandatory:
                for m in missing_mandatory:
                    issues.append({
                        "type": "mandatory_kt_missing",
                        "kt_name": m,
                        "stage": actual_stage,
                        "severity": "substantial",  # нарушение правил = существенное
                    })

    # ========================================================================
    # ШАГ 3: Обязательная КТ просрочена
    # ========================================================================
    # КТ обязательная + создана + ForecastDate < today + НЕ выполнена.
    # → КРИТИЧЕСКОЕ + "Просрочена обязательная КТ '<X>', N дн."
    # Проверяем ТОЛЬКО КТ текущей стадии.
    # Обязательная КТ просрочена (ForecastDate < today и КТ НЕ выполнена).
    # Это критическое нарушение сроков.
    #
    # КТ считается просроченной если:
    # - она обязательна для текущей стадии (из MANDATORY_KT_BY_STAGE)
    # - НЕ выполнена (нет FactDate)
    # - имеет ForecastDate < today
    #
    # ВАЖНО: "Выполнена" (есть факт.дата, но не подтверждена) — НЕ просрочка.
    # "Подтверждена" — точно НЕ просрочка.
    # Подтверждение согласующим — это ОТДЕЛЬНАЯ проблема (другой шаг).
    #
    # Логика: КТ просрочена если её ещё НЕ начали закрывать (нет факт.даты).
    # Если КТ уже закрыта (факт.дата есть) — она НЕ просрочена, даже если
    # согласующий ещё не подтвердил.
    if kt_with_fact_dates:
        from datetime import datetime, date
        today = datetime.now().date()

        # Получаем список обязательных КТ для текущей стадии
        current_mandatory = set()
        if actual_stage in MANDATORY_KT_BY_STAGE:
            current_mandatory = set(MANDATORY_KT_BY_STAGE[actual_stage])

        # Создаём lookup по имени КТ для быстрого поиска состояния
        kt_state_lookup = {}
        if kt_with_approvers:
            for kt_info in kt_with_approvers:
                kt_state_lookup[kt_info.get("name", "").lower()] = kt_info

        for kt_info in kt_with_fact_dates:
            name = kt_info.get("name", "")
            if not name:
                continue

            # Проверяем что КТ обязательна для текущей стадии
            is_mandatory = any(
                m.lower() in name.lower() or name.lower() in m.lower()
                for m in current_mandatory
            )
            if not is_mandatory:
                continue

            # КТ просрочена ТОЛЬКО если она НЕ выполнена (нет факт.даты).
            # Подтверждение — это отдельный вопрос, не влияет на просрочку.
            # Если КТ "Выполнена" (есть факт.дата) — то она НЕ просрочена.
            # Если КТ "Подтверждена" — точно НЕ просрочена.
            fact_date = None
            for kt_name_lower, kt_state_info in kt_state_lookup.items():
                if kt_name_lower and (kt_name_lower in name.lower() or name.lower() in kt_name_lower):
                    fact_date = kt_state_info.get("FactDate")
                    break

            # КТ просрочена только если нет факт.даты (не выполнена)
            if fact_date:
                continue  # КТ выполнена → не просрочена

            # Проверяем просрочку
            fact = kt_info.get("FactDate")
            forecast = kt_info.get("ForecastDate")
            if not fact and forecast:
                try:
                    if isinstance(forecast, str):
                        fdate = datetime.fromisoformat(forecast.replace("Z", "+00:00")).date()
                    else:
                        fdate = forecast
                    if fdate < today:
                        days_overdue = (today - fdate).days
                        issues.append({
                            "type": "mandatory_kt_overdue",
                            "kt_name": name,
                            "days_overdue": days_overdue,
                            "severity": "critical",
                        })
                except (ValueError, TypeError):
                    pass

    # ========================================================================
    # ШАГ 4: КТ выполнена, но не подтверждена согласующим
    # ========================================================================
    # КТ обязательная + выполнена (есть FactDate) + НЕ подтверждена.
    # → ИНФОРМАЦИОННОЕ + "КТ '<X>' выполнена, но не подтверждена N дн."
    # Проверяем ТОЛЬКО КТ текущей стадии.
    # Обязательная КТ выполнена (есть FactDate), но НЕ подтверждена.
    # Это информационное замечание (не критично, но требует внимания).
    #
    # Условие:
    # - КТ обязательна для текущей стадии (из MANDATORY_KT_BY_STAGE)
    # - КТ существует (создана в календарном плане)
    # - КТ выполнена (есть FactDate)
    # - КТ НЕ подтверждена (состояние != "Подтверждена")
    #
    # В замечании указываем наименование КТ + кол-во дней без подтверждения.
    if kt_with_fact_dates:
        from datetime import datetime, date
        today = datetime.now().date()

        # Получаем список обязательных КТ для текущей стадии
        current_mandatory = set()
        if actual_stage in MANDATORY_KT_BY_STAGE:
            current_mandatory = set(MANDATORY_KT_BY_STAGE[actual_stage])

        # Lookup по имени КТ для быстрого поиска состояния
        kt_state_lookup = {}
        if kt_with_approvers:
            for kt_info in kt_with_approvers:
                kt_state_lookup[kt_info.get("name", "").lower()] = kt_info

        for kt_info in kt_with_fact_dates:
            name = kt_info.get("name", "")
            if not name:
                continue

            # Проверяем что КТ обязательна для текущей стадии
            is_mandatory = any(
                m.lower() in name.lower() or name.lower() in m.lower()
                for m in current_mandatory
            )
            if not is_mandatory:
                continue

            # Проверяем что КТ выполнена (есть FactDate) и НЕ подтверждена
            fact_date = None
            is_confirmed = False
            for kt_name_lower, kt_state_info in kt_state_lookup.items():
                if kt_name_lower and (kt_name_lower in name.lower() or name.lower() in kt_name_lower):
                    fact_date = kt_state_info.get("FactDate")
                    is_confirmed = kt_state_info.get("ApproverConfirmed", False)
                    break

            # Шаг 4: КТ выполнена, но НЕ подтверждена
            if fact_date and not is_confirmed:
                # Считаем сколько дней без подтверждения
                try:
                    if isinstance(fact_date, str):
                        fdate_obj = datetime.fromisoformat(fact_date.replace("Z", "+00:00")).date()
                    else:
                        fdate_obj = fact_date

                    days_unconfirmed = max(0, (today - fdate_obj).days)
                    issues.append({
                        "type": "kt_unconfirmed",
                        "kt_name": name,
                        "days_unconfirmed": days_unconfirmed,
                        "severity": "informational",
                    })
                except (ValueError, TypeError):
                    pass

    # --- Шаг 6 (по логике пользователя, 2026-09-02): ---
    # Все обязательные КТ для ТЕКУЩЕЙ стадии ЖЦ:
    # - созданы (все)
    # - выполнены (все)
    # - подтверждены (все)
    # → но проект НЕ переведён на следующую стадию.
    #
    # Причина: пользователь забыл нажать кнопку перехода в UI.
    # Вердикт: Информационное (забывчивость, не критично).
    #
    # ВАЖНО (по уточнению пользователя):
    # "При этом могут быть созданы обязательные КТ от следующих стадий ЖЦ
    # и какие-то могут быть даже закрыты и подтверждены! Это не имеет значения!
    # Мы идём последовательно по стадиям ЖЦ и обращаем внимание только на
    # то, что относится к ДАННОЙ стадии ЖЦ"
    #
    # То есть Шаг 6 проверяет ТОЛЬКО КТ текущей стадии, не предыдущих/следующих.
    if kt_with_approvers and actual_stage in MANDATORY_KT_BY_STAGE:
        current_mandatory = MANDATORY_KT_BY_STAGE[actual_stage]
        if current_mandatory:
            # Проверяем что ВСЕ обязательные КТ текущей стадии созданы, выполнены, подтверждены
            all_current_present = all(
                any(m.lower() in kt.get("name", "").lower() or kt.get("name", "").lower() in m.lower()
                    for kt in kt_with_approvers)
                for m in current_mandatory
            )
            if all_current_present:
                # Все КТ созданы — проверяем что все выполнены и подтверждены
                all_current_confirmed = all(
                    kt.get("ApproverConfirmed", False) and kt.get("FactDate")
                    for kt in kt_with_approvers
                    for m in current_mandatory
                    if m.lower() in kt.get("name", "").lower() or kt.get("name", "").lower() in m.lower()
                )
                if all_current_confirmed:
                    stage_idx = get_stage_index(actual_stage)
                    if stage_idx is not None and stage_idx < len(LC_STAGES) - 1:
                        # Это последняя стадия (Архив)? Не нужно переходить дальше
                        next_stage = LC_STAGES[stage_idx + 1]
                        issues.append({
                            "type": "stage_not_advanced",
                            "current_stage": actual_stage,
                            "recommended_stage": next_stage,
                            "severity": "informational",
                        })

    # --- Определение общего вердикта ---
    severities = [i["severity"] for i in issues]
    if "critical" in severities:
        verdict = "Критическое"
    elif "substantial" in severities:
        verdict = "Существенное"
    elif "informational" in severities:
        verdict = "Информационное"
    else:
        verdict = "Норма"

    # Рекомендация по стадии (если есть issues)
    recommended_stage = None
    for i in issues:
        if i.get("recommended_stage"):
            recommended_stage = i["recommended_stage"]
            break

    return {
        "verdict": verdict,
        "issues": issues,
        "recommended_stage": recommended_stage,
        "comparison": comparison,
    }
