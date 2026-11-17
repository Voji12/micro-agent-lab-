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
    execute_parser = sub.add_parser("run", help="Run student against isolated workspace")
    execute_parser.add_argument("plan", type=Path)
    execute_parser.add_argument("--workspace", type=Path, required=True)
    execute_parser.add_argument("--run-dir", type=Path, default=Path("runs/latest"))
    execute_parser.add_argument("--lessons", type=Path, default=Path("memory/lessons.jsonl"))
    execute_parser.add_argument("--allow-checks", action="store_true", help="Explicitly allow plan subprocess commands")
    execute_parser.add_argument("--provider", choices=["student", "unsloth", "runpod", "notebook", "shadow"], default="student")
    execute_parser.add_argument("--create-pod", action="store_true", help="Explicitly provision billable RunPod Pod")
    execute_parser.add_argument("--keep-pod-running", action="store_true", help="Do not stop Pod after execution")
    probe = sub.add_parser("probe", help="Check configured model endpoint")
    probe.add_argument("--provider", choices=["notebook", "shadow"], required=True)
    args = p.parse_args()
    if args.action == "probe":
        from .profiles import probe_profile
        print(json.dumps(probe_profile(args.provider), indent=2))
    elif args.action == "prompts":
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
    elif args.action == "run":
        from .runner import execute
        if args.provider in ("notebook", "shadow"):
            from .profiles import select_profile
            select_profile(args.provider)
        elif args.provider == "unsloth":
            import os
            from .config import load_dotenv
            load_dotenv()
            os.environ["STUDENT_BASE_URL"] = os.environ.get("UNSLOTH_BASE_URL", "http://127.0.0.1:8888/v1")
            os.environ["STUDENT_API_KEY"] = os.environ.get("UNSLOTH_API_KEY", "")
            os.environ["STUDENT_MODEL"] = os.environ.get("UNSLOTH_MODEL", "")
        def do_run():
            return execute(args.plan, args.workspace, args.run_dir, args.lessons, allow_checks=args.allow_checks)
        if args.provider == "runpod":
            from .runpod import managed_run
            from .config import load_dotenv
            import os
            load_dotenv()
            os.environ["STUDENT_MODEL"] = os.environ.get("RUNPOD_MODEL", "")
            os.environ["STUDENT_API_KEY"] = os.environ.get("RUNPOD_INFERENCE_API_KEY", "")
            result = managed_run(do_run, create_pod=args.create_pod, stop_after=not args.keep_pod_running)
        else:
            result = do_run()
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["passed"] else 1)
    else:
        record_jsonl(args.path, {"step": args.step, "failure": args.failure,
                                 "lesson": args.lesson, "evidence": args.evidence, "verified": False})
        print(f"Saved candidate lesson to {args.path}; verify before reuse")

if __name__ == "__main__":
    main()
