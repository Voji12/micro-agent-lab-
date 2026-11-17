from __future__ import annotations
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Step:
    id: str
    objective: str
    files: list[str]
    instructions: str
    checks: list[list[str]]
    max_attempts: int = 2

    @classmethod
    def parse(cls, data: dict) -> "Step":
        required = ("id", "objective", "files", "instructions", "checks")
        if any(k not in data for k in required):
            raise ValueError(f"Step missing required fields: {required}")
        if not isinstance(data["files"], list) or not isinstance(data["checks"], list):
            raise ValueError("files and checks must be lists")
        if not all(isinstance(cmd, list) and cmd and all(isinstance(s, str) for s in cmd) for cmd in data["checks"]):
            raise ValueError("checks must be nonempty argv arrays")
        return cls(**data)

def load_plan(path: Path) -> list[Step]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    steps = [Step.parse(s) for s in raw["steps"]]
    ids = [s.id for s in steps]
    if len(ids) != len(set(ids)):
        raise ValueError("Step ids must be unique")
    return steps

def record_jsonl(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

def run_checks(step: Step, cwd: Path, log: Path, *, timeout: int = 180) -> bool:
    """Run trusted plan commands only. Never execute unreviewed plans."""
    success = True
    for argv in step.checks:
        start = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
            entry = {"step": step.id, "command": argv, "exit_code": result.returncode,
                     "seconds": round(time.monotonic()-start, 3), "stdout": result.stdout[-4000:],
                     "stderr": result.stderr[-4000:]}
            success &= result.returncode == 0
        except (subprocess.TimeoutExpired, OSError) as exc:
            entry = {"step": step.id, "command": argv, "exit_code": None,
                     "seconds": round(time.monotonic()-start, 3), "error": str(exc)}
            success = False
        record_jsonl(log, entry)
        if not success:
            break
    return success

def format_prompt(step: Step, lessons: list[dict]) -> str:
    rules = "\n".join(f"- {x['lesson']}" for x in lessons if x.get("verified") is True and x.get("lesson")) or "- None yet"
    return (f"You are a coding student. Implement ONLY step {step.id}.\n"
            f"Objective: {step.objective}\nAllowed files: {', '.join(step.files)}\n"
            f"Instructions:\n{step.instructions}\nRelevant verified lessons:\n{rules}\n"
            "Do not change unrelated files. Do not invent external APIs. "
            "Explain the changes and any tests you could not run.\n")

def load_lessons(path: Path, *, limit: int = 10) -> list[dict]:
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in records if r.get("verified") is True][-limit:]
