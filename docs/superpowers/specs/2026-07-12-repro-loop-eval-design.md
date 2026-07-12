# Experiment-Loop Evaluation Design (bench/tiny-lm)

Evaluate whether porting autoresearch's experiment-loop discipline into `/reproduce`
improves the harness. Build a Mac-runnable benchmark, run the workflow before and
after the change, compare metrics.

## Decisions

| Decision | Choice |
|---|---|
| Benchmark | Tiny char-level LM on tiny-shakespeare, metric `val_bpb` (lower is better) |
| Time budget per training run | 120 s wall clock (env-overridable for tests) |
| Comparison | Two-arm session: Arm A = current freeform `/reproduce`, Arm B = autoresearch loop |
| Arm caps | 8 training runs or 35 min wall clock per arm, whichever first |
| Arm execution | Sequential subagents (MPS cannot be shared), each on its own git branch from the same baseline commit |
| Compute | Apple Silicon MPS, CPU fallback; single-device only |
| Dependency | `torch` in a `bench` dependency group (package-safety check before install) |

## Layout

```
bench/tiny-lm/
  prepare.py     — fixed: download, vocab, dataloader, evaluate_bpb, constants. Never edited during arms.
  train.py       — agent-editable: model, optimizer, training loop, summary printout.
  data/          — downloaded corpus (gitignored)
  README.md      — what this benchmark is, how to run it
  eval-report.md — the before/after comparison (written last)
tests/test_bench_prepare.py
tests/test_bench_train.py
```

`bench/` is outside the paper store; `scripts/check_store.py` is unaffected.

## prepare.py (fixed file)

- `DATA_URL` = karpathy/char-rnn tiny-shakespeare raw URL (1.1 MB, single ASCII file, stdlib urllib).
- `TIME_BUDGET_S` = 120, overridable via env var `TIME_BUDGET_S`.
- `MAX_SEQ_LEN` = 256, `VAL_FRACTION` = 0.1, `EVAL_BATCHES` = 20.
- `download() -> Path` — fetch corpus into `data/` if absent.
- `load_data() -> (train_ids, val_ids, stoi, itos, bytes_per_token)` — char vocab from sorted set of
  characters; whole text encoded to an int64 tensor; contiguous train/val split;
  `bytes_per_token = len(text.encode()) / len(text)`.
- `get_batch(data, batch_size, seq_len, device) -> (x, y)` — random offsets, next-char targets.
- `evaluate_bpb(model, val_ids, device, bytes_per_token) -> float` — fixed `EVAL_BATCHES` deterministic batches,
  `bpb = mean_nats / ln(2) / bytes_per_token`. Ground-truth metric; not modifiable.
- `pick_device() -> torch.device` — mps > cuda > cpu.

## train.py (baseline, agent-editable)

Plain small GPT, deliberately simple so there is honest headroom (constant LR, no
warmup, no weight tying, no grad clipping — normal baseline choices, not planted bugs):

- Config constants at top: `DEPTH=4`, `N_EMBD=256`, `N_HEAD=8`, `BATCH_SIZE=32`,
  `SEQ_LEN=256`, `LR=3e-4`, `WEIGHT_DECAY=0.1`.
- Blocks: LayerNorm → causal self-attention (`F.scaled_dot_product_attention`) → LayerNorm → 4x GELU MLP,
  learned positional embeddings, separate lm_head.
- Loop: one warmup step (excluded from timing, matches autoresearch's "excluding startup"),
  then train until `TIME_BUDGET_S`; count steps and tokens.
- Prints an autoresearch-style summary block: `val_bpb`, `training_seconds`, `total_seconds`,
  `num_steps`, `total_tokens_M`, `num_params_M`, `depth`. `grep "^val_bpb:" run.log` must work.

## /reproduce upgrade (the "after")

Append an "Experiment loop" section to `.claude/skills/reproduce/SKILL.md`:

1. Declare up front: the single metric, its direction, and the fixed per-run budget.
2. Loop: edit → `git commit` → `uv run python train.py > run.log 2>&1` → `grep "^<metric>:" run.log`
   → improved: keep (branch advances) / not improved: `git reset --hard` back → append `results.tsv`
   (`commit  metric  status  description`, tab-separated, status `keep|discard|crash`).
3. Crash rule: empty grep → `tail -n 50 run.log`; trivial fix → retry once; else log `crash`, revert, move on.
4. Kill rule: a run exceeding 2x budget is killed and logged as crash.
5. First run is always the unmodified baseline.

## Arm protocol

Both arms receive identical framing: goal = lowest `val_bpb`; edit only `train.py`;
`prepare.py` and the metric are read-only; no new dependencies; max 8 training runs, then
stop and report. Baseline run counts as run 1 in both arms.

- Branches: `bench/arm-a` and `bench/arm-b`, both cut from the same baseline commit on `main`.
- **Arm A (before):** current `/reproduce` behavior — keep a README-style log, iterate freely.
  No prescribed commits, no keep/discard rule, no results.tsv.
- **Arm B (after):** the upgraded loop protocol verbatim.
- Sequential dispatch; Arm A first.

## Metrics and report

`bench/tiny-lm/eval-report.md` compares:

- **Speed:** wall clock per arm; per-iteration overhead = (arm wall clock − sum of training_seconds) / runs.
  Sources: git commit timestamps, run summary blocks, arm logs.
- **Accuracy:** baseline val_bpb → best val_bpb per arm; per-run trajectory.
- **Complexity:** net LOC delta of the final kept `train.py` vs baseline; count of kept changes
  not attributable to a measured improvement.
- **Edge cases:** crashes/regressions encountered vs detected vs correctly discarded per arm.
- **Auditability:** fraction of results traceable to a specific commit (Arm B should be 100% by design).
- Stated caveat: single session per arm; process metrics are solid, the accuracy delta is
  suggestive, not statistically firm.

## Error handling

- Download failure: raise with the URL; no retry loop.
- No MPS: silently fall back to CPU via `pick_device()` (numbers still comparable within one machine).
- NaN loss during an arm: it is the arm's job to notice (that is part of the edge-case metric).

## Testing

- `test_bench_prepare.py`: encode/decode round-trip; `get_batch` shapes/dtypes and next-char
  alignment; `evaluate_bpb` on a uniform-logits dummy model ≈ `log2(V) / bytes_per_token`.
- `test_bench_train.py`: subprocess smoke run with `TIME_BUDGET_S=5`, assert the summary block
  parses and `val_bpb` is finite.
- Tests download the corpus once (1.1 MB) into the gitignored `data/`.

## Out of scope

- HF datasets/tokenizers, CUDA-specific kernels, distributed anything.
- Overnight never-stop mode.
- Touching the paper store or its lint.
- Statistical replication of arms (single session each).
