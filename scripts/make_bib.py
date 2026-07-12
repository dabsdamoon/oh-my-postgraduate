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
