# Two-GPU zero-extra-cloud-cost lab

## Hardware roles

- Notebook: RTX 3500 Ada 12 GB; Unsloth Studio, 7B/8B coding student, GGUF Q4_K_M initially.
- Shadow PC Power: RTX A4500 20 GB; Unsloth Studio, 14B coding student / comparison. GPU availability and model fit must be confirmed.
- RunPod: optional and **never started** when selecting notebook or shadow.
- Teacher: manual plan initially; automatic teacher API integration is not yet implemented.

Unsloth Studio is preferred for its visible chat, model management and API controls. Its API adds overhead relative to direct llama.cpp; measure tokens/sec and end-to-end latency instead of assuming it is fastest.

## Install and serve Unsloth Studio

Official instructions: https://github.com/unslothai/unsloth

Start on notebook (Windows PowerShell, after installing Studio):
```powershell
unsloth studio -p 8888 --disable-tools
```
Load a coding GGUF model in the UI, open **Settings → API**, generate a key, and inspect the exact model ID in the API models list. The `--disable-tools` switch prevents server-side terminal/web/Python tools from being available to API clients.

Configure notebook in `.env`:
```dotenv
NOTEBOOK_BASE_URL=http://127.0.0.1:8888/v1
NOTEBOOK_API_KEY=YOUR_UNSLOTH_KEY
NOTEBOOK_MODEL=EXACT_MODEL_ID
```

Shadow: install and launch Studio the same way. **Do not expose Studio directly to the Internet**. Prefer Tailscale plus an authenticated HTTPS reverse proxy, or run the benchmark locally on Shadow. Configure `SHADOW_BASE_URL=https://your-private-shadow-endpoint/v1`, `SHADOW_API_KEY`, and `SHADOW_MODEL`.

## Probe

```bash
micro-agent probe --provider notebook
micro-agent probe --provider shadow
```

Probe returns only URL, configured model name, whether a key is configured, available model IDs, and whether the configured model is listed. It never prints the key.

## Run isolated benchmark

```bash
mkdir -p student-workspace
micro-agent run experiments/000-smoke/plan.json --provider notebook --workspace student-workspace --run-dir runs/notebook --allow-checks
micro-agent run experiments/000-smoke/plan.json --provider shadow --workspace student-workspace --run-dir runs/shadow --allow-checks
```

For a fair comparison, use a **fresh workspace** per provider and distinct run dirs. The runner records response usage, latency, test outcome and retries. It does not currently record GPU utilization or true energy costs.

Shadow PC sessions can expire; run the harness on the same machine or ensure your network tunnel stays up. Avoid scheduling unattended multi-hour runs without checking session behavior.

## Next milestones

1. Confirm notebook and Shadow model IDs, exact VRAM use and inference speed.
2. Add fully clean-room MSFS gauge fixture and independent tests.
3. Implement teacher endpoint and automated plan generation.
4. Compare notebook 7B vs Shadow 14B using identical tasks.
