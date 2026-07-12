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
