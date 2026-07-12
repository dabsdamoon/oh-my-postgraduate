# Experiment-Loop Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Mac-runnable char-LM benchmark, port autoresearch's experiment loop into `/reproduce`, run the workflow before and after the change, and report the comparison.

**Architecture:** `bench/tiny-lm/` mirrors autoresearch's two-file split — `prepare.py` fixed (data, metric, constants), `train.py` agent-editable (model, training loop). Two sequential subagent arms on separate git branches from one baseline commit; a final report on `main` compares them.

**Tech Stack:** Python 3.12, uv, PyTorch (MPS/CPU), pytest, stdlib urllib.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-12-repro-loop-eval-design.md`.
- `TIME_BUDGET_S = 120` default, env-overridable; tests use `TIME_BUDGET_S=5`.
- Arm caps: 8 training runs or 35 min wall clock, whichever first; baseline counts as run 1.
- Metric: `val_bpb`, lower is better; `evaluate_bpb` in `prepare.py` is ground truth and read-only.
- `torch` goes in a `bench` dependency group after the package-safety check; no other new deps.
- `bench/tiny-lm/data/` is gitignored. The paper store and `check_store.py` are untouched.
- Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: torch dependency and gitignore

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

**Interfaces:**
- Produces: importable `torch` in the uv environment for all later tasks.

- [ ] **Step 1: Package-safety check** — verify `torch` on PyPI (publisher PyTorch, latest stable version, no fresh supply-chain advisories) and report findings before installing.

Run: `curl -s https://pypi.org/pypi/torch/json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['info']['version'], d['info']['author'] or d['info']['maintainer'])"`

- [ ] **Step 2: Add the dependency group**

Run: `uv add --group bench torch`
Expected: resolves and installs a macOS arm64 wheel.

- [ ] **Step 3: Verify import and device**

Run: `uv run python -c "import torch; print(torch.__version__, torch.backends.mps.is_available())"`
Expected: version string and `True` (or `False` → CPU fallback, still fine).

- [ ] **Step 4: Gitignore the corpus**

Append to `.gitignore`:

```
bench/tiny-lm/data/
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .gitignore
git commit -m "Add torch bench dependency group"
```

---

### Task 2: prepare.py (fixed benchmark scaffolding)

**Files:**
- Create: `bench/tiny-lm/prepare.py`
- Test: `tests/test_bench_prepare.py`

**Interfaces:**
- Produces: `TIME_BUDGET_S`, `MAX_SEQ_LEN`, `download() -> Path`, `load_data() -> (train_ids, val_ids, stoi, itos, bytes_per_token)`, `get_batch(data, batch_size, seq_len, device, generator=None) -> (x, y)`, `evaluate_bpb(model, val_ids, device, bytes_per_token) -> float`, `pick_device() -> torch.device`.

- [ ] **Step 1: Write the failing tests**

```python
import math
import sys
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).parent.parent / "bench" / "tiny-lm"))

import prepare


def test_vocab_round_trip():
    _, _, stoi, itos, _ = prepare.load_data()
    assert all(itos[stoi[c]] == c for c in stoi)
    assert len(stoi) == len(itos)


def test_get_batch_shapes_and_alignment():
    train_ids, _, _, _, _ = prepare.load_data()
    g = torch.Generator().manual_seed(0)
    x, y = prepare.get_batch(train_ids, 4, 16, torch.device("cpu"), g)
    assert x.shape == (4, 16) and y.shape == (4, 16)
    assert x.dtype == torch.long and y.dtype == torch.long
    assert torch.equal(x[:, 1:], y[:, :-1])


class UniformModel(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.vocab_size = vocab_size
        self.dummy = nn.Parameter(torch.zeros(1))

    def forward(self, idx):
        return torch.zeros(*idx.shape, self.vocab_size)


def test_evaluate_bpb_uniform_model():
    _, val_ids, stoi, _, bytes_per_token = prepare.load_data()
    bpb = prepare.evaluate_bpb(UniformModel(len(stoi)), val_ids, torch.device("cpu"), bytes_per_token)
    assert math.isclose(bpb, math.log2(len(stoi)) / bytes_per_token, rel_tol=1e-5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bench_prepare.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prepare'`

