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
