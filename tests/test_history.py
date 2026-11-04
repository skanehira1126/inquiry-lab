import json
from pathlib import Path

import pytest

from inquiry_lab.cli import main

EXAMPLES = Path(__file__).resolve().parents[1] / "docs/examples"


def test_record_and_render_example(tmp_path):
    record = ["history", "record", "--workspace", str(tmp_path)]
    render = ["history", "render", "--workspace", str(tmp_path)]
    for entry in sorted((EXAMPLES / "history").glob("*.json")):
        assert main([*record, "--input", str(entry)]) == 0
    assert main(render) == 0
    output = tmp_path / "作業履歴.md"
    assert output.read_bytes() == (EXAMPLES / "作業履歴.md").read_bytes()

    text = output.read_text(encoding="utf-8")
    assert text.index("```mermaid") < text.index("## 現在地")
    assert "e1 --> e2" in text and "(history/000001.md)" in text

    assert "e1 -->|元のrun| e4" in text and "e3 --> e4" in text
    detail = (tmp_path / "history/000004.md").read_text(encoding="utf-8")
    assert "元のrun　[記録1](000001.md)" in detail
    assert "1,000円 × 16/80" in detail and "1,000円 × 16/80" not in text
    assert "(<../observations.csv>)" in detail
    assert "## 検証" in detail and "## 検証" not in text
    for entry in sorted((EXAMPLES / "history").glob("*.json")):
        data = json.loads(entry.read_text(encoding="utf-8"))
        assert data["summary"] in text
        assert (tmp_path / "history" / entry.with_suffix(".md").name).read_bytes() == (
            entry.with_suffix(".md").read_bytes()
        )

    decision = {
        "sequence": 5,
        "kind": "decision",
        "decision": ["原票が揃うまで店舗比較を保留する。"],
        "reason": ["西店の欠測理由は不明。"],
        "references": [],
        "current_state": "原票の入手待ち。",
    }
    source = tmp_path / "decision.json"
    source.write_text(json.dumps(decision), encoding="utf-8")
    assert main([*record, "--input", str(source)]) == 0
    assert main(render) == 0
    text = output.read_text(encoding="utf-8")
    assert text.index("原票の入手待ち。") < text.index("## 試行履歴")
    assert "e4 --> e5" not in text
    assert text.index("店舗別の欠測率を確認", text.index("## 試行履歴")) < text.index(
        "**判断の記録**"
    )
    detail = (tmp_path / "history/000005.md").read_text(encoding="utf-8")
    assert decision["reason"][0] in detail and decision["reason"][0] not in text
    assert "**判断の記録** — 原票の入手待ち。" in text


def test_history_preserves_existing_records_and_output_on_errors(tmp_path, monkeypatch):
    record = ["history", "record", "--workspace", str(tmp_path)]
    render = ["history", "render", "--workspace", str(tmp_path)]
    source = EXAMPLES / "history/000001.json"
    with source.open(encoding="utf-8") as stdin:
        monkeypatch.setattr("sys.stdin", stdin)
        assert main(record) == 0
    saved = tmp_path / "history/000001.json"
    original = saved.read_bytes()
    assert main([*record, "--input", str(source)]) == 1
    assert saved.read_bytes() == original

    output = tmp_path / "作業履歴.md"
    output.write_text("手書きの記録", encoding="utf-8")
    assert main(render) == 1
    assert output.read_text(encoding="utf-8") == "手書きの記録"
    output.unlink()
    assert main(render) == 0
    before = output.read_bytes()
    entry = json.loads(original)
    entry["results"] = "not a list"
    saved.write_text(json.dumps(entry), encoding="utf-8")
    assert main(render) == 1
    assert output.read_bytes() == before


