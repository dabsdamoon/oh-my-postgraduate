# tiny-lm benchmark

Char-level LM speedrun on tiny-shakespeare, autoresearch-style, scaled to Apple Silicon.

- `prepare.py` — data, vocab, dataloader, `evaluate_bpb` (ground-truth metric), constants. Read-only during experiments.
- `train.py` — model, optimizer, training loop. The file experiments modify.
- Metric: `val_bpb` (validation bits per byte), lower is better.
- Budget: each run trains for a fixed `TIME_BUDGET_S` (default 120 s) of wall clock, warmup excluded.

Run: `uv run python train.py` from this directory. Extract the metric: `grep "^val_bpb:" run.log`.

Baseline (this machine): see eval-report.md.