- [ ] **Step 3: Write prepare.py**

```python
"""Fixed benchmark scaffolding: data, vocab, dataloader, evaluation, constants.

Do not modify this file during experiments. evaluate_bpb is the ground-truth metric.
"""

import math
import os
import urllib.request
from pathlib import Path

import torch

DATA_URL = "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"
DATA_DIR = Path(__file__).parent / "data"
TIME_BUDGET_S = float(os.environ.get("TIME_BUDGET_S", 120))
MAX_SEQ_LEN = 256
VAL_FRACTION = 0.1
EVAL_BATCHES = 20
EVAL_BATCH_SIZE = 32


def download() -> Path:
    path = DATA_DIR / "input.txt"
    if not path.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(DATA_URL, path)
        except OSError as e:
            raise RuntimeError(f"failed to download {DATA_URL}") from e
    return path


def load_data():
    text = download().read_text()
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    itos = {i: c for i, c in enumerate(chars)}
    ids = torch.tensor([stoi[c] for c in text], dtype=torch.long)
    split = int(len(ids) * (1 - VAL_FRACTION))
    bytes_per_token = len(text.encode()) / len(text)
    return ids[:split], ids[split:], stoi, itos, bytes_per_token


def get_batch(data, batch_size, seq_len, device, generator=None):
    ix = torch.randint(len(data) - seq_len - 1, (batch_size,), generator=generator)
    x = torch.stack([data[i : i + seq_len] for i in ix])
    y = torch.stack([data[i + 1 : i + seq_len + 1] for i in ix])
    return x.to(device), y.to(device)


@torch.no_grad()
def evaluate_bpb(model, val_ids, device, bytes_per_token) -> float:
    model.eval()
    generator = torch.Generator().manual_seed(1337)
    total = 0.0
    for _ in range(EVAL_BATCHES):
        x, y = get_batch(val_ids, EVAL_BATCH_SIZE, MAX_SEQ_LEN, device, generator)
        logits = model(x)
        loss = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
        total += loss.item()
    model.train()
    mean_nats = total / EVAL_BATCHES
    return mean_nats / math.log(2) / bytes_per_token


def pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_bench_prepare.py -v`
Expected: 3 passed (first run downloads the 1.1 MB corpus).

- [ ] **Step 5: Commit**

```bash
git add bench/tiny-lm/prepare.py tests/test_bench_prepare.py
git commit -m "Add tiny-lm benchmark scaffolding"
```

---

### Task 3: train.py baseline

**Files:**
- Create: `bench/tiny-lm/train.py`
- Test: `tests/test_bench_train.py`

**Interfaces:**
- Consumes: everything from `prepare.py` (Task 2).
- Produces: `uv run python train.py` (cwd `bench/tiny-lm/`) prints a summary block where `grep "^val_bpb:"` yields the metric.

- [ ] **Step 1: Write the failing smoke test**

```python
import math
import os
import re
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).parent.parent / "bench" / "tiny-lm"


def test_smoke_run():
    result = subprocess.run(
        [sys.executable, "train.py"],
        cwd=BENCH,
        env={**os.environ, "TIME_BUDGET_S": "5"},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    m = re.search(r"^val_bpb:\s+([\d.]+)$", result.stdout, re.M)
    assert m, result.stdout
    bpb = float(m.group(1))
    assert math.isfinite(bpb) and 0 < bpb < 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bench_train.py -v`
Expected: FAIL (train.py does not exist, returncode != 0).

- [ ] **Step 3: Write train.py**

