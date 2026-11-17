import json
import sys
from pathlib import Path
from micro_agent_lab.core import Step, format_prompt, load_lessons, load_plan, record_jsonl, run_checks

def test_prompt_uses_only_verified_lessons():
    step = Step("s1", "Implement", ["x.ts"], "One function", [[sys.executable, "-c", "pass"]])
    result = format_prompt(step, [{"lesson": "Use degrees", "verified": True}, {"lesson": "unreviewed", "verified": False}])
    assert "Use degrees" in result and "unreviewed" not in result and "x.ts" in result

def test_plan_and_check(tmp_path: Path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"steps": [{"id": "s1", "objective": "test", "files": ["x"],
        "instructions": "noop", "checks": [[sys.executable, "-c", "print('ok')"]]}]}))
    step = load_plan(plan)[0]
    assert run_checks(step, tmp_path, tmp_path / "checks.jsonl")
    assert json.loads((tmp_path / "checks.jsonl").read_text().splitlines()[0])["exit_code"] == 0

def test_memory_filters_unverified(tmp_path: Path):
    path = tmp_path / "lessons.jsonl"
    record_jsonl(path, {"lesson": "Unverified", "verified": False})
    record_jsonl(path, {"lesson": "Don't guess units", "verified": True})
    assert [x["lesson"] for x in load_lessons(path)] == ["Don't guess units"]
