# Unsloth Studio and RunPod

## Unsloth Studio (local or remote)

Unsloth Studio exposes OpenAI-compatible `/v1/chat/completions`. Start Studio, load a coding model, and create a key in **Settings → API**. Use the model ID returned by `/v1/models`.

In `.env`:

```dotenv
UNSLOTH_BASE_URL=http://127.0.0.1:8888/v1
UNSLOTH_API_KEY=your-unsloth-key
UNSLOTH_MODEL=exact-loaded-model-id
```

Run:
```bash
micro-agent run experiments/000-smoke/plan.json --provider unsloth --workspace student-workspace --run-dir runs/unsloth --allow-checks
```

If remote, use an authenticated HTTPS endpoint. Do not expose Studio on the public Internet without protection.

## RunPod (GPU billed while running)

Uses **RunPod REST API v2**, not deprecated v1. Supports:
- Existing stopped Pod: query state → start if stopped → wait for model API → run → stop in `finally`.
- Existing running Pod: use it without stopping someone else's running workload.
- New Pod: **explicit** `--create-pod`, then stop after the run.
- `--keep-pod-running` disables automatic stop (may continue billing).
- No Pod is created or started by running `pytest` or `micro-agent prompts`.

Configure:

```dotenv
RUNPOD_API_KEY=your-runpod-api-key
RUNPOD_POD_ID=existing-pod-id
RUNPOD_MODEL=exact-served-model-id
RUNPOD_INFERENCE_API_KEY=your-inference-server-key
RUNPOD_INFERENCE_PORT=8000
RUNPOD_READY_TIMEOUT_SECONDS=600
```

The inference URL is derived as `https://{pod-id}-8000.proxy.runpod.net/v1`. Alternatively set `RUNPOD_INFERENCE_BASE_URL` explicitly. **The Pod must already be configured to launch an OpenAI-compatible inference server** on the selected port. RunPod management does not automatically install, download, or serve the model.

```bash
micro-agent run experiments/000-smoke/plan.json --provider runpod --workspace student-workspace --run-dir runs/runpod --allow-checks
```

### Provision a new Pod via API

Set `RUNPOD_POD_ID=` and configure:

```dotenv
RUNPOD_GPU_TYPE=NVIDIA GeForce RTX 4090
RUNPOD_TEMPLATE_ID=your-preconfigured-inference-template-id
RUNPOD_IMAGE=
RUNPOD_CLOUD_TYPE=SECURE
RUNPOD_VOLUME_GB=30
RUNPOD_CONTAINER_DISK_GB=30
RUNPOD_PORTS=8000/http
```

A template or image must **start the model API automatically**. The recommended path is a RunPod template with vLLM or another OpenAI-compatible server preconfigured. If using a custom image, set `RUNPOD_IMAGE` instead of the template ID. A generic PyTorch image alone will **not** work. Do not put the inference key in container arguments, which can be exposed through API metadata.

```bash
micro-agent run experiments/000-smoke/plan.json --provider runpod --create-pod --workspace student-workspace --run-dir runs/newpod --allow-checks
```

The Pod is stopped on completion or failure **when this run started it**. RunPod may still bill persistent storage after stop; delete unused Pods/storage manually. Stopping a Pod releases the GPU and resuming later may fail due to GPU unavailability. The RunPod HTTP proxy can time out long inference calls; consider direct TCP or a suitable authenticated proxy for long generations.

### Security and spending

- API keys are loaded from `.env` and not committed.
- The management key is sent only to `api.runpod.io`, not the model server.
- Review any `--allow-checks` commands; they execute local subprocesses.
- Use low-cost GPUs, short readiness timeouts and watch billing.
- No remote Pod has been launched by this project yet. Creation and stop have **mock tests**, not live billing tests.

Sources:
- https://docs.runpod.io/
- https://github.com/runpod/runpod-plugins-official/blob/main/plugins/runpod/skills/runpod-migrate/reference/graphql-to-v2.md
- https://github.com/unslothai/unsloth/discussions/5285
