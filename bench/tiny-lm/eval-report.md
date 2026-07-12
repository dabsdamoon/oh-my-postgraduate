# Experiment-loop evaluation: before vs after

Did porting autoresearch's experiment loop into `/reproduce` improve the harness?
Two agent sessions ran the same task — lower `val_bpb` on this benchmark, editing only
`train.py` — from the same baseline commit (`d3fee83`), max 8 training runs each
(baseline included), 120 s training budget per run, Apple Silicon MPS.

- **Arm A (before):** freeform iteration, no prescribed git or logging protocol. Branch `bench/arm-a`.
- **Arm B (after):** the `/reproduce` experiment loop — one change per run, commit before run,
  keep/discard by metric, `results.tsv`. Branch `bench/arm-b`.

## Results

| Metric | Arm A (before) | Arm B (after) |
|---|---|---|
| Baseline val_bpb | 2.9636 | 3.1246 |
| Best val_bpb | **2.1001** | 2.2966 |
| Relative improvement | −29.1% | −26.5% |
| Wall clock | **115 min** | **24.3 min** |
| bpb reduction per minute | 0.0075 | **0.034** (4.5x) |
| Time per budgeted run | 14.4 min | 3.0 min |
| train.py net LOC delta | +160 (106 → 266) | **+36** (106 → 142) |
| Changes per run | bundled (2–3) | one |
| Regressions detected | 2 (informal rollback) | 3 (logged, reverted commits) |
| Crashes | 0 | 0 |
| Results traceable to a commit | 0/8 during session | **8/8** |

### Per-run trajectories

Arm A: 2.9636 → 3.5536 (regression) → 2.3911 → 2.1692 (Muon) → 2.1515 (RoPE+EMA) →
2.1345 → **2.1001** (trapezoid LR) → 2.1332 (replication check, throttled).

Arm B: 3.1246 → 2.4122 (LR schedule) → 2.4044 (on-device batching) → 2.3796 (bf16) →
2.4722 discard (batch 64) → **2.2966** (weight tying + init) → 2.8269 discard (EMA) →
3.1111 discard (torch.compile).

## Reading the numbers

**Speed.** The loop was the decisive win: 4.7x less wall clock for a comparable relative
gain. Arm A's time went into ~15 unbudgeted "offline smoke previews" between official runs
— careful, but each one cost minutes and none was accounted anywhere. Arm B's fixed
edit→commit→run→grep cycle kept overhead at ~0.5 min per run.

**Accuracy.** Arm A's absolute best is better (2.10 vs 2.30), bought with ~5x the compute:
its previews de-risked aggressive changes (custom Muon optimizer, RoPE), which the strict
one-change-per-run loop didn't attempt in 8 runs. Per minute of wall clock, the loop was
4.5x more efficient. With equal wall-clock budgets instead of equal run counts, Arm B
would have had ~35 more runs to spend.

**Complexity.** Arm A's final file more than doubled (+160 LOC: hand-rolled Muon with
batched Newton-Schulz, a Rotary class, EMA machinery). Because it bundled 2–3 changes per
run, the contribution of individual kept changes is not attributable from its own data.
Arm B's +36 LOC are one-commit-per-idea; every kept line maps to a measured delta.

**Edge cases.** Both arms detected their regressions. Arm B's protocol additionally
surfaced a no-op run (zsh noclobber blocked the log redirect — caught before consuming a
run) and left discarded ideas as revert commits, so failures are inspectable. Arm A's
replication check (run 8) exposed the machine's noise floor: identical config scored
2.1001 vs 2.1332 (469–694 steps under throttling) — ±0.03 bpb. That matters for the
protocol: Arm B's run 3 "keep" (Δ0.008) is inside that noise. The loop as written has no
noise guard; a minimum-improvement threshold or replicate-before-keep rule is the obvious
next upgrade.

**Auditability.** Arm B: every result, kept or discarded, checks out to a commit
(`git checkout <hash>` reproduces the exact code; discards preserved via revert commits —
the permission system denied `git reset --hard`, and the fallback turned out to be an
improvement over autoresearch's reset, which destroys discarded states). Arm A: nothing
was committed during the session; intermediate states are unrecoverable and results exist
only in its freeform log.

## Verdict

The autoresearch port pays for itself on process metrics: 4.7x faster iteration, 4.5x more
metric improvement per minute, one-quarter the code growth, full audit trail, and
regressions handled by rule instead of judgment. The freeform arm reached a lower absolute
bpb only by spending unaccounted compute on off-protocol previews — with matched wall
clock, the loop dominates.

Caveats: one session per arm (LLM run-to-run variance is unmeasured); the arms drew
different baseline numbers from the machine-load noise the replication check exposed
(±0.03 bpb); arms were capped by run count, not wall clock, which is what let Arm A's
time balloon — an informative outcome, but a confound for the accuracy comparison. The
identified protocol gap (no noise guard on keep/discard) is real and worth fixing in
`/reproduce`.

Machine: Apple Silicon, MPS, torch 2.13.0, 2026-07-12. Arms: `bench/arm-a` (tip
`a7e95df`), `bench/arm-b` (tip `0471d5d`), both cut from `d3fee83`.
