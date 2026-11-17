import pytest
from micro_agent_lab.profiles import select_profile

def test_notebook_profile(monkeypatch):
    monkeypatch.setenv("NOTEBOOK_BASE_URL", "http://127.0.0.1:8888/v1")
    monkeypatch.setenv("NOTEBOOK_MODEL", "qwen")
    monkeypatch.setenv("NOTEBOOK_API_KEY", "secret")
    x = select_profile("notebook")
    assert x["model"] == "qwen" and x["has_key"]
    assert "secret" not in repr(x)

def test_shadow_requires_url(monkeypatch):
    monkeypatch.delenv("SHADOW_BASE_URL", raising=False)
    monkeypatch.setenv("SHADOW_MODEL", "coder14")
    with pytest.raises(ValueError):
        select_profile("shadow")

def test_unknown_profile():
    with pytest.raises(ValueError):
        select_profile("missing")
