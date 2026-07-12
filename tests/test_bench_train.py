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
