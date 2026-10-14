"""
logging_utils.py — утилиты логирования для fst-project-health-from-md-snapshot.

Зеркало scripts/logging_utils.py из fst-project-health-snap-md.
Дубликат нужен, чтобы между скиллами не было cross-import'а.

Философия (2026-09-24):
    Скрипт может — делает.
    Не может — пишет в лог с полным текстом ошибки и кодом.
    На середине никогда не останавливается и не падает.

Каждый запуск = один файл в logs/<ISO-timestamp>.log.

Используется в:
    - fetch_snapshot.py (извлечение MD-слепков из MCP)
    - run.py (обёртка извлечение + сборка HTML)
"""

import base64
import json
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def log_filename(now: datetime) -> str:
    """2026-09-24T13-45-12.log — без ':' (Windows-safe)."""
    return now.strftime("%Y-%m-%dT%H-%M-%S") + ".log"


def log_path(now: datetime) -> Path:
    """Полный путь к файлу лога, лениво создаёт подкаталог."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / log_filename(now)


def decode_jwt_user(token: str) -> dict:
    """Декодирует JWT (без верификации подписи).

    Возвращает {"name": ..., "email": ..., "sub": ...}.
    Никогда не падает; при ошибке возвращает {"name": "n/a", ...}.
    Никогда не обращается к сети.

    PMForesight JWT (2026-09-24):
    - displayname, givenname — короткие ключи для имени.
    - emailaddress и sid — в XML-schema claims (длинные URI).
    - role = "auth" — технический claim, не путаем с ролевой привилегией.
    """
    try:
        head_b64, payload_b64, *_ = token.split(".")
        padded = payload_b64 + "=" * ((4 - len(payload_b64) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        name = (
            payload.get("displayname")
            or payload.get("name")
            or payload.get("givenname")
            or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")
            or "n/a"
        )
        email = (
            payload.get("email")
            or payload.get("emailaddress")
            or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
            or "n/a"
        )
        sub = (
            payload.get("sub")
            or payload.get("UserId")
            or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier")
            or "n/a"
        )
        return {
            "name": name,
            "email": email,
            "sub": str(sub),
            "issuer": payload.get("iss", "n/a"),
            "_user_id": payload.get("UserId"),
        }
    except Exception as e:
        return {
            "name": "n/a",
            "email": "n/a",
            "sub": "n/a",
            "_decode_error": f"{type(e).__name__}: {e}",
        }


def get_user_role_via_mcp(sid_func) -> str:
    """Best-effort: получает роль пользователя из MCP.

    PMForesight MCP через `get_user_profile` возвращает профиль БЕЗ
    явных прав/ролей. Записываем найденное для диагностики.
    При ошибке (MCP лежит / метод недоступен) — 'n/a (...)'.
    """
    try:
        import requests
        from pathlib import Path as _P
        env_p = _P.home() / ".hermes/profiles/fst-control/.env"
        token = ""
        if env_p.exists():
            for line in env_p.read_text(encoding="utf-8").splitlines():
                if line.startswith("PMP_TOKEN"):
                    token = line.split("=", 1)[1].strip().strip("'\"")

        sid = sid_func()
        url = "https://ppreplica.hera.pmpractice.ru/mcp"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": sid,
        }
        r = requests.post(
            url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": "get_user_profile", "arguments": {}}},
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        body = r.content.decode("utf-8", errors="replace")
        for line in body.splitlines():
            if line.startswith("data: "):
                envelope = json.loads(line[6:])
                result = envelope.get("result", {})
                if result.get("isError"):
                    return f"n/a (get_user_profile error: {result.get('content', [{}])[0].get('text', '<no msg>')[:80]})"
                text = result.get("content", [{}])[0].get("text", "{}")
                data = json.loads(text)
                keys = sorted(data.keys())[:6]
                return f"n/a (PMForesight profile fields: {keys}; no role/permissions exposed)"
        return "n/a (no data line in SSE)"
    except Exception as e:
        return f"n/a ({type(e).__name__}: {str(e)[:80]})"


class RunLogger:
    """Минимальный логгер для извлечения MD и/или сборки HTML.

    Использование:
        logger = RunLogger()
        logger.log_header({...})
        for code in projects:
            ...
            logger.log_project("504-595", "ok", local_path=Path(...), snapshot_ts=...)
            ...
            logger.log_project("503-152", "not_found", error={...})
        logger.log_trailer({...})    # в finally:
    """

    def __init__(self, now: datetime | None = None, *, enabled: bool = True):
        self.now = now or datetime.now()
        self.path = log_path(self.now) if enabled else None
        self._fp = open(self.path, "w", encoding="utf-8") if enabled else None
        self._results = []

    @property
    def log_file(self) -> Path:
        return self.path

    def _write(self, line: str = "") -> None:
        if self._fp is None:
            return  # no-op (enabled=False)
        if line:
            self._fp.write(line)
            if not line.endswith("\n"):
                self._fp.write("\n")
        self._fp.flush()

    def log_header(self, *, version: str, token_user: dict, role: str,
                    action: str, projects_in_run: list, args_summary: str) -> None:
        """action: 'fetch' (только извлечение MD), 'html' (только HTML), 'fetch+html'
        args_summary: краткое описание аргументов (например, '--codes 504-595 999-FAKE-XXX --last')
        """
        self._write(f"=== fst-project-health-from-md-snapshot v{version} run log ===")
        self._write(f"Started at:           {self.now.isoformat()}")
        self._write(f"Caller account:       {token_user.get('name')} <{token_user.get('email')}> (sub={token_user.get('sub')})")
        self._write(f"Caller role (MCP):    {role}")
        self._write(f"Action:               {action}")
        self._write(f"Args:                 {args_summary}")
        self._write(f"Projects in run:      {projects_in_run}")
        self._write("─" * 80)

    def log_project(self, code: str, status: str,
                    *, local_path: Path | None = None,
                    snapshot_ts: str | None = None,
                    html_path: Path | None = None,
                    physical_id: str | None = None,
                    error: dict | None = None,
                    duration_ms: float = 0.0) -> None:
        """status: 'ok' | 'not_found' | 'fetch_error' | 'read_error' |
                   'html_ok' | 'html_error' | 'no_snapshots' | 'permission_denied'

        error: dict с полями {type, message, http_code, raw}
        """
        sym = "✓" if status in ("ok", "html_ok") else "✗"
        parts = [f"  {sym} {code}"]
        parts.append(f"— {status}")
        if physical_id:
            parts.append(f"— physicalFileId={physical_id}")
        if local_path:
            parts.append(f"— file={local_path.name}")
        if snapshot_ts:
            parts.append(f"— snapshot_ts={snapshot_ts}")
        if html_path:
            parts.append(f"— html={html_path.name}")
        if duration_ms:
            parts.append(f"— {duration_ms/1000:.2f} s")
        self._write(" ".join(parts))

        if error:
            err_type = error.get("type", "n/a")
            err_msg = error.get("message", str(error))
            err_code = error.get("http_code")
            err_raw = error.get("raw")
            self._write(f"      type:       {err_type}")
            if err_code is not None:
                self._write(f"      http_code:  {err_code}")
            self._write(f"      message:    {err_msg[:300]}")
            if err_raw:
                self._write(f"      raw[:300]:  {err_raw[:300]}")

        self._results.append({"code": code, "status": status, "ok": status in ("ok", "html_ok")})

    def log_trailer(self, *, total_ms: float | None = None) -> None:
        ok = sum(1 for r in self._results if r["ok"])
        fail = len(self._results) - ok
        self._write("─" * 80)
        self._write(f"Total: {len(self._results)} projects, {ok} ok, {fail} fail")
        if total_ms is not None:
            self._write(f"Total duration: {total_ms/1000:.2f} s")
        self._write(f"Finished at: {datetime.now().isoformat()}")
        self._write("=== END LOG ===")

    def close(self) -> None:
        if self._fp is None:
            return
        try:
            self._fp.close()
        except Exception:
            pass
