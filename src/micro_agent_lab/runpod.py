"""RunPod Pod lifecycle through documented GraphQL operations.

No automatic Pod creation without explicit --create-pod.
The RunPod API key is never sent to the inference endpoint.
"""
from __future__ import annotations
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .config import load_dotenv

API = "https://api.runpod.io/graphql"

def _request(query: str, variables: dict | None = None) -> dict:
    load_dotenv()
    key = os.environ.get("RUNPOD_API_KEY", "")
    if not key:
        raise ValueError("RUNPOD_API_KEY missing")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    # RunPod GraphQL documentation specifies api_key query parameter.
    from urllib.parse import urlencode
    req = Request(API + "?" + urlencode({"api_key": key}), data=body,
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=40) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"RunPod HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("RunPod API unreachable") from exc
    if result.get("errors"):
        raise RuntimeError("RunPod GraphQL error: " +
                           "; ".join(e.get("message", "unknown") for e in result["errors"]))
    return result["data"]

def status(pod_id: str) -> dict:
    return _request("query($id:String!){pod(input:{podId:$id}){id desiredStatus runtime{uptimeInSeconds}}}",
                    {"id": pod_id})["pod"]

def start(pod_id: str) -> dict:
    return _request("mutation($id:String!){podResume(input:{podId:$id,gpuCount:1}){id desiredStatus}}",
                    {"id": pod_id})["podResume"]

def stop(pod_id: str) -> dict:
    return _request("mutation($id:String!){podStop(input:{podId:$id}){id desiredStatus}}",
                    {"id": pod_id})["podStop"]

def create() -> str:
    load_dotenv()
    gpu = os.environ.get("RUNPOD_GPU_TYPE", "").strip()
    image = os.environ.get("RUNPOD_IMAGE", "").strip()
    if not gpu or not image:
        raise ValueError("Set RUNPOD_GPU_TYPE and RUNPOD_IMAGE for Pod creation")
    input_data = {
        "cloudType": os.environ.get("RUNPOD_CLOUD_TYPE", "SECURE"),
        "gpuCount": 1,
        "gpuTypeId": gpu,
        "name": os.environ.get("RUNPOD_POD_NAME", "micro-agent-lab"),
        "imageName": image,
        "volumeInGb": int(os.environ.get("RUNPOD_VOLUME_GB", "30")),
        "containerDiskInGb": int(os.environ.get("RUNPOD_CONTAINER_DISK_GB", "30")),
        "ports": os.environ.get("RUNPOD_PORTS", "8000/http"),
        "volumeMountPath": "/workspace",
    }
    # The image must serve the configured model itself. Creation does not install/launch a model.
    result = _request(
        "mutation($input:PodFindAndDeployOnDemandInput!){podFindAndDeployOnDemand(input:$input){id}}",
        {"input": input_data})
    return result["podFindAndDeployOnDemand"]["id"]

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
            if current.get("desiredStatus") != "RUNNING":
                start(pod_id)
                started_here = True
        base = os.environ.get("RUNPOD_INFERENCE_BASE_URL", "").strip() or endpoint(pod_id)
        os.environ["STUDENT_BASE_URL"] = base
        wait_ready(base)
        return run_fn()
    finally:
        if stop_after and started_here:
            stop(pod_id)
