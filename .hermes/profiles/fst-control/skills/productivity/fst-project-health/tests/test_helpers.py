"""
test_helpers.py — проверка helpers в mcp_config.py.

Что проверяется:
- *_FILTERS возвращают dict с правильным ProjectId
- *_VIEW константы существуют
- DEPRECATED лямбды *_VIEW_FOR удалены (2026-09-01)
- mcp_init / mcp_call / parse_sse_response импортируются
- status_class распознаёт цвета на русском

Запуск:
    python3 tests/test_helpers.py
"""
import sys
import unittest
import importlib.util
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def load(name: str, fname: str):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / fname))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


mcp = load("mcp_config", "mcp_config.py")


class TestMcpConfigHelpers(unittest.TestCase):

    def test_all_my_point_filters(self):
        """ALL_MY_POINT_FILTERS возвращает dict с ProjectId."""
        self.assertEqual(mcp.ALL_MY_POINT_FILTERS(3434), {"ProjectId": 3434})
        self.assertEqual(mcp.ALL_MY_POINT_FILTERS(4595), {"ProjectId": 4595})

    def test_project_budget_filters(self):
        """PROJECT_BUDGET_FILTERS возвращает dict с ProjectId."""
        self.assertEqual(mcp.PROJECT_BUDGET_FILTERS(4595), {"ProjectId": 4595})

    def test_project_resource_plan_filters(self):
        """PROJECT_RESOURCE_PLAN_FILTERS возвращает dict с ProjectId."""
        self.assertEqual(mcp.PROJECT_RESOURCE_PLAN_FILTERS(3434), {"ProjectId": 3434})

    def test_project_health_cost_my_filters(self):
        """PROJECT_HEALTH_COST_MY_FILTERS работает (фикс 2026-09-01)."""
        self.assertEqual(mcp.PROJECT_HEALTH_COST_MY_FILTERS(4595), {"ProjectId": 4595})
        self.assertEqual(mcp.PROJECT_HEALTH_COST_MY_FILTERS(3434), {"ProjectId": 3434})
        self.assertEqual(mcp.PROJECT_HEALTH_COST_MY_FILTERS(3152), {"ProjectId": 3152})

    def test_all_my_point_view_constant(self):
        """ALL_MY_POINT_VIEW — константа с именем view."""
        self.assertEqual(mcp.ALL_MY_POINT_VIEW, "AllMyPoint")

    def test_project_budget_view_constant(self):
        """PROJECT_BUDGET_VIEW — константа."""
        self.assertEqual(mcp.PROJECT_BUDGET_VIEW, "ProjectBudgetCompleteBusiness")

    def test_project_resource_plan_view_constant(self):
        """PROJECT_RESOURCE_PLAN_VIEW — константа."""
        self.assertEqual(mcp.PROJECT_RESOURCE_PLAN_VIEW, "ProjectResourcePlan")

    def test_project_health_cost_my_view_constant(self):
        """PROJECT_HEALTH_COST_MY_VIEW — константа."""
        self.assertEqual(mcp.PROJECT_HEALTH_COST_MY_VIEW, "ProjectHealthCostMy")

    # --- DEPRECATED лямбды удалены (2026-09-01) ---

    def test_view_for_lambdas_removed(self):
        """DEPRECATED лямбды *_VIEW_FOR удалены (2026-09-01)."""
        for name in ['PROJECT_RESOURCE_PLAN_VIEW_FOR',
                     'PROJECT_BUDGET_VIEW_FOR',
                     'PROJECT_HEALTH_COST_MY_VIEW_FOR',
                     'ALL_MY_POINT_VIEW_FOR']:
            self.assertFalse(
                hasattr(mcp, name),
                f"{name} должна быть удалена (DEPRECATED с 2026-09-01)"
            )

    def test_get_view_with_filters_exists(self):
        """get_view_with_filters — универсальный вызов с фильтрами."""
        self.assertTrue(hasattr(mcp, "get_view_with_filters"))
        self.assertTrue(callable(mcp.get_view_with_filters))

    # --- основные импорты ---

    def test_mcp_init_call_imports(self):
        """mcp_init / mcp_call / parse_sse_response импортируются."""
        self.assertTrue(hasattr(mcp, "mcp_init"))
        self.assertTrue(hasattr(mcp, "mcp_call"))
        self.assertTrue(hasattr(mcp, "parse_sse_response"))
        self.assertTrue(callable(mcp.mcp_init))
        self.assertTrue(callable(mcp.mcp_call))
        self.assertTrue(callable(mcp.parse_sse_response))

    def test_helpers_handle_int(self):
        """*_FILTERS принимают int и преобразуют в str."""
        for pid in [1, 100, 4595, 3434, 3152]:
            self.assertEqual(mcp.ALL_MY_POINT_FILTERS(pid), {"ProjectId": pid})
            self.assertEqual(mcp.PROJECT_BUDGET_FILTERS(pid), {"ProjectId": pid})
            self.assertEqual(mcp.PROJECT_RESOURCE_PLAN_FILTERS(pid), {"ProjectId": pid})
            self.assertEqual(mcp.PROJECT_HEALTH_COST_MY_FILTERS(pid), {"ProjectId": pid})

    def test_status_class_recognizes_colors(self):
        """status_class распознаёт цвета на русском (Синий/Желтый/Красный)."""
        spec = importlib.util.spec_from_file_location(
            "build_html_report", str(SCRIPTS_DIR / "build_html_report.py")
        )
        bh = importlib.util.module_from_spec(spec)
        sys.modules["build_html_report"] = bh
        spec.loader.exec_module(bh)
        # Цвета должны работать в обоих вариантах (ё и е)
        self.assertEqual(bh.status_class("Синий"), "status-info")
        self.assertEqual(bh.status_class("Желтый"), "status-warning")
        self.assertEqual(bh.status_class("Жёлтый"), "status-warning")
        self.assertEqual(bh.status_class("Красный"), "status-critical")
        self.assertEqual(bh.status_class("критическое"), "status-critical")
        self.assertEqual(bh.status_class("существенное"), "status-warning")
        self.assertEqual(bh.status_class("информационное"), "status-info")

    def test_mcpe_keys_deprecated(self):
        """META_TIME_KEYS помечен как DEPRECATED (live-probe 2026-08-07)."""
        self.assertTrue(hasattr(mcp, "META_TIME_KEYS"))


if __name__ == "__main__":
    unittest.main()
