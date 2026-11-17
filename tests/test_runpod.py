import os
import pytest
from micro_agent_lab import runpod

def test_endpoint(monkeypatch):
    monkeypatch.setenv("RUNPOD_INFERENCE_PORT", "8000")
    assert runpod.endpoint("abc123") == "https://abc123-8000.proxy.runpod.net/v1"

def test_existing_running_pod_is_not_stopped(monkeypatch):
    monkeypatch.setenv("RUNPOD_POD_ID", "abc")
    monkeypatch.setattr(runpod, "status", lambda _: {"desiredStatus": "RUNNING"})
    monkeypatch.setattr(runpod, "wait_ready", lambda _: None)
    monkeypatch.setattr(runpod, "stop", lambda _: pytest.fail("Must not stop preexisting running pod"))
    assert runpod.managed_run(lambda: 42) == 42

def test_started_pod_stops_even_on_failure(monkeypatch):
    monkeypatch.setenv("RUNPOD_POD_ID", "abc")
    monkeypatch.setattr(runpod, "status", lambda _: {"desiredStatus": "EXITED"})
    calls = []
    monkeypatch.setattr(runpod, "start", lambda pod: calls.append(("start", pod)))
    monkeypatch.setattr(runpod, "stop", lambda pod: calls.append(("stop", pod)))
    monkeypatch.setattr(runpod, "wait_ready", lambda _: None)
    with pytest.raises(RuntimeError):
        runpod.managed_run(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    assert calls == [("start", "abc"), ("stop", "abc")]

def test_no_pod_without_id(monkeypatch):
    monkeypatch.delenv("RUNPOD_POD_ID", raising=False)
    with pytest.raises(ValueError):
        runpod.managed_run(lambda: None)
