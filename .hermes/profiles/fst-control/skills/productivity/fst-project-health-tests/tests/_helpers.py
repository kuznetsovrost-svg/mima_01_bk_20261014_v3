"""
_helpers.py — общие утилиты для всех тестов.

Содержит:
    - constants: пути к скиллам семейства, MCP URL, documentId
    - colored print: green/yellow/red (как в основных скриптах)
    - skip(): «пропуск» с объяснением (без падения exit code)
    - fail()/ok(): маркеры для раннера
    - measure_ms(): замер времени с возвратом ms
    - sha256_file(): хеш файла
"""

import hashlib
import time
from pathlib import Path

# --- Конфигурация ----------------------------------------------------------

SKILLS_DIR = Path("/root/.hermes/profiles/fst-control/skills/productivity")

SKILL_HEALTH = SKILLS_DIR / "fst-project-health"
SKILL_HEALTH_SNAP_MD = SKILLS_DIR / "fst-project-health-snap-md"
SKILL_HEALTH_FROM_MD_SNAPSHOT = SKILLS_DIR / "fst-project-health-from-md-snapshot"

MCP_URL = "https://ppreplica.hera.pmpractice.ru/mcp"
DOCUMENT_ID_AI = 70139
ENTITY_NAME = "Project"

CACHE_DIR = Path.home() / ".hermes/profiles/fst-control/cache/snapshots"

# Лог последнего прогона тестов.
TESTS_LOG = Path(__file__).resolve().parent.parent / "logs" / "tests.log"

# --- ANSI цвета ------------------------------------------------------------

def _c(code: int, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"

def green(t): return _c(32, t)
def yellow(t): return _c(33, t)
def red(t): return _c(31, t)
def bold(t): return _c(1, t)
def cyan(t): return _c(36, t)

# --- Маркеры ---------------------------------------------------------------

def ok(msg: str) -> str:
    return f"{green('✓')} {msg}"

def fail(msg: str) -> str:
    return f"{red('✗')} {msg}"

def skip_msg(msg: str) -> str:
    return f"{yellow('⚠ SKIP')} {msg}"

def info(msg: str) -> str:
    return f"{cyan('ℹ')} {msg}"


# --- Утилиты ---------------------------------------------------------------

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class measure_ms:
    """Контекстный менеджер для замера времени в ms."""

    def __init__(self):
        self.ms = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self._t0) * 1000


def fmt_ms(ms: float) -> str:
    if ms >= 1000:
        return f"{ms/1000:.2f} s"
    return f"{ms:.0f} ms"


# --- Запись в tests.log ---------------------------------------------------

def log_to_file(line: str) -> None:
    """Дописывает строку в tests.log (используется раннером)."""
    TESTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TESTS_LOG.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def log_section(title: str) -> None:
    """Заголовок секции в tests.log."""
    log_to_file("")
    log_to_file(f"=== {title} ===")
