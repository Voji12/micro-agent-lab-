"""Isolated microtask runner. Run only in a disposable, trusted workspace."""
from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path, PurePosixPath
from .core import Step, format_prompt, load_lessons, load_plan, record_jsonl, run_checks
from .provider import completion, decode_files

MAX_FILE_BYTES = 100_000
MAX_CONTEXT_BYTES = 35_000

def safe_path(workspace: Path, relative: str, allowed: set[str]) -> Path:
    posix = PurePosixPath(relative)
    if relative not in allowed or posix.is_absolute() or ".." in posix.parts or "\\" in relative or not relative or posix.parts[0] == ".":
        raise ValueError(f"Disallowed path: {relative!r}")
    root = workspace.resolve(strict=True)
    candidate = root.joinpath(*posix.parts)
    if not candidate.resolve().is_relative_to(root):
        raise ValueError(f"Path escapes workspace: {relative!r}")
    return candidate

def snapshots(step: Step, workspace: Path) -> dict[str, str | None]:
    before = {}
    for relative in step.files:
        path = safe_path(workspace, relative, set(step.files))
        if path.exists() and not path.is_file():
            raise ValueError(f"Not a regular file: {relative}")
        before[relative] = path.read_text(encoding="utf-8") if path.exists() else None
    return before

def apply_files(step: Step, workspace: Path, files: list[dict[str, str]]) -> None:
    if not files:
        raise ValueError("Model returned no files")
    if len(files) != len({f["path"] for f in files}):
        raise ValueError("Duplicate file path")
    checked = []
    for item in files:
        path = safe_path(workspace, item["path"], set(step.files))
        data = item["content"].encode("utf-8")
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("Generated file exceeds size limit")
        checked.append((path, item["content"]))
    for path, content in checked:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

def restore(step: Step, workspace: Path, before: dict[str, str | None]) -> None:
    for relative, content in before.items():
        path = safe_path(workspace, relative, set(step.files))
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

def build_context(step: Step, workspace: Path) -> str:
    sections = []
    total = 0
    for relative in step.files:
        path = safe_path(workspace, relative, set(step.files))
        content = path.read_text(encoding="utf-8") if path.is_file() else "(file does not exist)"
        size = len(content.encode("utf-8"))
        total += size
        if total > MAX_CONTEXT_BYTES:
            raise ValueError("Context exceeds limit; split task further")
        sections.append(f"FILE {relative}:\n{content}")
    return "\n\n".join(sections)

def execute(plan: Path, workspace: Path, run_dir: Path, lessons_path: Path, *, allow_checks: bool) -> dict:
    if not allow_checks:
        raise ValueError("Explicit --allow-checks required: plans execute subprocesses")
    workspace = workspace.resolve(strict=True)
    if not workspace.is_dir() or workspace == Path.cwd().resolve():
        raise ValueError("Workspace must exist and differ from runner working directory")
    run_dir.mkdir(parents=True, exist_ok=True)
    if run_dir.resolve().is_relative_to(workspace):
        raise ValueError("Run logs must be outside student workspace")
    steps = load_plan(plan)
    results = []
    for step in steps:
        before = snapshots(step, workspace)
        passed = False
        last_error = ""
        for attempt in range(1, min(step.max_attempts, 2) + 1):
            started = time.monotonic()
            usage = {}
            changed = []
            try:
                prompt = format_prompt(step, load_lessons(lessons_path))
                prompt += "\nCURRENT ALLOWED FILE CONTENTS:\n" + build_context(step, workspace)
                if last_error:
                    prompt += "\nPREVIOUS ATTEMPT FAILED. Fix this error:\n" + last_error[-2500:]
                response, usage = completion(prompt)
                changes = decode_files(response)
                apply_files(step, workspace, changes)
                changed = [x["path"] for x in changes]
                passed = run_checks(step, workspace, run_dir / "checks.jsonl")
                if not passed:
                    lines = (run_dir / "checks.jsonl").read_text(encoding="utf-8").splitlines()
                    last_error = lines[-1][-2500:] if lines else "Check failed"
            except (ValueError, RuntimeError, OSError, KeyError, json.JSONDecodeError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                passed = False
            record_jsonl(run_dir / "attempts.jsonl", {
                "step": step.id, "attempt": attempt, "passed": passed,
                "seconds": round(time.monotonic()-started, 3),
                "usage": usage, "changed_files": changed,
                "error": "" if passed else last_error,
            })
            if passed:
                break
        if not passed:
            restore(step, workspace, before)
            record_jsonl(run_dir / "candidates.jsonl", {"step": step.id,
                "failure": last_error, "lesson": "", "verified": False})
        results.append({"step": step.id, "passed": passed})
        if not passed:
            break
    report = {"passed": bool(results) and all(x["passed"] for x in results),
              "steps": results, "workspace": str(workspace)}
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
