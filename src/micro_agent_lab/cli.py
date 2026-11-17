from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import format_prompt, load_lessons, load_plan, record_jsonl, run_checks

def main() -> None:
    p = argparse.ArgumentParser(description="Micro Agent Lab: offline orchestration utilities")
    sub = p.add_subparsers(dest="action", required=True)
    show = sub.add_parser("prompts", help="Generate student prompts from a teacher plan")
    show.add_argument("plan", type=Path)
    show.add_argument("--lessons", type=Path, default=Path("memory/lessons.jsonl"))
    check = sub.add_parser("verify", help="Run trusted checks for one step")
    check.add_argument("plan", type=Path)
    check.add_argument("step")
    check.add_argument("--cwd", type=Path, required=True)
    check.add_argument("--log", type=Path, default=Path("runs/checks.jsonl"))
    lesson = sub.add_parser("lesson", help="Record a candidate lesson for independent verification")
    lesson.add_argument("--step", required=True)
    lesson.add_argument("--failure", required=True)
    lesson.add_argument("--lesson", required=True)
    lesson.add_argument("--evidence", required=True)
    lesson.add_argument("--path", type=Path, default=Path("memory/lessons.jsonl"))
    args = p.parse_args()
    if args.action == "prompts":
        lessons = load_lessons(args.lessons)
        for step in load_plan(args.plan):
            print(f"\n{'='*20} {step.id} {'='*20}\n{format_prompt(step, lessons)}")
    elif args.action == "verify":
        matches = [s for s in load_plan(args.plan) if s.id == args.step]
        if not matches:
            p.error(f"Unknown step {args.step}")
        ok = run_checks(matches[0], args.cwd.resolve(), args.log)
        print(json.dumps({"step": args.step, "passed": ok, "log": str(args.log)}))
        raise SystemExit(0 if ok else 1)
    else:
        record_jsonl(args.path, {"step": args.step, "failure": args.failure,
                                 "lesson": args.lesson, "evidence": args.evidence, "verified": False})
        print(f"Saved candidate lesson to {args.path}; verify before reuse")

if __name__ == "__main__":
    main()
