# Research Agent Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Claude Code-native research agent harness specified in `docs/superpowers/specs/2026-07-12-research-agent-harness-design.md`: file store, six workflow skills, three subagents, and an LLM-free arXiv watcher.

**Architecture:** Workflow-shaped harness; topics are data (profile, tags, topic notes). Paper *type* (empirical/theoretical/systems) selects the reading template. All state is plain files in git. Deterministic Python scripts handle fetch/lint/bib; LLM judgment lives in skills and subagents.

**Tech Stack:** Python 3.12+ managed by uv; PyYAML (only runtime dep); pytest (dev); stdlib urllib + xml.etree for arXiv API; Claude Code skills/agents as markdown.

## Global Constraints

- Paper status values exactly: `discovered | queued | read | noted | exported`.
- Paper type values exactly: `empirical | theoretical | systems`.
- Notes verification values exactly: `draft | verified`; only `verified` notes may be exported.
- `arxiv_watch.py` contains no LLM calls; it parses the fenced YAML block under `## Watch` in `profile.md` literally.
- Python: type hints, `pathlib`, f-strings, pytest, no mocks (tests use tmp_path + fixture files).
- No emojis anywhere.
- Git: stage specific files; concise imperative commit messages; end commit messages with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`; never push unless asked.
- PDFs are not committed (gitignored); notes and metadata are the durable content.

---

### Task 1: Repo bootstrap (git, remote, Python project)

**Files:**
- Create: `.gitignore`, `pyproject.toml`
- Existing: `docs/superpowers/specs/2026-07-12-research-agent-harness-design.md`, `docs/superpowers/plans/2026-07-12-research-agent-harness.md`

**Interfaces:**
- Produces: a git repo on branch `main` with remote `origin = git@github.com:dabsdamoon/oh-my-postgraduate.git`; `uv run python`/`uv run pytest` working with pyyaml + pytest available.

- [ ] **Step 1: git init and remote**

```bash
git init -b main
git remote add origin git@github.com:dabsdamoon/oh-my-postgraduate.git
git remote -v
```
Expected: both fetch/push lines show the SSH URL.

- [ ] **Step 2: Write `.gitignore`**

```gitignore
__pycache__/
.pytest_cache/
.venv/
.DS_Store
papers/*/paper.pdf
```

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[project]
name = "oh-my-postgraduate"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pyyaml>=6.0.2"]

[dependency-groups]
dev = ["pytest>=8.0"]
```

- [ ] **Step 4: Package-safety check, then sync**

Per global package-safety rules, verify `pyyaml` and `pytest` on PyPI (publisher, downloads, no typosquat) and report findings before installing. Then:

```bash
uv sync
uv run python -c "import yaml; print(yaml.__version__)"
```
Expected: prints 6.x.

- [ ] **Step 5: Commit**

```bash
git add .gitignore pyproject.toml uv.lock docs/
git commit -m "Bootstrap research agent harness repo with spec and plan"
```

---

### Task 2: Store skeleton, CLAUDE.md, profile.md

**Files:**
- Create: `CLAUDE.md`, `profile.md`, `queue.md`, `papers/index.jsonl` (empty), `.gitkeep` in `notes/topics/`, `notes/syntheses/`, `inbox/`, `experiments/`, `bib/`

**Interfaces:**
- Produces: the store layout every later task assumes; `profile.md`'s `## Watch` fenced YAML block with keys `categories` (list), `keywords` (list), `max_results` (int) — parsed by Task 5's `parse_watch()`.

- [ ] **Step 1: Create directories and empty files**

```bash
mkdir -p papers notes/topics notes/syntheses inbox experiments bib
touch papers/index.jsonl notes/topics/.gitkeep notes/syntheses/.gitkeep inbox/.gitkeep experiments/.gitkeep bib/.gitkeep
```

- [ ] **Step 2: Write `CLAUDE.md`**

```markdown
# oh-my-postgraduate

Personal deep learning research agent harness. Running `claude` here makes Claude Code the research agent.

## First actions each session

- Read `profile.md` (interests, active projects, watch config).
- Read `queue.md` when the task involves reading or triage.

## Store schema

- `papers/index.jsonl` — catalog; one JSON object per line: `{"id", "title", "year", "type", "tags", "status", "dir"}`.
- `papers/<id>/meta.yaml` — per-paper truth: `id, title, authors, year, url, type, tags, status`. Wins over index on conflict.
- `papers/<id>/notes.md` — reading notes; YAML frontmatter `paper: <id>`, `verification: draft|verified`.
- `notes/topics/<topic>.md` — accumulated topic syntheses (one per tag, grows as papers are read).
- `notes/syntheses/` — survey outputs.
- `queue.md` — reading queue (`## High`, `## Maybe` sections; each item: id, title, reason).
- `inbox/` — pre-triage candidates written by `scripts/arxiv_watch.py`.
- `experiments/<slug>/` — `README.md` (goal, linked paper, status), `config/`, `src/`, `results/`.
- `bib/references.bib` — generated by `uv run python scripts/make_bib.py`; never edit by hand.

## Lifecycle and invariants

- Paper status: `discovered -> queued -> read -> noted -> exported`.
- Paper type: `empirical | theoretical | systems`. Type selects the reading template; topics are tags.
- `notes.md` starts as `verification: draft`. Only the claim-verifier subagent may flip it to `verified`. Only verified notes may be exported.
- After any store mutation, run `uv run python scripts/check_store.py` and fix violations before finishing the task.

## Behavior rules

- Topics are tags plus `notes/topics/` files. Never create per-topic agents.
- Never state numbers or citations without a location reference in the source paper; the claim-verifier gates export.
- Use subagents: `paper-scout` for search fan-out, `paper-reader` for whole-PDF reading, `claim-verifier` before export.
- Experiments are local-first (uv, MPS/CPU scale); all parameters in config files, results as files, so a remote runner can be added later.
- Regenerate `bib/references.bib` after adding or editing paper metadata.
```

- [ ] **Step 3: Write `profile.md`**

````markdown
# Research Profile

Edit by hand; the agent reads this every session.

## Interests

- (fill in, one per line: e.g., efficient LLM inference)

## Active projects

- (fill in: project name — one-line goal)

## Watch

The arXiv watcher parses the fenced YAML block below literally.

```yaml
categories:
  - cs.LG
keywords: []
max_results: 50
```
````

- [ ] **Step 4: Write `queue.md`**

```markdown
# Reading Queue

## High

## Maybe
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md profile.md queue.md papers notes inbox experiments bib
git commit -m "Add store skeleton, harness constitution, and research profile"
```

---

### Task 3: check_store.py (store invariant lint)

**Files:**
- Create: `scripts/check_store.py`
- Test: `tests/test_check_store.py`

**Interfaces:**
- Produces: `check_store(root: Path) -> list[str]` (violation strings, empty when clean); CLI `uv run python scripts/check_store.py [root]` exiting 0/1; `read_frontmatter(path: Path) -> dict` (reused conceptually by skills, not imported elsewhere).

- [ ] **Step 1: Write failing tests**

`tests/test_check_store.py`:

```python
import json
from pathlib import Path

import yaml

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from check_store import check_store


def make_paper(root: Path, pid: str, status: str = "noted",
               verification: str = "draft", with_notes: bool = True) -> dict:
    d = root / "papers" / pid
    d.mkdir(parents=True)
    meta = {"id": pid, "title": f"Paper {pid}", "authors": ["A. Author"],
            "year": 2026, "url": f"https://arxiv.org/abs/{pid}",
            "type": "empirical", "tags": ["llm"], "status": status}
    (d / "meta.yaml").write_text(yaml.safe_dump(meta))
    if with_notes:
        (d / "notes.md").write_text(
            f"---\npaper: '{pid}'\nverification: {verification}\n---\n\nnotes\n")
    entry = {"id": pid, "title": meta["title"], "year": 2026, "type": "empirical",
             "tags": ["llm"], "status": status, "dir": f"papers/{pid}"}
    return entry


def write_index(root: Path, entries: list[dict]) -> None:
    (root / "papers").mkdir(parents=True, exist_ok=True)
    (root / "papers" / "index.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in entries))


def test_valid_store_passes(tmp_path):
    e = make_paper(tmp_path, "2401.00001")
    write_index(tmp_path, [e])
    assert check_store(tmp_path) == []


def test_missing_meta_reported(tmp_path):
    e = make_paper(tmp_path, "2401.00002")
    (tmp_path / "papers" / "2401.00002" / "meta.yaml").unlink()
    write_index(tmp_path, [e])
    assert any("meta.yaml missing" in err for err in check_store(tmp_path))


def test_status_mismatch_reported(tmp_path):
    e = make_paper(tmp_path, "2401.00003", status="noted")
    e["status"] = "queued"
    write_index(tmp_path, [e])
    assert any("status mismatch" in err for err in check_store(tmp_path))


def test_exported_requires_verified(tmp_path):
    e = make_paper(tmp_path, "2401.00004", status="exported", verification="draft")
    write_index(tmp_path, [e])
    assert any("verified" in err for err in check_store(tmp_path))


def test_noted_requires_notes(tmp_path):
    e = make_paper(tmp_path, "2401.00005", status="noted", with_notes=False)
    write_index(tmp_path, [e])
    assert any("notes.md missing" in err for err in check_store(tmp_path))


def test_unindexed_dir_reported(tmp_path):
    make_paper(tmp_path, "2401.00006")
    write_index(tmp_path, [])
    assert any("not in index" in err for err in check_store(tmp_path))


def test_bad_status_value_reported(tmp_path):
    e = make_paper(tmp_path, "2401.00007")
    e["status"] = "reading"
    write_index(tmp_path, [e])
    assert any("bad status" in err for err in check_store(tmp_path))
```

- [ ] **Step 2: Run tests, verify failure**

Run: `uv run pytest tests/test_check_store.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'check_store'`.

- [ ] **Step 3: Write `scripts/check_store.py`**

```python
#!/usr/bin/env python3
"""Lint store invariants: index <-> directories, schemas, note verification."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

STATUSES = {"discovered", "queued", "read", "noted", "exported"}
TYPES = {"empirical", "theoretical", "systems"}
VERIFICATIONS = {"draft", "verified"}
INDEX_KEYS = {"id", "title", "year", "type", "tags", "status", "dir"}
META_KEYS = {"id", "title", "authors", "year", "url", "type", "tags", "status"}


def read_frontmatter(path: Path) -> dict:
    text = path.read_text()
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else {}


def load_index(index_path: Path, errors: list[str]) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    if not index_path.exists():
        return entries
    for lineno, line in enumerate(index_path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"index.jsonl:{lineno}: invalid JSON")
            continue
        missing = INDEX_KEYS - entry.keys()
        if missing:
            errors.append(f"index.jsonl:{lineno}: missing keys {sorted(missing)}")
            continue
        if entry["status"] not in STATUSES:
            errors.append(f"index.jsonl:{lineno}: bad status {entry['status']!r}")
        if entry["type"] not in TYPES:
            errors.append(f"index.jsonl:{lineno}: bad type {entry['type']!r}")
        entries[entry["id"]] = entry
    return entries


def check_paper(root: Path, entry: dict, errors: list[str]) -> None:
    pid = entry["id"]
    paper_dir = root / entry["dir"]
    if not paper_dir.is_dir():
        errors.append(f"{pid}: dir {entry['dir']} missing")
        return
    meta_path = paper_dir / "meta.yaml"
    if not meta_path.exists():
        errors.append(f"{pid}: meta.yaml missing")
        return
    meta = yaml.safe_load(meta_path.read_text())
    if not isinstance(meta, dict):
        errors.append(f"{pid}: meta.yaml is not a mapping")
        return
    missing = META_KEYS - meta.keys()
    if missing:
        errors.append(f"{pid}: meta.yaml missing keys {sorted(missing)}")
    if meta.get("id") != pid:
        errors.append(f"{pid}: meta.yaml id {meta.get('id')!r} != index id")
    if meta.get("status") != entry["status"]:
        errors.append(f"{pid}: status mismatch meta={meta.get('status')!r} index={entry['status']!r}")
    notes_path = paper_dir / "notes.md"
    if entry["status"] in {"noted", "exported"} and not notes_path.exists():
        errors.append(f"{pid}: notes.md missing for status {entry['status']}")
    if notes_path.exists():
        fm = read_frontmatter(notes_path)
        verification = fm.get("verification")
        if verification not in VERIFICATIONS:
            errors.append(f"{pid}: notes.md bad verification {verification!r}")
        elif entry["status"] == "exported" and verification != "verified":
            errors.append(f"{pid}: exported but notes not verified")


def check_store(root: Path) -> list[str]:
    errors: list[str] = []
    entries = load_index(root / "papers" / "index.jsonl", errors)
    for entry in entries.values():
        check_paper(root, entry, errors)
    papers_dir = root / "papers"
    if papers_dir.exists():
        indexed_dirs = {root / e["dir"] for e in entries.values()}
        for p in sorted(papers_dir.iterdir()):
            if p.is_dir() and p not in indexed_dirs:
                errors.append(f"{p.name}: paper dir not in index")
    return errors


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    errors = check_store(root)
    for err in errors:
        print(err)
    if errors:
        return 1
    print("store OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests, verify pass**

Run: `uv run pytest tests/test_check_store.py -v`
Expected: 7 passed. Also run `uv run python scripts/check_store.py` at repo root — expected: `store OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_store.py tests/test_check_store.py
git commit -m "Add store invariant lint"
```

---

### Task 4: make_bib.py (BibTeX generation)

**Files:**
- Create: `scripts/make_bib.py`
- Test: `tests/test_make_bib.py`

**Interfaces:**
- Consumes: `papers/*/meta.yaml` schema from Task 3's tests.
- Produces: `generate(root: Path) -> str`; CLI `uv run python scripts/make_bib.py [root]` writing `bib/references.bib`. Bib key = paper id with `.` and `/` replaced by `_`.

- [ ] **Step 1: Write failing tests**

`tests/test_make_bib.py`:

```python
from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from make_bib import bib_key, generate


