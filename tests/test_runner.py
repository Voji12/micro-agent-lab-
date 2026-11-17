import json
import sys
from pathlib import Path
import pytest
from micro_agent_lab.provider import decode_files
from micro_agent_lab.runner import safe_path, apply_files, execute
from micro_agent_lab.core import Step

def test_json_response():
    assert decode_files('{"files":[{"path":"a.txt","content":"hello"}]}')[0]["content"] == "hello"
    with pytest.raises(ValueError):
        decode_files('{"files":[{"path":"a.txt"}]}')

def test_path_allowlist_and_traversal(tmp_path):
    assert safe_path(tmp_path, "src/a.txt", {"src/a.txt"}) == tmp_path / "src/a.txt"
    with pytest.raises(ValueError):
        safe_path(tmp_path, "../escape", {"../escape"})
    with pytest.raises(ValueError):
        safe_path(tmp_path, "other", {"src/a.txt"})

def test_symlink_escape(tmp_path):
    external = tmp_path.parent / "external-dir"
    external.mkdir(exist_ok=True)
    (tmp_path / "link").symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError):
        safe_path(tmp_path, "link/a.txt", {"link/a.txt"})

def test_apply_only_allowed_files(tmp_path):
    step = Step("1", "test", ["ok.txt"], "test", [[sys.executable, "-c", "pass"]])
    with pytest.raises(ValueError):
        apply_files(step, tmp_path, [{"path": "wrong.txt", "content": "oops"}])
    apply_files(step, tmp_path, [{"path": "ok.txt", "content": "hello"}])
    assert (tmp_path / "ok.txt").read_text() == "hello"

def test_run_mock_model(tmp_path, monkeypatch):
    from micro_agent_lab import runner
    monkeypatch.setattr(runner, "completion", lambda prompt: ('{"files":[{"path":"result.txt","content":"OK"}]}', {"total_tokens": 12}))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"steps":[{"id":"1","objective":"write OK","files":["result.txt"],
      "instructions":"exactly OK","checks":[[sys.executable,"-c","from pathlib import Path; assert Path('result.txt').read_text() == 'OK'"]]}]}))
    report = execute(plan, workspace, tmp_path / "runs", tmp_path / "lessons.jsonl", allow_checks=True)
    assert report["passed"]
    assert (workspace / "result.txt").read_text() == "OK"
    assert json.loads((tmp_path / "runs" / "attempts.jsonl").read_text().splitlines()[0])["usage"]["total_tokens"] == 12

def test_failed_step_rolls_back(tmp_path, monkeypatch):
    from micro_agent_lab import runner
    monkeypatch.setattr(runner, "completion", lambda prompt: ('{"files":[{"path":"result.txt","content":"BAD"}]}', {}))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "result.txt").write_text("ORIGINAL")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"steps":[{"id":"1","objective":"write OK","files":["result.txt"],
      "instructions":"exactly OK","checks":[[sys.executable,"-c","from pathlib import Path; assert Path('result.txt').read_text() == 'OK'"]]}]}))
    report = execute(plan, workspace, tmp_path / "runs", tmp_path / "lessons.jsonl", allow_checks=True)
    assert not report["passed"]
    assert (workspace / "result.txt").read_text() == "ORIGINAL"
    assert len((tmp_path / "runs" / "attempts.jsonl").read_text().splitlines()) == 2