def test_dependency_must_point_to_an_existing_earlier_entry(tmp_path):
    source = tmp_path / "decision.json"
    entry = json.loads((EXAMPLES / "history/000002.json").read_text(encoding="utf-8"))
    for parent in (1, 2, 3):
        entry["depends_on"] = [parent]
        source.write_text(json.dumps(entry), encoding="utf-8")
        assert (
            main(["history", "record", "--workspace", str(tmp_path), "--input", str(source)]) == 1
        )
    assert not (tmp_path / "history/000002.json").exists()


def test_base_run_cannot_point_to_a_decision_at_record_or_render(tmp_path):
    record = ["history", "record", "--workspace", str(tmp_path)]
    render = ["history", "render", "--workspace", str(tmp_path)]
    samples = EXAMPLES / "history"
    for name in ["000001.json", "000002.json"]:
        assert main([*record, "--input", str(samples / name)]) == 0
    assert main(render) == 0
    output = tmp_path / "作業履歴.md"
    before = output.read_bytes()
    entry = json.loads((samples / "000003.json").read_text(encoding="utf-8"))
    entry["base_run"] = 2
    source = tmp_path / "input.json"
    source.write_text(json.dumps(entry), encoding="utf-8")
    assert main([*record, "--input", str(source)]) == 1
    destination = tmp_path / "history/000003.json"
    assert not destination.exists()
    source.rename(destination)
    assert main(render) == 1
    assert output.read_bytes() == before


def test_render_checks_all_destinations_before_overwriting(tmp_path):
    record = ["history", "record", "--workspace", str(tmp_path)]
    render = ["history", "render", "--workspace", str(tmp_path)]
    assert main([*record, "--input", str(EXAMPLES / "history/000001.json")]) == 0
    assert main(render) == 0
    overview = tmp_path / "作業履歴.md"
    before = overview.read_bytes()
    detail = tmp_path / "history/000001.md"
    detail.write_text("手書きの詳しいメモ", encoding="utf-8")
    assert main(render) == 1
    assert overview.read_bytes() == before
    assert detail.read_text(encoding="utf-8") == "手書きの詳しいメモ"


def test_render_stages_all_documents_and_rebases_only_local_references(tmp_path, monkeypatch):
    entry = json.loads((EXAMPLES / "history/000001.json").read_text(encoding="utf-8"))
    entry.pop("summary")
    entry["references"] = [
        {"label": "ローカルの図", "target": "report/欠測 図.png"},
        {"label": "MLflow", "target": "https://mlflow.example/runs/123?tab=artifacts#figure"},
    ]
    source = tmp_path / "input.json"
    source.write_text(json.dumps(entry), encoding="utf-8")
    assert main(["history", "record", "--workspace", str(tmp_path), "--input", str(source)]) == 0
    render = ["history", "render", "--workspace", str(tmp_path)]
    assert main(render) == 0
    overview = tmp_path / "作業履歴.md"
    detail = tmp_path / "history/000001.md"
    assert entry["current_state"] in overview.read_text(encoding="utf-8")
    text = detail.read_text(encoding="utf-8")
    assert "(<../report/%E6%AC%A0%E6%B8%AC%20%E5%9B%B3.png>)" in text
    assert "(<https://mlflow.example/runs/123?tab=artifacts#figure>)" in text
    before = (overview.read_bytes(), detail.read_bytes())
    write_text = Path.write_text

    def fail_overview_write(path, content, **kwargs):
        if content.startswith("# 作業履歴"):
            raise OSError("disk full")
        return write_text(path, content, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_overview_write)
    assert main(render) == 1
    assert (overview.read_bytes(), detail.read_bytes()) == before


@pytest.mark.parametrize("summary", ["", "line1\nline2", ["text"]])
def test_record_rejects_invalid_summary_without_writing(tmp_path, summary):
    entry = json.loads((EXAMPLES / "history/000001.json").read_text(encoding="utf-8"))
    entry["summary"] = summary
    source = tmp_path / "input.json"
    source.write_text(json.dumps(entry), encoding="utf-8")
    assert main(["history", "record", "--workspace", str(tmp_path), "--input", str(source)]) == 1
    assert not (tmp_path / "history").exists()
