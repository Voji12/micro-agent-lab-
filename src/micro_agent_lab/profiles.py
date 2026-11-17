"""Select inference profile without copying secrets into logs."""
from __future__ import annotations
import os
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .config import load_dotenv

PROFILES = {
    "notebook": ("NOTEBOOK", "UNSLOTH"),
    "shadow": ("SHADOW", "UNSLOTH"),
    "runpod": ("RUNPOD",),
}

def select_profile(name: str) -> dict:
    load_dotenv()
    if name not in PROFILES:
        raise ValueError(f"Unknown profile {name!r}")
    prefixes = PROFILES[name]
    def get(suffix: str, fallback: str = "") -> str:
        for prefix in prefixes:
            value = os.environ.get(prefix + "_" + suffix, "").strip()
            if value:
                return value
        return fallback
    base = get("BASE_URL")
    key = get("API_KEY")
    model = get("MODEL")
    if name == "runpod":
        base = get("INFERENCE_BASE_URL", base)
        key = get("INFERENCE_API_KEY", key)
    if not base and name == "notebook":
        base = "http://127.0.0.1:8888/v1"
    if not base and name == "shadow":
        raise ValueError("SHADOW_BASE_URL missing")
    if not model:
        raise ValueError(f"{name.upper()}_MODEL missing")
    if base:
        os.environ["STUDENT_BASE_URL"] = base
    os.environ["STUDENT_API_KEY"] = key
    os.environ["STUDENT_MODEL"] = model
    return {"profile": name, "base_url": base, "model": model, "has_key": bool(key)}

def probe_profile(name: str) -> dict:
    info = select_profile(name)
    base = info["base_url"].rstrip("/")
    if not base:
        raise ValueError("Profile has no base URL")
    if not base.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
        raise ValueError("Use HTTPS or localhost; for remote Tailscale use HTTPS proxy")
    headers = {}
    if os.environ.get("STUDENT_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["STUDENT_API_KEY"]
    req = Request(base + "/models", headers=headers)
    try:
        with urlopen(req, timeout=15) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Model API HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("Model endpoint unreachable") from exc
    ids = [item.get("id", "") for item in data.get("data", []) if isinstance(item, dict)]
    return {**info, "available_models": ids, "model_available": info["model"] in ids}
