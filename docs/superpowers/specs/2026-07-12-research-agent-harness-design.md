# Research Agent Harness — Design

Date: 2026-07-12
Status: Approved (design review complete)

## Purpose

A personal academic research agent for deep learning, built as a Claude Code harness in this repository plus a small headless component for recurring monitoring. Running `claude` in this repo makes Claude Code the research agent.

## Decisions

| Question | Decision |
|---|---|
| Workflows | All four: literature discovery/survey, deep paper reading, experimentation/code, writing/knowledge base |
| Runtime | Hybrid: Claude Code-native harness + LLM-free headless arXiv watcher on cron |
| Knowledge store | Repo-native file store; polished notes exported to Obsidian LLM-Wiki via existing `make-llm-wiki-raw` → `wikify-raw` pipeline |
| Compute | Local-first (Mac, MPS/CPU scale); experiment layout kept remote-friendly (configs/results as files) so a remote runner can be added without restructuring |
| Topic breadth | Workflow-shaped harness; topics handled as data (profile, tags, accumulated topic notes), not as per-topic agents |

## Core architecture principle

Research procedures are topic-invariant; the axis that changes agent behavior is **paper type**, not topic:

- Empirical papers → extract setup, baselines, ablations, claims
- Theoretical papers → extract assumptions, theorems, proof sketches, limitations
- Systems/MLOps papers → extract architecture, bottlenecks, throughput trade-offs

Topics (LLM, vision, audio, MLOps, ...) are lightweight tags plus per-topic knowledge notes that accumulate as papers are read. A paper can carry multiple tags; no forced hierarchy. The base model already knows the field; the harness supplies the user's context via files.

## Repository layout

```
oh-my-postgraduate/
├── CLAUDE.md            # harness constitution: store schema, conventions, behavior rules
├── profile.md           # research interests, active projects, priorities (user-edited)
├── papers/
│   ├── index.jsonl      # one line per paper: id, title, year, tags, type, status
│   └── <arxiv-id>/
│       ├── paper.pdf
│       ├── meta.yaml    # bibliographic data + topic tags + paper type
│       └── notes.md     # structured reading notes (type-specific template)
├── notes/
│   ├── topics/<t>.md    # accumulated per-topic synthesis
│   └── syntheses/       # survey outputs, cross-paper comparisons
├── queue.md             # reading queue: priority + reason queued
├── inbox/               # raw candidates from arxiv watcher, pre-triage
├── experiments/<slug>/  # README (goal, linked paper, status), config/, src/, results/
├── bib/references.bib   # generated; single source of truth for citations
├── .claude/
│   ├── skills/          # workflow skills
│   └── agents/          # subagents
└── scripts/
    ├── arxiv_watch.py   # headless fetcher (no LLM)
    ├── check_store.py   # store invariant lint
    └── watch.sh         # cron/launchd entry
```

All state is plain files in git: every agent action is diffable and revertible.

Paper lifecycle: `discovered → queued → read → noted → exported`.
Separately, each `notes.md` carries a verification status in frontmatter (`draft` | `verified`); claim-verifier flips it, and only `verified` notes may be exported.
`papers/index.jsonl` is the greppable catalog; `meta.yaml` is per-paper truth. `profile.md` is loaded every session and contains an explicit `watch:` section (arXiv categories + keyword list) that the headless watcher parses literally — no NLP in the script.

## Skills (workflow verbs)

- `/survey <question>` — fan-out search (arXiv API, Semantic Scholar, web), dedupe, rank against `profile.md`, write cited synthesis to `notes/syntheses/`, queue candidates.
- `/read <arxiv-id|pdf|url>` — ingest paper, detect paper type, apply type-specific extraction template, write `notes.md`, update topic notes and index.
- `/reproduce <paper>` — scaffold `experiments/<slug>/` from the paper's notes; local-first (uv), configs as files.
- `/triage` — rank `inbox/` candidates against profile, update `queue.md`. Used interactively and by the headless run.
- `/wiki-export [paper|topic]` — polish verified notes and hand off to the `make-llm-wiki-raw` → `wikify-raw` pipeline.
- `/status` — dashboard: queue, in-flight experiments, recent notes.

## Subagents

- **paper-scout** — read-only parallel multi-source search (arXiv, Semantic Scholar, web).
- **paper-reader** — deep-reads one paper in an isolated context so large PDFs never flood the main session; returns structured notes.
- **claim-verifier** — adversarial check that note claims (numbers, dataset names, what the authors actually showed) match the source paper. Gate before Obsidian export. Exists because fabricated numbers/citations are the primary failure mode of research agents.

## Headless component

`scripts/arxiv_watch.py` is deliberately LLM-free: pulls new arXiv listings for the categories and keywords listed in `profile.md`'s `watch:` section, diffs against `papers/index.jsonl`, writes candidates to `inbox/`. A daily launchd/cron job runs it, then `claude -p "/triage"` performs the judgment step. Deterministic fetch and LLM triage stay separate: cheap to run, independently debuggable.

## Error handling

- Fetch failures (arXiv/S2 down) leave `inbox/` untouched; triage skips missing data gracefully.
- Notes remain `status: draft` until claim-verifier passes; only verified notes are exported to Obsidian.
- `scripts/check_store.py` lints store invariants (index ↔ directory consistency, required note sections, schema validity); runs during triage.
- Git provides rollback for any agent action.

## Testing

- `arxiv_watch.py`, `check_store.py`, and BibTeX generation: pytest with recorded fixtures.
- Skills: validated by running each on a known paper of each type (one empirical, one theoretical, one systems) and checking store invariants afterward.

## Out of scope (for now)

- Remote GPU job orchestration (layout is remote-friendly; runner added later).
- Per-topic specialist subagents (revisit only if data shows a topic needs procedural depth beyond paper-type modes).
- Any UI beyond Claude Code itself.
