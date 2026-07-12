---
name: read
description: Deep-read a paper (arXiv id, PDF path, or URL) into structured notes in the store. Use when asked to read, ingest, or summarize a specific paper.
---

# /read <arxiv-id|pdf-path|url>

1. Resolve the paper. arXiv id or URL: fetch title/authors/year/abstract from the abs page and download the PDF to `papers/<id>/paper.pdf`. Local PDF: use as-is; slug = kebab-case short title. `<id>` = arXiv id without version, or the slug.
2. Write `papers/<id>/meta.yaml`: `id, title, authors, year, url, type, tags, status: read`. Classify `type` as `empirical`, `theoretical`, or `systems` from the abstract. Choose 1-4 lowercase topic tags (e.g., `llm`, `audio`, `mlops`).
3. Append/update the paper's line in `papers/index.jsonl` (keys: id, title, year, type, tags, status, dir).
4. Dispatch the `paper-reader` subagent with the PDF path, the type, and the matching template below. Write its output to `papers/<id>/notes.md` with frontmatter:

   ```
   ---
   paper: "<id>"
   verification: draft
   ---
   ```

5. Set status to `noted` in both meta.yaml and index.jsonl.
6. For each tag, merge a 2-5 sentence takeaway into `notes/topics/<tag>.md` (create with `# <tag>` heading if missing), citing the paper id.
7. Remove the paper from `queue.md` if listed. Then run:
   - `uv run python scripts/make_bib.py`
   - `uv run python scripts/check_store.py` (fix any violations)

## Templates by type

**empirical**
- Problem and central claim
- Method: what is actually new
- Setup: datasets, baselines, compute
- Headline results: exact numbers with table references
- Ablations that matter
- Limitations and threats to validity
- Relevance to my projects (read profile.md)

**theoretical**
- Problem and central claim
- Assumptions, each with a plausibility note
- Main theorems: informal statement + where proved
- Proof sketch / key technique
- What breaks without each assumption
- Practical implications
- Relevance to my projects (read profile.md)

**systems**
- Problem and central claim
- Architecture
- Bottleneck addressed
- Throughput / latency / cost trade-offs, exact numbers
- Operational complexity and adoption prerequisites
- Limitations
- Relevance to my projects (read profile.md)
