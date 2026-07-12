---
name: status
description: Research dashboard — inbox, queue, experiments, recent activity. Use when asked "status", "where am I", or "what should I read next".
---

# /status

1. Gather: `inbox/` file count; `queue.md` items; `papers/index.jsonl` status counts; `experiments/*/README.md` statuses; recently modified `notes/topics/*.md` (git log, last 14 days).
2. Report, in order:
   - Inbox awaiting triage (count; suggest /triage if > 0)
   - Top 5 queue items with reasons
   - Papers by status (one line)
   - Experiments not `done`, one line each
   - Recently active topics
3. End with the single most valuable next action, with a one-line justification.