META = {"id": "2401.00001", "title": "A Paper", "authors": ["Ada Lovelace", "Alan Turing"],
        "year": 2026, "url": "https://arxiv.org/abs/2401.00001",
        "type": "empirical", "tags": ["llm"], "status": "noted"}


def test_bib_key_replaces_separators():
    assert bib_key(META) == "2401_00001"


def test_generate_produces_entry(tmp_path):
    d = tmp_path / "papers" / "2401.00001"
    d.mkdir(parents=True)
    (d / "meta.yaml").write_text(yaml.safe_dump(META))
    out = generate(tmp_path)
    assert "@misc{2401_00001," in out
    assert "author = {Ada Lovelace and Alan Turing}," in out
    assert "year = {2026}," in out


def test_generate_empty_store(tmp_path):
    assert generate(tmp_path) == ""
```

- [ ] **Step 2: Run tests, verify failure**

Run: `uv run pytest tests/test_make_bib.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'make_bib'`.

- [ ] **Step 3: Write `scripts/make_bib.py`**

```python
#!/usr/bin/env python3
"""Generate bib/references.bib from papers/*/meta.yaml. Never edit the output by hand."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def bib_key(meta: dict) -> str:
    return str(meta["id"]).replace(".", "_").replace("/", "_")


def bib_entry(meta: dict) -> str:
    authors = " and ".join(meta["authors"])
    return "\n".join([
        f"@misc{{{bib_key(meta)},",
        f"  title = {{{meta['title']}}},",
        f"  author = {{{authors}}},",
        f"  year = {{{meta['year']}}},",
        f"  url = {{{meta['url']}}},",
        "}",
    ])


def generate(root: Path) -> str:
    papers = root / "papers"
    if not papers.exists():
        return ""
    metas = [yaml.safe_load(p.read_text()) for p in sorted(papers.glob("*/meta.yaml"))]
    if not metas:
        return ""
    return "\n\n".join(bib_entry(m) for m in metas) + "\n"


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out = root / "bib" / "references.bib"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate(root))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests, verify pass**

Run: `uv run pytest tests/test_make_bib.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/make_bib.py tests/test_make_bib.py
git commit -m "Add BibTeX generation from paper metadata"
```

---

### Task 5: arxiv_watch.py + watch.sh (headless watcher)

**Files:**
- Create: `scripts/arxiv_watch.py`, `scripts/watch.sh`
- Test: `tests/test_arxiv_watch.py`, `tests/fixtures/arxiv_feed.xml`

**Interfaces:**
- Consumes: `profile.md` `## Watch` YAML block (Task 2); `papers/index.jsonl` ids.
- Produces: `parse_watch(text: str) -> dict`, `build_query(config: dict) -> str`, `parse_feed(xml_text: str) -> list[dict]` (dicts with keys `id, title, summary, authors, published, url`), `known_ids(index_path: Path) -> set[str]`, `write_candidates(entries, inbox: Path, known: set[str]) -> int`. CLI: `uv run python scripts/arxiv_watch.py [--root PATH] [--dry-run]`. Inbox file format: `inbox/<id>.md` with YAML frontmatter (id, title, authors, published, url) + abstract body — this is what `/triage` reads.

- [ ] **Step 1: Write fixture `tests/fixtures/arxiv_feed.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.11111v2</id>
    <title>Efficient  Attention
 Variants</title>
    <summary>We study efficient attention.
    Multi-line abstract.</summary>
    <published>2026-07-10T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <author><name>Alan Turing</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.22222v1</id>
    <title>Known Paper</title>
    <summary>Already indexed.</summary>
    <published>2026-07-09T00:00:00Z</published>
    <author><name>Grace Hopper</name></author>
  </entry>
</feed>
```

- [ ] **Step 2: Write failing tests**

`tests/test_arxiv_watch.py`:

```python
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from arxiv_watch import build_query, known_ids, parse_feed, parse_watch, write_candidates

FIXTURE = (Path(__file__).parent / "fixtures" / "arxiv_feed.xml").read_text()

PROFILE = """# Research Profile

