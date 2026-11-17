"""OpenAI-compatible student API client using Python standard library."""
from __future__ import annotations
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from .config import student_config

SYSTEM = """You are a careful coding student. Return ONLY a JSON object:
{"files":[{"path":"relative/allowed/path","content":"complete UTF-8 file content"}]}
Write complete files, not patches. Never return shell commands, markdown, secrets or unrelated files.
If you cannot solve the task, return {"files":[]}."""

def completion(prompt: str) -> tuple[str, dict]:
    base, key, model, timeout, temperature = student_config()
    payload = json.dumps({"model": model, "temperature": temperature,
                          "messages": [{"role": "system", "content": SYSTEM},
                                       {"role": "user", "content": prompt}]}).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = Request(f"{base}/chat/completions", data=payload, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Model API HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Model API unavailable: {exc.reason}") from exc
    choice = data["choices"][0]["message"]["content"]
    if isinstance(choice, list):
        choice = "".join(x.get("text", "") for x in choice if isinstance(x, dict))
    if not isinstance(choice, str):
        raise ValueError("Model returned no text content")
    return choice, data.get("usage") or {}

def decode_files(message: str) -> list[dict[str, str]]:
    text = message.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    obj = json.loads(text)
    files = obj["files"]
    if not isinstance(files, list):
        raise ValueError("files must be a list")
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("content"), str):
            raise ValueError("Each file needs path and complete text content")
    return files
