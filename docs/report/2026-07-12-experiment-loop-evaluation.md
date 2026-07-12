# Evaluation: autoresearch experiment loop in /reproduce (before vs after)

Date: 2026-07-12
Machine: Apple Silicon (MPS), torch 2.13.0, Python 3.14 via uv
Branch under evaluation: `feat/bring-autoresearch`

## Question

Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) runs an autonomous
experiment loop: edit one file, train for a fixed time budget, keep or discard by a single
metric, log everything, repeat. We ported that loop discipline into the `/reproduce` skill.
Does it actually improve how the agent runs experiments, measured on speed, accuracy,
complexity, edge-case detection, and auditability?

## Benchmark

`bench/tiny-lm/` — a char-level LM speedrun scaled to Apple Silicon, mirroring
autoresearch's two-file split:

- `prepare.py` (read-only): tiny-shakespeare download, char vocab, dataloader,
  `evaluate_bpb` ground-truth metric, fixed constants.
- `train.py` (agent-editable): baseline GPT (depth 4, 256 embd, 3.3M params), AdamW,
  training loop with a fixed **120 s** wall-clock budget (warmup excluded).
- Metric: `val_bpb` — validation bits per byte, lower is better. Uniform-random scores
  ~6.0; the untouched baseline scores ~3.0–3.1 depending on machine load.

Covered by 4 pytest tests (vocab round-trip, batch alignment, uniform-model bpb sanity,
subprocess smoke run); full repo suite: 21 passed.

## Method

Two agent sessions ("arms") ran the same task from the same baseline commit (`d3fee83`):
lowest `val_bpb`, edit only `train.py`, no new dependencies, maximum 8 training runs
including the mandatory unmodified-baseline first run.

- **Arm A (before):** freeform iteration — no prescribed git or logging protocol, log
  format its own choice. Branch `bench/arm-a` (tip `a7e95df`).
- **Arm B (after):** the ported loop, verbatim — one change per run, commit before run,
  `run.log` redirect + grep for the metric, keep (branch advances) / discard (roll back),
  append to `results.tsv`, crash and kill rules. Branch `bench/arm-b` (tip `0471d5d`).

Arms ran sequentially (single MPS device). Neither arm was given a wall-clock cap, only
the 8-run cap — identical prompts except for the protocol section.

## Per-run results

### Arm A (freeform)

| Run | Idea | val_bpb |
|----:|------|--------:|
| 1 | Unmodified baseline | 2.9636 |
| 2 | Bundle: 4x384 h3, bf16, cosine peak 2e-3, zero-init residuals+head | 3.5536 (regression) |
| 3 | Same arch, peak 8e-4 cosine, GPT-2 scaled residual init | 2.3911 |
| 4 | Muon optimizer (batched NS5) on hidden matrices, AdamW elsewhere | 2.1692 |
| 5 | + RoPE (full-dim), Muon wd 0.2, EMA weight selection | 2.1515 |
| 6 | RoPE made cheap: fused stacked-qk call, partial rotation | 2.1345 |
| 7 | Trapezoid LR schedule (3% warmup, flat to 60%, linear to 0) | **2.1001** |
| 8 | Replicate run 7 (stability check) | 2.1332 (throttled: 469 vs 694 steps) |

Also ran ~15 unbudgeted "offline smoke previews" between official runs (not counted
against the 8-run cap, unaccounted in any log). No commits made during the session;
final state captured afterward in a single commit.

### Arm B (loop protocol)

| Run | Idea | val_bpb | Decision |
|----:|------|--------:|----------|
| 1 | Unmodified baseline | 3.1246 | keep (baseline) |
| 2 | Peak LR 2e-3, time-based warmup+cosine, betas 0.9/0.95 | 2.4122 | keep |
| 3 | Vectorized on-device train batch gather | 2.4044 | keep (marginal) |
| 4 | bf16 autocast forward pass | 2.3796 | keep |
| 5 | Batch 64 + LR 3e-3 | 2.4722 | discard |
| 6 | Weight tying + GPT-2 init, scaled residual projections | **2.2966** | keep |
| 7 | EMA weight averaging for eval | 2.8269 | discard |
| 8 | torch.compile on MPS | 3.1111 | discard |

