---
name: triage
description: Rank inbox candidates against the research profile and update the reading queue. Use after the arXiv watcher runs, or when asked to triage or process the inbox.
---

# /triage

1. Read `profile.md` (Interests, Active projects) and every `inbox/*.md` file (YAML frontmatter: id, title, authors, published, url; body: abstract).
2. Score each candidate: high / medium / low relevance, with a one-line reason grounded in the profile.
3. Apply:
   - high: add to `queue.md` under `## High` as `- <id> — <title> — <reason>`; create `papers/<id>/meta.yaml` (status: `queued`, type + tags from abstract) and the matching `papers/index.jsonl` line.
   - medium: add to `queue.md` under `## Maybe` (no store entry).
   - low: drop.
4. Delete every processed inbox file.
5. Run `uv run python scripts/check_store.py`; fix violations.
6. Report counts: queued / maybe / dropped, and the top pick with reason.
