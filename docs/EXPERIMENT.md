# Experiment 001: reproduce the airspeed gauge

Reference: https://github.com/Voji12/msfs-cockpit (read-only).

## Hypothesis
A 7B–9B student using teacher-authored microtasks and verified experience memory can reproduce a functional airspeed indicator with fewer failures and lower total cost than without decomposition.

## Isolation
1. Clone source into a separate reference-only directory.
2. Construct a clean student workspace using approved telemetry contracts and fixtures, **without** the original gauge implementation.
3. Teacher reads reference and writes the plan. Reviewer checks for answer leakage.
4. Student edits only allowlisted files. No automatic push or SDK download.
5. Run deterministic tests. Live MSFS acceptance is manual and is **not** claimed by this harness.

## Arms
A: student, broad task, no memory.
B: student, microtasks, no memory.
C: student, microtasks, verified memory.
D: strong model directly.

## Metrics
Log model, quantization, GPU, planning time, wall time, token counts when available, retries, checks, escalations, human interventions, GPU time and cost. Separate GPU idle from generation time.

## Failure policy
Two attempts maximum per step. Record logs and diffs. Stop after failure. A teacher proposes a lesson; independent evidence is required before promoting it to verified memory.

## Next
Generate and review a full reference-derived plan. The example plan is intentionally incomplete.
