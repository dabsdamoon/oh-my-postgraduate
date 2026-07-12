---
name: wiki-export
description: Export verified paper notes or a topic synthesis to the Obsidian LLM-Wiki. Use when asked to export, publish, or wikify notes.
---

# /wiki-export <paper-id | topic:<name>>

1. Paper export: read `papers/<id>/notes.md`.
   - If `verification: draft`: dispatch `claim-verifier` with the notes path and paper PDF/URL. If it returns mismatches, fix the notes against the paper, then re-dispatch until `VERIFIED`. Set `verification: verified`.
2. Topic export: read `notes/topics/<name>.md`; verify that each cited paper id exists in the index (drop or fix citations that do not).
3. Polish for human reading: prose over fragments, keep every location reference and citation.
4. Hand off via the existing pipeline: invoke the `make-llm-wiki-raw` skill with the polished content, then follow with `wikify-raw`.
5. For papers: set status `exported` in meta.yaml and index.jsonl; run `uv run python scripts/check_store.py`.