## Watch

```yaml
categories:
  - cs.LG
  - cs.CL
keywords:
  - state space model
max_results: 25
```
"""


def test_parse_watch():
    config = parse_watch(PROFILE)
    assert config["categories"] == ["cs.LG", "cs.CL"]
    assert config["keywords"] == ["state space model"]
    assert config["max_results"] == 25


def test_parse_watch_missing_section():
    import pytest
    with pytest.raises(ValueError):
        parse_watch("# nothing here")


def test_build_query_cats_and_keywords():
    q = build_query({"categories": ["cs.LG"], "keywords": ["state space model"]})
    assert q == '(cat:cs.LG) AND (all:"state space model")'


def test_build_query_cats_only():
    assert build_query({"categories": ["cs.LG", "cs.CL"], "keywords": []}) == "cat:cs.LG OR cat:cs.CL"


def test_parse_feed():
    entries = parse_feed(FIXTURE)
    assert len(entries) == 2
    first = entries[0]
    assert first["id"] == "2401.11111"
    assert first["title"] == "Efficient Attention Variants"
    assert first["authors"] == ["Ada Lovelace", "Alan Turing"]
    assert first["url"] == "https://arxiv.org/abs/2401.11111"


def test_known_ids(tmp_path):
    idx = tmp_path / "index.jsonl"
    idx.write_text(json.dumps({"id": "2401.22222"}) + "\n")
    assert known_ids(idx) == {"2401.22222"}
    assert known_ids(tmp_path / "absent.jsonl") == set()


def test_write_candidates_skips_known_and_existing(tmp_path):
    entries = parse_feed(FIXTURE)
    inbox = tmp_path / "inbox"
    written = write_candidates(entries, inbox, known={"2401.22222"})
    assert written == 1
    assert (inbox / "2401.11111.md").exists()
    assert not (inbox / "2401.22222.md").exists()
    assert write_candidates(entries, inbox, known={"2401.22222"}) == 0
    text = (inbox / "2401.11111.md").read_text()
    assert text.startswith("---\n")
    assert "Efficient Attention Variants" in text
```

- [ ] **Step 3: Run tests, verify failure**

Run: `uv run pytest tests/test_arxiv_watch.py -v`
Expected: ERROR `ModuleNotFoundError: No module named 'arxiv_watch'`.

- [ ] **Step 4: Write `scripts/arxiv_watch.py`**

```python
#!/usr/bin/env python3
"""Fetch new arXiv listings matching profile.md's Watch config into inbox/. No LLM."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ATOM = "{http://www.w3.org/2005/Atom}"
API = "http://export.arxiv.org/api/query"