Kept commits: `162eac5`, `d97798d`, `367d1c5`, `4c52ec5`. Discards preserved as revert
commits (`882704c`, `9c2dcfb`, `ff52efc`). Full table in `results.tsv` (committed in
`0471d5d`), protocol log in `arm-b-log.md`.

## Comparison

| Metric | Arm A (before) | Arm B (after) |
|---|---|---|
| Baseline val_bpb | 2.9636 | 3.1246 |
| Best val_bpb | **2.1001** | 2.2966 |
| Relative improvement | −29.1% | −26.5% |
| Wall clock | 115 min | **24.3 min** |
| bpb reduction per minute | 0.0075 | **0.034** (4.5x) |
| Time per budgeted run | 14.4 min | 3.0 min |
| train.py net LOC delta | +160 (106 → 266) | **+36** (106 → 142) |
| Changes per run | bundled (2–3) | one |
| Regressions detected | 2 (informal rollback) | 3 (logged, reverted commits) |
| Crashes | 0 | 0 |
| Results traceable to a commit | 0/8 during session | **8/8** |

### Speed

The loop was the decisive win: 4.7x less wall clock for a comparable relative gain.
Arm A's time went into the unbudgeted smoke previews — each cost minutes, none was
accounted anywhere. Arm B's fixed edit→commit→run→grep cycle kept non-training overhead
at ~0.5 min per run.

### Accuracy

Arm A's absolute best is better (2.10 vs 2.30), bought with ~5x the compute: previews
de-risked aggressive changes (hand-rolled Muon, RoPE) that a strict one-change-per-run
loop did not attempt within 8 runs. Per minute of wall clock the loop was 4.5x more
efficient; at matched wall clock Arm B would have had ~35 additional runs to spend.

### Complexity

Arm A's final file more than doubled (+160 LOC: Muon with batched Newton-Schulz, a
Rotary class, EMA machinery), and because it bundled 2–3 changes per run, individual
contributions are not attributable from its own data. Arm B's +36 LOC map one-to-one to
measured deltas.

### Edge cases

Both arms detected their regressions. Arm B's protocol additionally surfaced a no-op run
(zsh noclobber blocked the `run.log` redirect — caught before consuming a run) and kept
discarded ideas inspectable as revert commits. Arm A's replication check (run 8) exposed
the machine's noise floor: identical config scored 2.1001 vs 2.1332 under thermal
throttling (469–694 steps), i.e. ±0.03 bpb.

That noise floor reveals a real protocol gap: Arm B's run 3 "keep" improved by 0.008 —
inside the noise. The loop as written has no noise guard.

### Auditability

Arm B: every result, kept or discarded, checks out to a commit; `git checkout <hash>`
reproduces the exact code. The permission system denied `git reset --hard`, and the
`git revert` fallback turned out better than autoresearch's own design — reset destroys
discarded states, revert preserves them. Arm A committed nothing during its session;
intermediate states are unrecoverable and results exist only in its freeform log.

## Verdict

The autoresearch port pays for itself on process metrics: **4.7x faster iteration, 4.5x
more metric improvement per minute, one-quarter the code growth, a complete audit trail,
and regressions handled by rule instead of judgment.** The freeform arm reached a lower
absolute bpb only by spending roughly 5x unaccounted compute on off-protocol previews;
at matched wall clock the loop dominates.

Recommended follow-up: add a noise guard to the `/reproduce` loop — a minimum-improvement
threshold or a replicate-before-keep rule — since keep/discard decisions near the
machine's ±0.03 bpb noise floor are currently coin flips.

## Caveats

- One LLM session per arm; run-to-run agent variance is unmeasured.
- The arms drew different baseline numbers (2.96 vs 3.12) from machine-load noise.
- Arms were capped by run count, not wall clock. That is what let Arm A's time balloon —
  informative in itself, but a confound for the accuracy comparison.

## Artifacts

- Benchmark and report: `bench/tiny-lm/` (`prepare.py`, `train.py`, `eval-report.md`)
- Protocol under test: `.claude/skills/reproduce/SKILL.md`, "Experiment loop" section
- Evidence branches: `bench/arm-a` (tip `a7e95df`), `bench/arm-b` (tip `0471d5d`), both
  cut from `d3fee83` on `feat/bring-autoresearch`
- Spec: `docs/superpowers/specs/2026-07-12-repro-loop-eval-design.md`
- Plan: `docs/superpowers/plans/2026-07-12-repro-loop-eval.md`
