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
