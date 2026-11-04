import json
from pathlib import Path

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
    assert "e1 --> e2" in text and "[記録1](#entry-1)" in text

    assert "e1 -->|元のrun| e4" in text and "e3 --> e4" in text
    assert "元のrun　[記録1](#entry-1)" in text

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
    assert text.index("### run-001") < text.index("### 判断の記録")
    assert "購入額が不明" in text and decision["reason"][0] in text


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
