"""RunPod REST API v2 Pod lifecycle with opt-in creation and automatic cleanup."""
from __future__ import annotations
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .config import load_dotenv

API = "https://api.runpod.io/v2"

def _request(method: str, path: str, payload: dict | None = None) -> dict:
    load_dotenv()
    key = os.environ.get("RUNPOD_API_KEY", "")
    if not key:
        raise ValueError("RUNPOD_API_KEY missing")
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(API + path, data=data, method=method, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=40) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"RunPod REST v2 HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("RunPod API unreachable") from exc

def status(pod_id: str) -> dict:
    return _request("GET", f"/pods/{pod_id}")

def start(pod_id: str) -> dict:
    return _request("POST", f"/pods/{pod_id}/action", {"action": "start"})

def stop(pod_id: str) -> dict:
    return _request("POST", f"/pods/{pod_id}/action", {"action": "stop"})

def create() -> str:
    load_dotenv()
    gpu = os.environ.get("RUNPOD_GPU_TYPE", "").strip()
    image = os.environ.get("RUNPOD_IMAGE", "").strip()
    template = os.environ.get("RUNPOD_TEMPLATE_ID", "").strip()
    if not gpu or (not image and not template):
        raise ValueError("Set RUNPOD_GPU_TYPE and RUNPOD_IMAGE or RUNPOD_TEMPLATE_ID for Pod creation")
    body = {
        "name": os.environ.get("RUNPOD_POD_NAME", "micro-agent-lab"),
        "image": image,
        "cloud": os.environ.get("RUNPOD_CLOUD_TYPE", "SECURE"),
        "gpu": {"id": gpu, "count": 1},
        "disk": int(os.environ.get("RUNPOD_CONTAINER_DISK_GB", "30")),
        "ports": [x.strip() for x in os.environ.get("RUNPOD_PORTS", "8000/http").split(",") if x.strip()],
        "mounts": {"persistent": {"size": int(os.environ.get("RUNPOD_VOLUME_GB", "30")),
                                   "path": "/workspace"}},
    }
    if template:
        body["templateId"] = template
        if not image:
            body.pop("image")
    return _request("POST", "/pods", body)["id"]

def endpoint(pod_id: str) -> str:
    load_dotenv()
    port = int(os.environ.get("RUNPOD_INFERENCE_PORT", "8000"))
    return f"https://{pod_id}-{port}.proxy.runpod.net/v1"

def wait_ready(base_url: str) -> None:
    """Probe authenticated model listing without logging headers or response bodies."""
    from urllib.request import Request, urlopen
    load_dotenv()
    timeout = int(os.environ.get("RUNPOD_READY_TIMEOUT_SECONDS", "600"))
    interval = int(os.environ.get("RUNPOD_POLL_SECONDS", "10"))
    key = os.environ.get("STUDENT_API_KEY", "")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(Request(base_url.rstrip("/") + "/models", headers=headers), timeout=10) as r:
                if r.status == 200:
                    return
        except (HTTPError, URLError, TimeoutError, OSError):
            pass
        time.sleep(interval)
    raise TimeoutError("Model endpoint not ready before timeout")

def managed_run(run_fn, *, create_pod: bool = False, stop_after: bool = True):
    """Start existing Pod if needed; always stop only if this invocation started/created it."""
    load_dotenv()
    pod_id = os.environ.get("RUNPOD_POD_ID", "").strip()
    started_here = False
    if create_pod:
        pod_id = create()
        started_here = True
    elif not pod_id:
        raise ValueError("Set RUNPOD_POD_ID or pass --create-pod")
    try:
        if not create_pod:
            current = status(pod_id)
            if not current:
                raise ValueError("Pod not found")
            if current.get("status") not in ("RUNNING", "STARTING", "PROVISIONING"):
                start(pod_id)
                started_here = True
        base = os.environ.get("RUNPOD_INFERENCE_BASE_URL", "").strip() or endpoint(pod_id)
        os.environ["STUDENT_BASE_URL"] = base
        wait_ready(base)
        return run_fn()
    finally:
        if stop_after and started_here:
            stop(pod_id)
