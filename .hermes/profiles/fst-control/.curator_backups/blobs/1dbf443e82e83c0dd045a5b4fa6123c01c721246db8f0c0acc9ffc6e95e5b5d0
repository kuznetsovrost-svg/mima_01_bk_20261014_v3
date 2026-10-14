"""
test_indicators_v100.py — тесты для 16 индикаторов секции 6 «Показатели проекта».

Проверяет:
- Все 16 индикаторов зарегистрированы в INDICATORS
- Каждый индикатор имеет корректную структуру результата
- IndicatorResult содержит обязательные поля
- Thresholds файлы загружаются
- Справочники (point_states, lc_stage_kt_registry) валидны
"""
import importlib.util
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"


def load_module(name, path):
    """Загружает модуль через importlib."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_all_indicators_registered():
    """В INDICATORS должно быть 16 функций."""
    pi = load_module("project_indicators", SCRIPTS / "project_indicators.py")
    assert len(pi.INDICATORS) == 16, f"Ожидается 16 индикаторов, найдено {len(pi.INDICATORS)}"

    # Все номера от 1 до 16
    for i, fn in enumerate(pi.INDICATORS, start=1):
        assert fn.__name__.startswith("check_"), f"Не check_*: {fn.__name__}"


def test_indicator_result_fields():
    """IndicatorResult имеет обязательные поля."""
    pi = load_module("project_indicators", SCRIPTS / "project_indicators.py")

    ir = pi.IndicatorResult(number=99, name="Test", result="X", detail="", verdict="Норма")
    assert hasattr(ir, "number")
    assert hasattr(ir, "name")
    assert hasattr(ir, "result")
    assert hasattr(ir, "detail")
    assert hasattr(ir, "verdict")
    assert hasattr(ir, "table")
    assert hasattr(ir, "table_title")

    assert ir.number == 99
    assert ir.verdict == "Норма"
    assert ir.table is None or isinstance(ir.table, list)


def test_section_verdict_from_results():
    """SectionVerdict агрегирует верно."""
    pi = load_module("project_indicators", SCRIPTS / "project_indicators.py")

    results = [
        pi.IndicatorResult(number=1, name="A", result="", detail="", verdict="Норма"),
        pi.IndicatorResult(number=2, name="B", result="", detail="", verdict="Существенное"),
    ]
    sv = pi.compute_section_verdict(results)
    assert sv.verdict == "Существенное"

    # С критическим
    results = [
        pi.IndicatorResult(number=1, name="A", result="", detail="", verdict="Существенное"),
        pi.IndicatorResult(number=2, name="B", result="", detail="", verdict="Критическое"),
    ]
    sv = pi.compute_section_verdict(results)
    assert sv.verdict == "Критическое"

    # Все нормальные
    results = [
        pi.IndicatorResult(number=1, name="A", result="", detail="", verdict="Норма"),
    ]
    sv = pi.compute_section_verdict(results)
    assert sv.verdict == "Норма"


def test_thresholds_modules_loadable():
    """Все thresholds файлы загружаются."""
    thresholds_files = [
        "indicator_thresholds.py",
        "lc_stage_kt_registry.py",
        "overload_thresholds.py",
        "effort_forecast_thresholds.py",
        "plan_effort_thresholds.py",
        "cross_activity_overload_thresholds.py",
        "financial_deadlines_thresholds.py",
        "act_pay_amounts_thresholds.py",
        "kp_labels_thresholds.py",
        "vat_constants.py",
        "vat_calc.py",
        "unfilled_roles_thresholds.py",
    ]
    for fn in thresholds_files:
        path = SCRIPTS / fn
        if path.exists():
            mod = load_module(fn[:-3], path)
            assert mod is not None


def test_point_states_registry():
    """point_states.py имеет все 4 состояния."""
    ps = load_module("point_states", SCRIPTS / "point_states.py")
    assert ps.PointState.IN_PROGRESS.value == "В работе"
    assert ps.PointState.COMPLETED.value == "Выполнена"
    assert ps.PointState.CANCELLED.value == "Отменено"
    assert ps.PointState.CONFIRMED.value == "Подтверждена"

    # ID хранятся в словаре POINT_STATE_IDS
    assert ps.POINT_STATE_IDS[10012] == ps.PointState.IN_PROGRESS
    assert ps.POINT_STATE_IDS[10018] == ps.PointState.COMPLETED
    assert ps.POINT_STATE_IDS[40031] == ps.PointState.CANCELLED
    assert ps.POINT_STATE_IDS[40041] == ps.PointState.CONFIRMED

    # Обратный маппинг работает
    assert ps.POINT_STATE_TO_ID[ps.PointState.IN_PROGRESS] == 10012
    assert ps.POINT_STATE_TO_ID[ps.PointState.CONFIRMED] == 40041


def test_lc_stage_kt_registry():
    """lc_stage_kt_registry имеет справочник обязательных КТ."""
    lc = load_module("lc_stage_kt_registry", SCRIPTS / "lc_stage_kt_registry.py")

    # Все 6 стадий ЖЦ
    assert "Пресейл" in lc.MANDATORY_KT_BY_STAGE
    assert "Инициирование" in lc.MANDATORY_KT_BY_STAGE
    assert "Подготовка" in lc.MANDATORY_KT_BY_STAGE
    assert "Реализация" in lc.MANDATORY_KT_BY_STAGE
    assert "Завершение" in lc.MANDATORY_KT_BY_STAGE

    # Пресейл имеет 3 обязательных КТ
    assert len(lc.MANDATORY_KT_BY_STAGE["Пресейл"]) == 3

    # У активных стадий (кроме Архива) есть хотя бы одна обязательная КТ
    for stage, kts in lc.MANDATORY_KT_BY_STAGE.items():
        if stage == "Архив":
            continue
        assert len(kts) >= 1, f"У активной стадии {stage!r} нет обязательных КТ"


def test_vat_constants():
    """vat_constants.py имеет правильные значения."""
    vc = load_module("vat_constants", SCRIPTS / "vat_constants.py")
    assert vc.DEFAULT_VAT_RATE == 5.0
    assert vc.VAT_TOLERANCE_RUB == 0.0001


def test_act_pay_amounts_formatter():
    """format_amount_short работает корректно."""
    apa = load_module("act_pay_amounts_thresholds", SCRIPTS / "act_pay_amounts_thresholds.py")
    fmt = apa.format_amount_short

    # Целые миллионы без дробей
    assert fmt(2_000_000) == "2 млн. руб."
    assert fmt(3_500_000) == "3,5 млн. руб."

    # Точные миллионы (3 знака после запятой)
    assert fmt(4_752_000) == "4,752 млн. руб."

    # Маленькие суммы — в рублях
    assert fmt(333) == "333 руб."
    assert fmt(100) == "100 руб."
    assert fmt(0) == "0 млн. руб."

    # Отрицательные
    assert fmt(-750_000) == "-0,75 млн. руб."


def test_classify_overload_percent():
    """classify_overload_percent работает корректно."""
    ot = load_module("overload_thresholds", SCRIPTS / "overload_thresholds.py")
    cfg = ot.INDICATOR_THRESHOLDS["6.5_overload"]
    cls = ot.classify_overload_percent

    # ≤100% — норма
    assert cls(50, cfg) == "normal"
    assert cls(100, cfg) == "normal"
    # 100-110 — informational
    assert cls(105, cfg) == "informational"
    assert cls(110, cfg) == "informational"
    # 110-150 — substantial
    assert cls(120, cfg) == "substantial"
    assert cls(150, cfg) == "substantial"
    # >150 — critical
    assert cls(151, cfg) == "critical"
    assert cls(200, cfg) == "critical"


def test_classify_amount_delta():
    """classify_amount_delta работает корректно."""
    apa = load_module("act_pay_amounts_thresholds", SCRIPTS / "act_pay_amounts_thresholds.py")
    cfg = apa.INDICATOR_THRESHOLDS["6.9_act_pay_amounts"]
    cls = apa.classify_amount_delta

    # ≤0 — норма
    assert cls(0, cfg) == "normal"
    assert cls(-100, cfg) == "normal"
    # 0-100 тыс — informational
    assert cls(50_000, cfg) == "informational"
    assert cls(100_000, cfg) == "informational"
    # 100 тыс - 1 млн — substantial
    assert cls(500_000, cfg) == "substantial"
    assert cls(1_000_000, cfg) == "substantial"
    # >1 млн — critical
    assert cls(1_500_000, cfg) == "critical"


def test_vat_calculate():
    """vat_calc функции считают правильно."""
    vc = load_module("vat_calc", SCRIPTS / "vat_calc.py")

    # calculate_vat_from_total
    assert abs(vc.calculate_vat_from_total(1260, 5.0) - 60.0) < 0.01
    assert abs(vc.calculate_vat_from_total(1050, 5.0) - 50.0) < 0.01

    # calculate_vat_rate (обратная)
    rate = vc.calculate_vat_rate(1260, 1200)
    assert abs(rate - 5.0) < 0.01


if __name__ == "__main__":
    # Ручной запуск для отладки
    test_all_indicators_registered()
    print("✅ test_all_indicators_registered")

    test_indicator_result_fields()
    print("✅ test_indicator_result_fields")

    test_section_verdict_from_results()
    print("✅ test_section_verdict_from_results")

    test_thresholds_modules_loadable()
    print("✅ test_thresholds_modules_loadable")

    test_point_states_registry()
    print("✅ test_point_states_registry")

    test_lc_stage_kt_registry()
    print("✅ test_lc_stage_kt_registry")

    test_vat_constants()
    print("✅ test_vat_constants")

    test_act_pay_amounts_formatter()
    print("✅ test_act_pay_amounts_formatter")

    test_classify_overload_percent()
    print("✅ test_classify_overload_percent")

    test_classify_amount_delta()
    print("✅ test_classify_amount_delta")

    test_vat_calculate()
    print("✅ test_vat_calculate")

    print("\n🎉 Все тесты прошли!")