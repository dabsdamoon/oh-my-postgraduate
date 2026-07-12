---
name: reproduce
description: Scaffold a local-first experiment to reproduce a paper's central claim. Use when asked to reproduce, implement, or run experiments from a paper.
---

# /reproduce <paper-id>

1. Read `papers/<id>/notes.md` and `meta.yaml`. If notes are missing, run /read first.
2. Identify the paper's central claim and design the smallest experiment that tests it at local scale (Mac, MPS/CPU): subset of the dataset, reduced model config, shortened schedule. State explicitly what the scaled-down result can and cannot confirm.
3. Scaffold `experiments/<slug>/` (slug: short kebab-case):
   - `README.md`: goal, linked paper id, central claim under test, success criterion, status (`planned`), log section
   - `config/base.yaml`: every hyperparameter and path as data — nothing hardcoded in code
   - `src/`: minimal implementation; use the repo's uv environment; add deps to pyproject.toml only after the package-safety check
   - `results/`: metrics written as `results/metrics.jsonl`, plots as files
4. Keep the layout remote-friendly: code reads config paths relative to the experiment dir, results land in `results/` — a remote runner can later execute the same layout unchanged.
5. Update README status as work progresses: planned -> running -> done | blocked, with findings vs the paper's claim (exact numbers, both sides).

## Experiment loop (iterating on a scaffolded experiment)

Once the experiment has a script that prints a single machine-readable metric, iterate with this loop. Declare up front in the experiment README: the metric name exactly as printed, its direction, and the fixed per-run budget.

1. The first run is always the unmodified baseline; it sets the number to beat.
2. Each iteration:
   - Make one experimental change to the code.
   - `git commit` it (short message stating the idea).
   - Run: `uv run python <script> > run.log 2>&1` — never tee output into context.
   - Read the result: `grep "^<metric>:" run.log`.
   - Improved: keep; the branch advances. Not improved: `git reset --hard HEAD~1`.
   - Append to `results.tsv` (tab-separated, header `commit	<metric>	status	description`): short commit hash, metric value (0.0 for crashes), status `keep | discard | crash`, one-line description of the idea.
3. Crash rule: empty grep means the run crashed. `tail -n 50 run.log`; if the fix is trivial (typo, import), fix and re-run once; otherwise log `crash`, revert, move on.
4. Kill rule: kill any run exceeding 2x the budget; log it as `crash`.
5. Stop only at the declared run or time cap; then report the best metric, the kept changes, and the results.tsv path.
