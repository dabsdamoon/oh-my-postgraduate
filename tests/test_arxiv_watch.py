import json
import sys
from pathlib import Path

import pytest

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