```python
"""Baseline model and training loop. Experiments modify this file."""

import time

import torch
import torch.nn as nn
import torch.nn.functional as F

from prepare import (
    MAX_SEQ_LEN,
    TIME_BUDGET_S,
    evaluate_bpb,
    get_batch,
    load_data,
    pick_device,
)

DEPTH = 4
N_EMBD = 256
N_HEAD = 8
BATCH_SIZE = 32
SEQ_LEN = MAX_SEQ_LEN
LR = 3e-4
WEIGHT_DECAY = 0.1


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(N_EMBD)
        self.attn = nn.Linear(N_EMBD, 3 * N_EMBD)
        self.proj = nn.Linear(N_EMBD, N_EMBD)
        self.ln2 = nn.LayerNorm(N_EMBD)
        self.mlp = nn.Sequential(
            nn.Linear(N_EMBD, 4 * N_EMBD), nn.GELU(), nn.Linear(4 * N_EMBD, N_EMBD)
        )

    def forward(self, x):
        b, t, c = x.shape
        q, k, v = self.attn(self.ln1(x)).split(N_EMBD, dim=2)
        q = q.view(b, t, N_HEAD, c // N_HEAD).transpose(1, 2)
        k = k.view(b, t, N_HEAD, c // N_HEAD).transpose(1, 2)
        v = v.view(b, t, N_HEAD, c // N_HEAD).transpose(1, 2)
        att = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(att.transpose(1, 2).contiguous().view(b, t, c))
        x = x + self.mlp(self.ln2(x))
        return x


class GPT(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, N_EMBD)
        self.pos_emb = nn.Embedding(MAX_SEQ_LEN, N_EMBD)
        self.blocks = nn.ModuleList(Block() for _ in range(DEPTH))
        self.ln_f = nn.LayerNorm(N_EMBD)
        self.lm_head = nn.Linear(N_EMBD, vocab_size, bias=False)

    def forward(self, idx):
        b, t = idx.shape
        x = self.tok_emb(idx) + self.pos_emb(torch.arange(t, device=idx.device))
        for block in self.blocks:
            x = block(x)
        return self.lm_head(self.ln_f(x))


def main():
    t_start = time.monotonic()
    device = pick_device()
    train_ids, val_ids, stoi, itos, bytes_per_token = load_data()
    model = GPT(len(stoi)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    def step():
        x, y = get_batch(train_ids, BATCH_SIZE, SEQ_LEN, device)
        logits = model(x)
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        return loss

    step()  # warmup: compilation and first-touch allocations, excluded from the budget
    t0 = time.monotonic()
    num_steps = 0
    while time.monotonic() - t0 < TIME_BUDGET_S:
        loss = step()
        num_steps += 1
        if num_steps % 20 == 0:
            loss.item()  # sync so the wall-clock check reflects real device time
    training_seconds = time.monotonic() - t0

    val_bpb = evaluate_bpb(model, val_ids, device, bytes_per_token)
    num_params = sum(p.numel() for p in model.parameters())
    print("---")
    print(f"val_bpb:          {val_bpb:.6f}")
    print(f"training_seconds: {training_seconds:.1f}")
    print(f"total_seconds:    {time.monotonic() - t_start:.1f}")
    print(f"num_steps:        {num_steps}")
    print(f"total_tokens_M:   {num_steps * BATCH_SIZE * SEQ_LEN / 1e6:.1f}")
    print(f"num_params_M:     {num_params / 1e6:.1f}")
    print(f"depth:            {DEPTH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the smoke test**

Run: `uv run pytest tests/test_bench_train.py -v`
Expected: 1 passed (roughly 30-60 s: 5 s training plus eval and startup).

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest`
Expected: all pass (17 existing + 4 new).

- [ ] **Step 6: Commit**

```bash
git add bench/tiny-lm/train.py tests/test_bench_train.py
git commit -m "Add tiny-lm baseline model and training loop"
```

---

### Task 4: benchmark README and full baseline run

**Files:**
- Create: `bench/tiny-lm/README.md`

**Interfaces:**
- Produces: the baseline commit both arms branch from; the baseline `val_bpb` number.

- [ ] **Step 1: Write README.md**

```markdown
# tiny-lm benchmark

Char-level LM speedrun on tiny-shakespeare, autoresearch-style, scaled to Apple Silicon.

- `prepare.py` — data, vocab, dataloader, `evaluate_bpb` (ground-truth metric), constants. Read-only during experiments.
- `train.py` — model, optimizer, training loop. The file experiments modify.
- Metric: `val_bpb` (validation bits per byte), lower is better.
- Budget: each run trains for a fixed `TIME_BUDGET_S` (default 120 s) of wall clock, warmup excluded.

Run: `uv run python train.py` from this directory. Extract the metric: `grep "^val_bpb:" run.log`.

Baseline (this machine): see eval-report.md.
```