def parse_watch(profile_text: str) -> dict:
    match = re.search(r"## Watch.*?```yaml\n(.*?)```", profile_text, re.DOTALL)
    if not match:
        raise ValueError("profile.md has no '## Watch' section with a yaml block")
    config = yaml.safe_load(match.group(1))
    config.setdefault("max_results", 50)
    return config


def build_query(config: dict) -> str:
    cats = " OR ".join(f"cat:{c}" for c in config.get("categories", []))
    kws = " OR ".join(f'all:"{k}"' for k in config.get("keywords", []))
    if cats and kws:
        return f"({cats}) AND ({kws})"
    return cats or kws


def parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    entries: list[dict] = []
    for entry in root.findall(f"{ATOM}entry"):
        raw_id = entry.findtext(f"{ATOM}id") or ""
        arxiv_id = re.sub(r"v\d+$", "", raw_id.rsplit("/abs/", 1)[-1])
        entries.append({
            "id": arxiv_id,
            "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
            "summary": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
            "authors": [a.findtext(f"{ATOM}name") or "" for a in entry.findall(f"{ATOM}author")],
            "published": entry.findtext(f"{ATOM}published") or "",
            "url": f"https://arxiv.org/abs/{arxiv_id}",
        })
    return entries


def fetch(config: dict) -> list[dict]:
    params = urllib.parse.urlencode({
        "search_query": build_query(config),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": config["max_results"],
    })
    with urllib.request.urlopen(f"{API}?{params}", timeout=30) as resp:
        return parse_feed(resp.read().decode())


