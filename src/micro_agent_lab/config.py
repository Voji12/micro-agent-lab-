"""Small .env loader; no third-party dependencies or secret printing."""
from __future__ import annotations
import os
from pathlib import Path

def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key.isidentifier():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        os.environ.setdefault(key, value)

def student_config() -> tuple[str, str, str, int, float]:
    load_dotenv()
    url = os.environ.get("STUDENT_BASE_URL", "").strip().rstrip("/")
    model = os.environ.get("STUDENT_MODEL", "").strip()
    if not url or not model:
        raise ValueError("Set STUDENT_BASE_URL and STUDENT_MODEL in .env")
    if not url.startswith(("http://127.0.0.1:", "http://localhost:", "https://")):
        raise ValueError("Only loopback HTTP or HTTPS endpoints are allowed")
    return (url, os.environ.get("STUDENT_API_KEY", ""), model,
            int(os.environ.get("STUDENT_TIMEOUT_SECONDS", "180")),
            float(os.environ.get("STUDENT_TEMPERATURE", "0")))
