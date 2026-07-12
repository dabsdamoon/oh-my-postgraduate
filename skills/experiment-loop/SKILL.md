---
name: experiment-loop
description: Autonomous keep/discard experiment iteration against a single machine-readable metric with a fixed per-run budget. Use when iterating on any experiment whose script prints its metric — model training, benchmark tuning, optimizer comparisons.
---

# Experiment loop

Hill-climb a single metric by repeatedly editing one file, running it under a fixed
budget, and keeping or discarding the change by rule. Adapted from
[karpathy/autoresearch](https://github.com/karpathy/autoresearch); validated in a
controlled before/after evaluation (4.7x faster iteration, 4.5x more metric improvement
per minute, complete audit trail — see `docs/report/2026-07-12-experiment-loop-evaluation.md`
in the oh-my-postgraduate repo).

## Setup — declare before the first run

Write these in the experiment's log or README; they are fixed for the session:

- **Metric**: its name exactly as the script prints it (e.g. `val_bpb`), and its direction
  (lower or higher is better). The evaluation code that computes it is read-only.
- **Budget**: the fixed per-run cost (wall-clock seconds or step count), identical for
  every run so results are comparable.
- **Scope**: the one file experiments may modify. Everything else — data prep, the metric,
  dependencies — is read-only. No new packages.
- **Cap**: the run count or total time at which the session stops.

## The loop

1. The first run is always the unmodified baseline; it sets the number to beat.
2. Each iteration:
   - Make ONE experimental change.
   - Commit it (short message stating the idea; stage the specific file).
   - Run: `<runner> <script> > run.log 2>&1` — redirect everything; never tee or stream
     the output into context. Remove any stale `run.log` first (noclobber shells refuse
     the redirect and the run silently never happens).
   - Read the result: `grep "^<metric>:" run.log`.
   - Improved beyond the noise floor: keep — the branch advances.
     Not improved: undo the commit (see Reverting below).
   - Append to `results.tsv` (tab-separated, header `commit	<metric>	status	description`):
     short commit hash, metric value (0.0 for crashes), status `keep | discard | crash`,
     one-line description of the idea.
3. Stop only at the declared cap; then report the best metric, the kept changes, and the
   `results.tsv` path.

## Noise guard

Run-to-run variance is real (thermal throttling, system load) and un-guarded keeps near
the noise floor are coin flips.

- Establish the floor early: once, re-run an identical configuration; the absolute
  difference approximates the noise floor. Record it.
- A change that improves by less than the floor is not yet an improvement: replicate it
  once and keep only if the mean of both runs still beats the incumbent; otherwise discard.

## Crash rule

Empty grep means the run crashed. `tail -n 50 run.log`; if the fix is trivial (typo,
missing import), fix and re-run once; otherwise log `crash` in `results.tsv`, revert,
and move on to the next idea.

## Kill rule

Kill any run exceeding 2x the budget; log it as `crash`.

## Reverting

Prefer `git revert` over `git reset --hard`: revert preserves the discarded experiment in
history, so failed ideas remain inspectable and are not accidentally retried. Use reset
only when history noise matters more than the audit trail.

## Autonomy

Once the loop has begun, do not pause to ask whether to continue. If out of ideas: re-read
the in-scope file for untried angles, combine previous near-misses, or attempt one larger
structural change. Stop only at the declared cap.