def known_ids(index_path: Path) -> set[str]:
    if not index_path.exists():
        return set()
    return {json.loads(line)["id"]
            for line in index_path.read_text().splitlines() if line.strip()}


def write_candidates(entries: list[dict], inbox: Path, known: set[str]) -> int:
    inbox.mkdir(parents=True, exist_ok=True)
    written = 0
    for e in entries:
        path = inbox / f"{e['id']}.md"
        if e["id"] in known or path.exists():
            continue
        frontmatter = yaml.safe_dump(
            {k: e[k] for k in ("id", "title", "authors", "published", "url")},
            sort_keys=False, allow_unicode=True)
        path.write_text(f"---\n{frontmatter}---\n\n{e['summary']}\n")
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = parse_watch((args.root / "profile.md").read_text())
    entries = fetch(config)
    known = known_ids(args.root / "papers" / "index.jsonl")
    if args.dry_run:
        new = [e for e in entries if e["id"] not in known]
        print(f"{len(new)} new candidates (dry run)")
        return 0
    written = write_candidates(entries, args.root / "inbox", known)
    print(f"wrote {written} candidates to inbox/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests, verify pass**

Run: `uv run pytest tests/test_arxiv_watch.py -v`
Expected: 7 passed.

- [ ] **Step 6: Write `scripts/watch.sh` and make executable**

```bash
#!/bin/bash
# Daily: fetch new arXiv candidates, then let the agent triage them.
# Schedule via launchd/cron, e.g.: 0 7 * * * /path/to/repo/scripts/watch.sh
set -euo pipefail
cd "$(dirname "$0")/.."
uv run python scripts/arxiv_watch.py
claude -p "/triage" --permission-mode acceptEdits
```

Run: `chmod +x scripts/watch.sh`

- [ ] **Step 7: Commit**

```bash
git add scripts/arxiv_watch.py scripts/watch.sh tests/test_arxiv_watch.py tests/fixtures/arxiv_feed.xml
git commit -m "Add LLM-free arXiv watcher and cron entrypoint"
```

---

### Task 6: Subagents (paper-scout, paper-reader, claim-verifier)

**Files:**
- Create: `.claude/agents/paper-scout.md`, `.claude/agents/paper-reader.md`, `.claude/agents/claim-verifier.md`

**Interfaces:**
- Produces: subagent names `paper-scout`, `paper-reader`, `claim-verifier` referenced by skills in Tasks 7-8. paper-scout returns a JSON array of candidates; paper-reader returns filled template markdown; claim-verifier returns `VERIFIED` or a mismatch list.

- [ ] **Step 1: Write `.claude/agents/paper-scout.md`**

```markdown
---
name: paper-scout
description: Read-only literature searcher. Given a search angle, queries the arXiv API, Semantic Scholar, and the web, and returns structured candidates. Dispatched by /survey.
tools: Bash, Read, WebFetch, WebSearch
---

You are a literature scout for deep learning research. You receive one search angle (a focused query plus context on why it matters).

Sources, in order of preference:
1. arXiv API: `curl -s 'http://export.arxiv.org/api/query?search_query=...&max_results=20'`
2. Semantic Scholar API: `curl -s 'https://api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,year,externalIds,abstract,citationCount'`
3. Web search for surveys, blog posts naming papers, and conference proceedings.

Rules:
- Only report papers you actually retrieved in this session. Never cite from memory alone.
- Include exact arXiv ids or DOIs and URLs.
- Return 5-15 candidates.

Return ONLY a JSON array, no prose:
[{"id": "<arxiv-id-or-doi>", "title": "...", "authors": ["..."], "year": 2026, "venue": "...", "url": "...", "one_line_finding": "...", "relevance_note": "..."}]
```

- [ ] **Step 2: Write `.claude/agents/paper-reader.md`**

```markdown
---
name: paper-reader
description: Deep-reads one paper PDF in an isolated context and returns structured notes following a provided template. Dispatched by /read.
tools: Read, Bash, WebFetch
---

You read exactly one paper per invocation. You receive: a PDF path or arXiv URL, the paper type, and a notes template.

Procedure:
1. Read the full paper. For PDFs use the Read tool with page ranges (max 20 pages per call); for arXiv URLs fetch the abs page first, then the PDF.
2. Fill the provided template section by section.

Rules:
- Every claim and number must carry a location reference: (Table 2), (Section 4.1), (Eq. 3).
- Quote numbers exactly as printed. Never round, estimate, or reconstruct from memory.
- If the paper does not report something, write "not reported" — do not guess.
- Note explicitly when the authors' claims exceed their evidence.

Return ONLY the filled template as markdown. Your output becomes notes.md verbatim.
```

- [ ] **Step 3: Write `.claude/agents/claim-verifier.md`**

```markdown
---
name: claim-verifier
description: Adversarial verifier that checks notes' factual claims (numbers, datasets, attributions) against the source paper. Gates wiki export. Dispatched by /wiki-export.
tools: Read, Bash, WebFetch
---

You receive a notes.md path and the source paper (PDF path or URL). Your job is to REFUTE the notes.

Procedure:
1. Extract every factual claim from the notes: numbers, dataset names, baseline names, method attributions, theorem statements.
2. Locate each claim in the paper and compare exactly.
3. Claims you cannot locate in the paper count as mismatches.

Return ONLY one of:
- `VERIFIED` (every claim matched), or
- A markdown list of mismatches, each: `- claim: <what the notes say> | paper: <what the paper actually says or "not found"> | location: <where you looked>`

Do not rewrite the notes. Do not soften findings. A wrong number that "seems close" is a mismatch.
```

- [ ] **Step 4: Verify agent files parse (frontmatter present)**

Run: `head -5 .claude/agents/*.md`
Expected: each file starts with `---` and a `name:` line.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents
git commit -m "Add paper-scout, paper-reader, and claim-verifier subagents"
```

---

### Task 7: Core skills (/read, /triage)

**Files:**
- Create: `.claude/skills/read/SKILL.md`, `.claude/skills/triage/SKILL.md`

**Interfaces:**
- Consumes: store schema (Task 2), `check_store`/`make_bib` CLIs (Tasks 3-4), inbox file format (Task 5), `paper-reader` subagent (Task 6).
- Produces: `/read` and `/triage` slash commands; the type-specific reading templates other skills reference.

- [ ] **Step 1: Write `.claude/skills/read/SKILL.md`**

````markdown
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
````

- [ ] **Step 2: Write `.claude/skills/triage/SKILL.md`**

```markdown
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
```

- [ ] **Step 3: Verify frontmatter**

Run: `head -4 .claude/skills/read/SKILL.md .claude/skills/triage/SKILL.md`
Expected: each starts with `---` and has `name:`.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/read .claude/skills/triage
git commit -m "Add core reading and triage skills"
```

---

### Task 8: Remaining skills (/survey, /reproduce, /wiki-export, /status)

**Files:**
- Create: `.claude/skills/survey/SKILL.md`, `.claude/skills/reproduce/SKILL.md`, `.claude/skills/wiki-export/SKILL.md`, `.claude/skills/status/SKILL.md`

**Interfaces:**
- Consumes: `paper-scout` and `claim-verifier` subagents (Task 6), `/read` templates (Task 7), store schema (Task 2), user-level `make-llm-wiki-raw` / `wikify-raw` skills (already installed globally).

- [ ] **Step 1: Write `.claude/skills/survey/SKILL.md`**

```markdown
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
```

- [ ] **Step 2: Write `.claude/skills/reproduce/SKILL.md`**

```markdown
---
name: reproduce
description: Scaffold a local-first experiment to reproduce a paper's central claim. Use when asked to reproduce, implement, or run experiments from a paper.
---

# /reproduce <paper-id>

1. Read `papers/<id>/notes.md` and `meta.yaml`. If notes are missing, run /read first.
2. Identify the paper's central claim and design the smallest experiment that tests it at local scale (Mac, MPS/CPU): subset of the dataset, reduced model config, shortened schedule. State explicitly what the scaled-down result can and cannot confirm.
3. Scaffold `experiments/<slug>/` (slug: short kebab-case):
   - `README.md`: goal, linked paper id, central claim under test, success criterion, status (`planned`), log section
   - `config/base.yaml`: every hyperparameter and path as data — nothing hardcoded in code
   - `src/`: minimal implementation; use the repo's uv environment; add deps to pyproject.toml only after the package-safety check
   - `results/`: metrics written as `results/metrics.jsonl`, plots as files
4. Keep the layout remote-friendly: code reads config paths relative to the experiment dir, results land in `results/` — a remote runner can later execute the same layout unchanged.
5. Update README status as work progresses: planned -> running -> done | blocked, with findings vs the paper's claim (exact numbers, both sides).
```

- [ ] **Step 3: Write `.claude/skills/wiki-export/SKILL.md`**

```markdown
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
```

- [ ] **Step 4: Write `.claude/skills/status/SKILL.md`**

```markdown
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
```

- [ ] **Step 5: Verify all skills present**

Run: `ls .claude/skills/`
Expected: `read reproduce status survey triage wiki-export`.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/survey .claude/skills/reproduce .claude/skills/wiki-export .claude/skills/status
git commit -m "Add survey, reproduce, wiki-export, and status skills"
```

---

### Task 9: End-to-end validation

**Files:**
- Modify: none expected (fix anything validation surfaces)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Full test suite**

Run: `uv run pytest -v`
Expected: 17 passed (7 + 3 + 7), 0 failed.

- [ ] **Step 2: Store lint on the real store**

Run: `uv run python scripts/check_store.py`
Expected: `store OK`.

- [ ] **Step 3: Bib generation on empty store**

Run: `uv run python scripts/make_bib.py && cat bib/references.bib`
Expected: `wrote bib/references.bib`, empty file.

- [ ] **Step 4: Watcher dry-run against live arXiv (network permitting)**

Run: `uv run python scripts/arxiv_watch.py --dry-run`
Expected: `N new candidates (dry run)` for some N >= 0. If the network is unavailable, note it and move on — unit tests already cover parsing.

- [ ] **Step 5: Harness structure check**

Run: `ls .claude/agents .claude/skills scripts`
Expected: 3 agents, 6 skills, 4 scripts (arxiv_watch.py, check_store.py, make_bib.py, watch.sh).

Note: the spec's skill-level acceptance test (run `/read` on one known paper of each type and lint the store) requires live LLM runs on user-chosen papers — deferred to first real use.

- [ ] **Step 6: Final commit (bib output + any fixes)**

```bash
git add bib/references.bib
git commit -m "Validate harness end to end"
git log --oneline
```
Expected: 8 commits on main; working tree clean except intentionally untracked files.
