# Configuration and first run

## 1. Install
Requires Python 3.10+ and a disposable student workspace. Do not run this on your working source checkout.

```bash
git clone https://github.com/Voji12/micro-agent-lab-.git
cd micro-agent-lab-
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
```

On Windows PowerShell use `.venv\\Scripts\\Activate.ps1` and `Copy-Item .env.example .env`.

## 2. Configure .env
Local Ollama:
```dotenv
STUDENT_BASE_URL=http://127.0.0.1:11434/v1
STUDENT_API_KEY=
STUDENT_MODEL=qwen2.5-coder:7b
```
Use `ollama pull qwen2.5-coder:7b` then `ollama serve` if needed. Model name is an example, not a benchmarked recommendation.

Remote OpenAI-compatible server:
```dotenv
STUDENT_BASE_URL=https://your-private-llm.example/v1
STUDENT_API_KEY=YOUR_SECRET
STUDENT_MODEL=your-model-id
```
Keep the endpoint behind HTTPS/authentication. Do not expose Ollama publicly without authentication.

## 3. Review and run
```bash
pytest -q
micro-agent prompts experiments/001-airspeed/plan.example.json
mkdir -p student-workspace
micro-agent run experiments/001-airspeed/plan.example.json \\
  --workspace student-workspace --run-dir runs/first --allow-checks
```

The sample plan is illustrative: it is **not** a validated reproduction plan. Its TypeScript check requires an npm project with dependencies inside the student workspace. Prepare a clean-room workspace and reviewed plan before expecting success.

Logs: `runs/first/attempts.jsonl`, `checks.jsonl`, `candidates.jsonl`, `report.json`. Failed steps restore their allowed files; untracked side effects from check commands are not automatically reverted.

## Security and current limitations
- `.env` is ignored by git; do not paste credentials into plans, prompts or logs.
- Run only reviewed checks in disposable workspaces: checks execute local commands.
- Only explicitly allowlisted relative files can be written; symlinks escaping the workspace are rejected.
- Current file protocol uses full UTF-8 files, max 100KB per file; context max 35KB.
- A student is allowed at most two attempts per step. Failed steps stop the run.
- Experience records are **candidates** until independently marked verified.
- Teacher API variables are reserved; no automatic teacher planning, cl-agent or Aider integration yet.
- The harness does not start MSFS or certify flight behavior.
