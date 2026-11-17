# Micro Agent Lab

Experimental, provider-neutral harness for **teacher → microtask plan → small local coding student → verification → experience memory**.

**Status: executable student MVP.** OpenAI-compatible/Ollama student, constrained file writes, test loop, retries, rollback and JSONL logs are implemented. Teacher API, Aider/cl-agent integration and real model benchmarks are not implemented.

## Reference
Read-only source: https://github.com/Voji12/msfs-cockpit — React/TypeScript/SVG airspeed gauge, C#/.NET Framework 4.8 SimConnect bridge. This repo does not modify or copy the source.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env  # edit URL, key and model
pytest -q
micro-agent prompts experiments/000-smoke/plan.json
mkdir -p student-workspace
micro-agent run experiments/000-smoke/plan.json --workspace student-workspace --run-dir runs/first --allow-checks
```

## Commands
```bash
micro-agent verify experiments/001-airspeed/plan.example.json 001 --cwd /path/to/trusted-isolated-workspace
micro-agent lesson --step 001 --failure 'wrong angle unit' --lesson 'specify degrees explicitly' --evidence 'test output'
```

Read [setup and security](docs/SETUP.md), [experiment design](docs/EXPERIMENT.md) and [teacher instructions](docs/TEACHER_PROMPT.md). Only execute **reviewed** plan commands inside disposable workspaces; never commit secrets, proprietary SDKs or source from private projects.

## Next milestones
1. Prepare clean-room student fixture and teacher-generated plan.
2. Validate the existing Ollama/OpenAI-compatible student and constrained full-file runner on a clean-room fixture.
3. Record retries, latency, tokens, costs, tests and diffs.
4. Promote only independently verified lessons and compare experimental arms.
5. Evaluate Aider/cl-agent integration after checking compatibility.
