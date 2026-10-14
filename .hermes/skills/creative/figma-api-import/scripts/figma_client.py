"""
Figma REST API client.
Auto-loads FIGMA_PERSONAL_ACCESS_TOKEN from ~/.hermes/.env.
"""
import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional


class FigmaClient:
    BASE_URL = "https://api.figma.com"
    API_VERSION = "v1"

    def __init__(self, token: Optional[str] = None):
        self.token = token or self._load_token()
        if not self.token:
            raise ValueError(
                "FIGMA_PERSONAL_ACCESS_TOKEN not found. "
                "Add to ~/.hermes/.env: FIGMA_PERSONAL_ACCESS_TOKEN=***"
            )

    def _load_token(self) -> Optional[str]:
        env_path = Path.home() / ".hermes" / ".env"
        if not env_path.exists():
            return os.environ.get("FIGMA_PERSONAL_ACCESS_TOKEN")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("FIGMA_PERSONAL_ACCESS_TOKEN="):
                    return line.split("=", 1)[1].strip()
        return os.environ.get("FIGMA_PERSONAL_ACCESS_TOKEN")

    def _request(self, endpoint: str, params: Optional[dict] = None,
                method_override: Optional[str] = None,
                json_body: Optional[dict] = None) -> dict:
        url = f"{self.BASE_URL}/{self.API_VERSION}/{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url)
        req.add_header("X-Figma-Token", self.token)
        if method_override:
            req.method = method_override
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            req.add_header("Content-Type", "application/json")
            req.data = data
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {body}") from e

    def create_nodes(self, file_key: str, nodes: list, page_id: Optional[str] = None) -> dict:
        """Create nodes in Figma file. POST /v1/files/{file_key}/nodes"""
        # Если page_id указан, добавляем parent
        if page_id:
            for node in nodes:
                if "parent" not in node:
                    node["parent"] = page_id
        return self._request(
            f"files/{file_key}/nodes",
            method_override="POST",
            json_body={"nodes": nodes}
        )

    def get_me(self) -> dict:
        """Получить информацию о текущем пользователе."""
        return self._request("me")

    def get_file(self, file_key: str) -> dict:
        """Получить полный файл Figma."""
        return self._request(f"files/{file_key}")

    def get_nodes(self, file_key: str, node_ids: list) -> dict:
        """Получить конкретные ноды."""
        ids = ",".join(node_ids)
        return self._request(f"files/{file_key}/nodes", {"ids": ids})

    def get_styles(self, file_key: str) -> dict:
        """Получить стили файла."""
        return self._request(f"files/{file_key}/styles")

    def get_components(self, file_key: str) -> dict:
        """Получить компоненты файла."""
        return self._request(f"files/{file_key}/components")

    def get_component(self, file_key: str, component_key: str) -> dict:
        return self._request(f"components/{component_key}")

    def get_variables(self, file_key: str) -> dict:
        """Получить переменные (Variables API)."""
        return self._request(f"files/{file_key}/variables/local")

    def get_image(self, file_key: str, node_ids: list, fmt: str = "png", scale: int = 2) -> dict:
        """Получить URL для рендера нодов в PNG/SVG/JPG/PDF."""
        ids = ",".join(node_ids)
        return self._request(
            f"images/{file_key}",
            {"ids": ids, "format": fmt, "scale": scale}
        )


def main():
    """CLI: проверка токена."""
    try:
        client = FigmaClient()
        me = client.get_me()
        print(json.dumps({
            "status": "ok",
            "user": {
                "id": me.get("id"),
                "email": me.get("email"),
                "handle": me.get("handle"),
            }
        }, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
