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
