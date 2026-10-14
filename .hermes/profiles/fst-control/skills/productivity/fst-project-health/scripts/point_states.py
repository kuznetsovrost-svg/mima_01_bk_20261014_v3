__version__ = "1.0.19"
"""
point_states.py — УПОРЯДОЧЕННЫЕ состояния КТ (Point) с указанием порядка перехода.

ВАЖНО:
- Это единственный источник истины о состояниях КТ.
- Вся остальная логика (lc_stage_kt_registry.py, project_indicators.py) должна
  импортировать данные ОТСЮДА, а не дублировать хардкод.
- Источник: describe_entity(entityName="Point", show_allowed_values=["ActivityPhaseId"])
- Live-probe 2026-09-02: получено РОВНО 4 состояния.

СМЫСЛ СОСТОЯНИЙ (по логике пользователя):
1. "В работе" — КТ создана, но ещё не выполнена (нет факт.даты)
2. "Выполнена" — факт.дата указана, но согласующий ещё не подтвердил
3. "Подтверждена" — работа по КТ завершена, согласующий подтвердил

+ "Отменено" — КТ отменена (не блокирует переход)

ПОРЯДОК ПЕРЕХОДА (от менее "зрелого" к более):
  В работе (0) → Выполнена (1) → Подтверждена (2)
  Отменено (отдельная ветка, не влияет на порядок)
"""
from enum import Enum
from typing import List, Dict, Set, Optional


# ============================================================================
# Класс PointState — упорядоченные состояния КТ
# ============================================================================

class PointState(str, Enum):
    """Состояния КТ (Point) с упорядоченным уровнем "зрелости".

    Уровень: от 0 (initial) до 2 (final). Cancelled — отдельное состояние.

    Пример:
        >>> state = PointState.from_name("Подтверждена")
        >>> state.level
        2
        >>> PointState.CONFIRMED.is_terminal()
        True
    """
    IN_PROGRESS = "В работе"      # level=0, КТ создана, не выполнена
    COMPLETED = "Выполнена"        # level=1, факт.дата есть, согласующий не подтвердил
    CONFIRMED = "Подтверждена"     # level=2, согласующий подтвердил
    CANCELLED = "Отменено"          # level=-1, КТ отменена

    @property
    def level(self) -> int:
        """Уровень зрелости: 0=initial, 1=intermediate, 2=final, -1=cancelled."""
        return {
            PointState.IN_PROGRESS: 0,
            PointState.COMPLETED: 1,
            PointState.CONFIRMED: 2,
            PointState.CANCELLED: -1,
        }[self]

    @property
    def order(self) -> int:
        """Порядковый номер состояния (для отображения)."""
        return {
            PointState.IN_PROGRESS: 1,
            PointState.COMPLETED: 2,
            PointState.CONFIRMED: 3,
            PointState.CANCELLED: 4,
        }[self]

    def is_initial(self) -> bool:
        """КТ ещё не выполнена (нет факт.даты)."""
        return self == PointState.IN_PROGRESS

    def is_intermediate(self) -> bool:
        """КТ выполнена, но не подтверждена согласующим."""
        return self == PointState.COMPLETED

    def is_confirmed(self) -> bool:
        """КТ подтверждена согласующим (финальное состояние)."""
        return self == PointState.CONFIRMED

    def is_cancelled(self) -> bool:
        """КТ отменена."""
        return self == PointState.CANCELLED

    def blocks_stage_transition(self) -> bool:
        """Блокирует ли КТ переход на следующую стадию ЖЦ.

        Блокирует: IN_PROGRESS, COMPLETED (не подтверждена).
        Не блокирует: CONFIRMED (подтверждена), CANCELLED (отменена).
        """
        return self in (PointState.IN_PROGRESS, PointState.COMPLETED)

    @classmethod
    def from_name(cls, name: str) -> Optional["PointState"]:
        """Преобразует строковое название в PointState (без учёта регистра).

        Returns:
            PointState или None если название не распознано.
        """
        if not name:
            return None
        name_lower = name.lower().strip()
        for state in cls:
            if state.value.lower() == name_lower:
                return state
        return None

    @classmethod
    def all_states(cls) -> List["PointState"]:
        """Возвращает все состояния в порядке возрастания order."""
        return sorted(cls, key=lambda s: s.order)

    @classmethod
    def active_states(cls) -> List["PointState"]:
        """Возвращает только активные (не отменённые) состояния."""
        return [s for s in cls if s != cls.CANCELLED]


# ============================================================================
# Маппинг ID ↔ State (из MCP describe_entity)
# ============================================================================

