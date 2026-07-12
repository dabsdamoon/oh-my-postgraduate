import json
import sys
from pathlib import Path

import yaml

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