- [ ] **Step 2: Run the full-budget baseline**

Run: `cd bench/tiny-lm && uv run python train.py > baseline.log 2>&1 && grep "^val_bpb:" baseline.log`
Expected: finishes in ~2.5 min, prints the baseline val_bpb. Record the number.

- [ ] **Step 3: Commit (baseline.log stays untracked)**

```bash
git add bench/tiny-lm/README.md
git commit -m "Add tiny-lm benchmark README and baseline"
```

---

### Task 5: /reproduce experiment-loop upgrade

**Files:**
- Modify: `.claude/skills/reproduce/SKILL.md`

**Interfaces:**
- Produces: the loop protocol text that Arm B receives verbatim.

- [ ] **Step 1: Append the loop section to SKILL.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/reproduce/SKILL.md
git commit -m "Port autoresearch experiment loop into /reproduce"
```

---

### Task 6: Arm A (before — freeform iteration)

**Files:**
- Create (by the arm): edits to `bench/tiny-lm/train.py` on branch `bench/arm-a`, plus whatever log the arm keeps.

- [ ] **Step 1: Cut the branch** — `git checkout -b bench/arm-a` (from the Task 5 commit on main; note the timestamp).
- [ ] **Step 2: Dispatch a general-purpose subagent, synchronously,** with the Arm A prompt: goal lowest `val_bpb`; edit only `bench/tiny-lm/train.py`; `prepare.py` and the metric read-only; no new dependencies; max 8 training runs total including the baseline; keep a freeform log of what you try in `bench/tiny-lm/arm-a-log.md`; iterate however you see fit; do not read `.claude/skills/`; do not push; report per-run results and the best number.
- [ ] **Step 3: Capture final state** — commit any uncommitted work on `bench/arm-a` as `Arm A final state`; record wall-clock duration; `git checkout main`.

---

### Task 7: Arm B (after — autoresearch loop)

**Files:**
- Create (by the arm): commits on branch `bench/arm-b`, `bench/tiny-lm/results.tsv`.

- [ ] **Step 1: Cut the branch** — `git checkout -b bench/arm-b main` (same baseline; note the timestamp).
- [ ] **Step 2: Dispatch a general-purpose subagent, synchronously,** with the Arm B prompt: same framing as Arm A (goal, read-only files, no deps, max 8 runs including baseline, no push) plus the Task 5 loop protocol verbatim with `<metric>` = `val_bpb` and `<script>` = `train.py`, results in `bench/tiny-lm/results.tsv` (keep untracked until the arm ends).
- [ ] **Step 3: Capture final state** — commit `results.tsv` on `bench/arm-b` as `Arm B final state`; record wall-clock duration; `git checkout main`.

---

### Task 8: Comparison report

**Files:**
- Create: `bench/tiny-lm/eval-report.md`

- [ ] **Step 1: Collect artifacts** — from both branches: per-run metrics and descriptions (arm logs, results.tsv, commit history with timestamps), final `train.py` diffs vs baseline (`git diff main..bench/arm-a -- bench/tiny-lm/train.py`, same for arm-b).
- [ ] **Step 2: Write eval-report.md** with sections: Setup (machine, budget, caps, baseline val_bpb); Results table per arm (run, idea, val_bpb, decision); Speed (wall clock per arm, per-iteration overhead); Accuracy (baseline → best per arm); Complexity (net LOC delta, unattributed kept changes); Edge cases (crashes/regressions encountered vs detected vs correctly discarded); Auditability (fraction of results traceable to a commit); Verdict and the single-session caveat.
- [ ] **Step 3: Run the full test suite** — `uv run pytest` on main, all pass (arms only touched branches).
- [ ] **Step 4: Commit**

```bash
git add bench/tiny-lm/eval-report.md docs/superpowers/specs/2026-07-12-repro-loop-eval-design.md docs/superpowers/plans/2026-07-12-repro-loop-eval.md
git commit -m "Evaluate experiment-loop upgrade before/after on tiny-lm"
```