# Источник: describe_entity(entityName="Point", show_allowed_values=["ActivityPhaseId"])
# Live-probe 2026-09-02
POINT_STATE_IDS: Dict[int, PointState] = {
    10012: PointState.IN_PROGRESS,
    10018: PointState.COMPLETED,
    40031: PointState.CANCELLED,
    40041: PointState.CONFIRMED,
}

# Обратный маппинг: state → ID (для отправки в MCP если нужно)
POINT_STATE_TO_ID: Dict[PointState, int] = {v: k for k, v in POINT_STATE_IDS.items()}


def state_by_id(id: int) -> Optional[PointState]:
    """Возвращает PointState по ID из MCP."""
    return POINT_STATE_IDS.get(id)


def id_by_state(state: PointState) -> Optional[int]:
    """Возвращает ID состояния для отправки в MCP."""
    return POINT_STATE_TO_ID.get(state)


# ============================================================================
# Утилиты для проверки состояний
# ============================================================================

def is_confirmed(state: str) -> bool:
    """Проверяет что КТ подтверждена согласующим."""
    ps = PointState.from_name(state)
    return ps is not None and ps.is_confirmed()


def is_completed_but_not_confirmed(state: str) -> bool:
    """Проверяет что КТ выполнена, но НЕ подтверждена."""
    ps = PointState.from_name(state)
    return ps is not None and ps.is_intermediate()


def is_initial(state: str) -> bool:
    """Проверяет что КТ ещё не выполнена (нет факт.даты)."""
    ps = PointState.from_name(state)
    return ps is not None and ps.is_initial()


def is_cancelled(state: str) -> bool:
    """Проверяет что КТ отменена."""
    ps = PointState.from_name(state)
    return ps is not None and ps.is_cancelled()


def blocks_transition(state: str) -> bool:
    """Блокирует ли КТ переход на следующую стадию ЖЦ."""
    ps = PointState.from_name(state)
    return ps is not None and ps.blocks_stage_transition()


def get_state_level(state: str) -> int:
    """Возвращает уровень зрелости КТ (0/1/2/-1)."""
    ps = PointState.from_name(state)
    if ps is None:
        return -99  # неизвестное состояние
    return ps.level


# ============================================================================
# Цепочка переходов (для UI/log)
# ============================================================================

TRANSITION_CHAIN = (
    PointState.IN_PROGRESS,
    PointState.COMPLETED,
    PointState.CONFIRMED,
)

# Описание переходов
TRANSITION_DESCRIPTIONS = {
    (PointState.IN_PROGRESS, PointState.COMPLETED):
        "Исполнитель указал факт.дату (КТ выполнена, ожидает согласования)",
    (PointState.COMPLETED, PointState.CONFIRMED):
        "Согласующий подтвердил выполнение КТ",
}


# ============================================================================
# Проверки для индикаторов (6.2)
# ============================================================================

def is_mandatory_kt_blocked_transition(
    state: str,
    has_fact_date: bool,
) -> bool:
    """Определяет, блокирует ли обязательная КТ переход на следующую стадию.

    Логика по жизненному циклу:
    - CONFIRMED → не блокирует (КТ подтверждена)
    - COMPLETED → блокирует (есть факт.дата, но согласующий не подтвердил)
    - IN_PROGRESS → блокирует (КТ не выполнена)
    - CANCELLED → не блокирует (КТ отменена)
    - Неизвестное состояние → не блокирует (не можем оценить)

    Args:
        state: название состояния КТ
        has_fact_date: есть ли факт.дата у КТ

    Returns:
        True если КТ блокирует переход на следующую стадию.
    """
    ps = PointState.from_name(state)
    if ps is None:
        return False
    if ps.is_confirmed():
        return False  # Подтверждена — не блокирует
    if ps.is_cancelled():
        return False  # Отменена — не блокирует
    if ps.is_intermediate():
        return True  # Выполнена, но не подтверждена — блокирует
    if ps.is_initial():
        return True  # В работе — блокирует
    return False


if __name__ == "__main__":
    # Тестирование
    print("=== Состояния КТ ===")
    for state in PointState.all_states():
        print(f"  {state.order}. {state.value} (level={state.level})")

    print()
    print("=== Проверка блокировки перехода ===")
    test_states = ["В работе", "Выполнена", "Подтверждена", "Отменено", "Неизвестно"]
    for s in test_states:
        ps = PointState.from_name(s)
        blocks = blocks_transition(s) if ps else None
        print(f"  {s:>15} → blocks={blocks}")
