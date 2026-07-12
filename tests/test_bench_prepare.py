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
