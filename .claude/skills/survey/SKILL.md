---
name: survey
description: Literature survey on a research question — parallel search fan-out, ranking, cited synthesis. Use for "what is the state of X", "find papers about Y", "survey Z".
---

# /survey <question>

1. Read `profile.md`. Decompose the question into 2-4 distinct search angles (different phrasings, subproblems, or adjacent fields).
2. Dispatch one `paper-scout` subagent per angle, in parallel. Each returns a JSON array of candidates.
3. Dedupe by arXiv id, then by normalized title. Rank by relevance to the question first, profile second.
4. Write `notes/syntheses/YYYY-MM-DD-<slug>.md`:
   - The question and the queries used
   - Themes, each grounded in specific papers cited as `[arxiv:<id>]`
   - One-paragraph summary per key paper (from scout findings and abstracts — mark anything deeper as "needs /read")
   - Open questions and disagreements between papers
   - Reading recommendations, ordered
5. Add top recommendations to `queue.md` under `## High` with reasons.
6. Cite only papers a scout actually returned. Never add citations from memory.
