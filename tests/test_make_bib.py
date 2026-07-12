import sys
from pathlib import Path

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
