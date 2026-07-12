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
