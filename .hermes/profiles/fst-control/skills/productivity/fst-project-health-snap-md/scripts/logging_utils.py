"""
logging_utils.py — утилиты логирования для fst-project-health-snap-md.

Философия (2026-09-24):
    Скрипт может — делает.
    Не может — пишет в лог с полным текстом ошибки и кодом.
    На середине никогда не останавливается и не падает.

Каждый запуск = один файл в logs/<ISO-timestamp>.log.
Имя файла вычисляется в момент старта main() и используется
для всех записей.

Используется в:
    - run_snap_md.py (генерация слепков)

Зеркальная копия есть в fst-project-health-from-md-snapshot/scripts/.
"""

import base64
import json
import time
from datetime import datetime
from pathlib import Path

# Куда писать логи — подкаталог logs/ рядом со скиллом.
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def log_filename(now: datetime) -> str:
    """2026-09-24T13-45-12.log — без ':' (Windows-safe + удобно)."""
    return now.strftime("%Y-%m-%dT%H-%M-%S") + ".log"


def log_path(now: datetime) -> Path:
    """Полный путь к файлу лога, лениво создаёт подкаталог."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / log_filename(now)


def decode_jwt_user(token: str) -> dict:
    """Декодирует JWT (без верификации подписи — наш сервер верифицирует на своей стороне).

    Возвращает {"name": ..., "email": ..., "sub": ...} если есть в payload.
    Наш токен — JWT с HMAC/HS256, payload это base64(JSON) между первыми двумя '.'.

    Заметки про PMForesight JWT (2026-09-24):
    - displayname и givenname = "Кузнецов Ростислав Владимирович" (camelCase).
    - emailaddress и sid лежат в XML-schema claims (длинные URI).
    - role = "auth" — это технический claim, НЕ ролевая привилегия.
    - iss = "PMPractice.Foresight".

    Гарантия: никогда не падает; при ошибке декодирования возвращает {"name": "n/a", "_decode_error": ...}.
    Никогда не обращается к сети.
    """
    try:
        head_b64, payload_b64, *_ = token.split(".")
        padded = payload_b64 + "=" * ((4 - len(payload_b64) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))

        # Имя в разных полях (в порядке предпочтения)
        name = (
            payload.get("displayname")
            or payload.get("name")
            or payload.get("givenname")
            or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")
            or "n/a"
        )
        # Email
        email = (
            payload.get("email")
            or payload.get("emailaddress")
            or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
            or "n/a"
        )
        # Subject (идентификатор пользователя)
        sub = (
            payload.get("sub")
            or payload.get("UserId")
            or payload.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier")
            or "n/a"
        )
        # Технический claim role ("auth" / "user" / etc) — НЕ путаем с ролевой привилегией
        # в MCP. Используем только для диагностики.
        auth_role = payload.get("http://schemas.microsoft.com/ws/2008/06/identity/claims/role")

        return {
            "name": name,
            "email": email,
            "sub": str(sub),
            "issuer": payload.get("iss", "n/a"),
            "auth_role": auth_role,  # технический, отличаем от role из MCP
            "_user_id": payload.get("UserId"),
        }
    except Exception as e:
        return {
            "name": "n/a",
            "email": "n/a",
            "sub": "n/a",
            "_decode_error": f"{type(e).__name__}: {e}",
        }


def get_user_role_via_mcp(sid_func, role: str = "ProjectManager") -> str:
    """Получает роль пользователя из MCP (если метод доступен).

    sid_func: callable() -> str   возвращает mcp-session-id
    role:    текст, который вернём при ошибке (по умолчанию "ProjectManager"
             в духе нашей системы; реальная роль зависит от MCP).

    Если MCP лежит или метод не реализован — возвращает 'n/a'.

    Замечание (2026-09-24): PMForesight MCP через `get_user_profile`
    возвращает {Id, Account, FullName, Name, Phone}, но НЕ возвращает
    явных прав/ролей. Этот метод — best-effort; пишем всё что нашли,
    чтобы лог был информативным, и помечаем отсутствие.
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
                # PMForesight профиль: нет явной роли.
                # Записываем ключи, чтобы лог был информативным.
                keys = sorted(data.keys())[:6]
                return f"n/a (PMForesight profile fields: {keys}; no role/permissions exposed)"
        return "n/a (no data line in SSE)"
    except Exception as e:
        return f"n/a ({type(e).__name__}: {str(e)[:80]})"


class RunLogger:
    """Минимальный логгер, синхронно пишет в файл.

    Использование:
        logger = RunLogger()
        logger.log_header({
            "version": "1.0.19",
            "token": PMP_TOKEN,
            "sid_func": lambda: sid,
            "projects_in_script": ["504-595", ...],
            "projects_in_run": [...],
        })
        for code in projects:
            ...
            logger.log_project("504-595", "ok", file_id=206000, duration_ms=27432)
            ...
            logger.log_project("503-152", "permission_denied", error={"type": ..., "msg": ...})
        logger.log_trailer({"total_ms": ...})
        # log_trailer() вызывается в finally:
    """

    def __init__(self, now: datetime | None = None, *, enabled: bool = True):
        self.now = now or datetime.now()
        self.path = log_path(self.now) if enabled else None
        # Открываем сразу (write-mode) — держим хэндл для flush().
        # Если enabled=False — файл не открывается, все методы log_* становятся no-op.
        self._fp = open(self.path, "w", encoding="utf-8") if enabled else None
        self._results = []
        # Флаг для удобства — вызывающий код может проверять `if logger:`,
        # но может и не проверять (методы безопасны при None/_fp).
        self.enabled = enabled

    @property
    def log_file(self) -> Path:
        return self.path

    def _write(self, line: str = "") -> None:
        if self._fp is None:
            return  # no-op режим (enabled=False)
        if line:
            self._fp.write(line)
            if not line.endswith("\n"):
                self._fp.write("\n")
        self._fp.flush()  # важно: при краше хотим видеть всё, что есть

    def log_header(self, *, version: str, token_user: dict,
                    role: str, projects_in_script: list,
                    projects_in_run: list, mode: str) -> None:
        self._write(f"=== fst-project-health-snap-md v{version} run log ===")
        self._write(f"Started at:           {self.now.isoformat()}")
        self._write(f"Caller account:       {token_user.get('name')} <{token_user.get('email')}> (sub={token_user.get('sub')})")
        self._write(f"Caller role (MCP):    {role}")
        self._write(f"Mode:                 {mode}")
        self._write(f"Projects in script:   {projects_in_script}")
        self._write(f"Projects in run:      {projects_in_run}")
        self._write("─" * 80)

    def log_project(self, code: str, status: str,
                    *, file_id: int | None = None,
                    file_name: str | None = None,
                    error: dict | None = None,
                    duration_ms: float = 0.0) -> None:
        """status: 'ok' | 'permission_denied' | 'not_found' | 'upload_error' | 'exception' | 'snapshot_error'

        error: dict с полями {type, message, http_code, raw (опционально)}
        """
        sym = "✓" if status == "ok" else "✗"
        parts = [f"  {sym} {code}"]
        parts.append(f"— {status}")
        if file_id is not None:
            parts.append(f"— FileId={file_id}")
        if file_name:
            parts.append(f"— file={file_name}")
        if duration_ms:
            parts.append(f"— {duration_ms/1000:.2f} s")
        self._write(" ".join(parts))

        # Если ошибка — пишем полный текст ниже
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

        # Запоминаем для trailer
        self._results.append({"code": code, "status": status, "ok": status == "ok"})

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
