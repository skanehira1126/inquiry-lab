import copy
import io
import json
from datetime import datetime
from pathlib import Path

import pytest

from inquiry_lab.cli import main
from inquiry_lab.history import record_entry
from inquiry_lab.state import update_state


@pytest.fixture
def state():
    example = Path(__file__).resolve().parents[1] / "skills/analyze/assets/state.json"
    return json.loads(example.read_text(encoding="utf-8"))


def test_update_replaces_whole_snapshot_and_show_preserves_all_values(
    tmp_path, state, monkeypatch, capsys
):
    workspace = tmp_path / "分析 先"
    assert main(["init", str(workspace), "--title", "比較"]) == 0
    original = {p: p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    capsys.readouterr()
    before_input = copy.deepcopy(state)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(state)))
    assert main(["state", "update", "--workspace", str(workspace)]) == 0
    assert capsys.readouterr().out.strip() == str(workspace / "state.json")
    assert state == before_input
    first = json.loads((workspace / "state.json").read_text())
    assert datetime.fromisoformat(first["updated_at"]).utcoffset().total_seconds() == 0

    state["current_task"] = None
    state["current_conclusion"] = "長い結果" * 100
    state["completion_criteria"][0]["evidence"] = [f"結果{i}" for i in range(25)]
    source = tmp_path / "new.json"
    source.write_text(json.dumps(state), encoding="utf-8-sig")
    assert main(["state", "update", "--workspace", str(workspace), "--input", str(source)]) == 0
    capsys.readouterr()
    saved_bytes = (workspace / "state.json").read_bytes()
    assert main(["state", "show", "--workspace", str(workspace)]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown.pop("updated_at")
    assert shown == state
    assert (workspace / "state.json").read_bytes() == saved_bytes
    assert all(path.read_bytes() == content for path, content in original.items())
    assert not list(workspace.glob(".state-*"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", True),
        ("goal", " "),
        ("status", "finished"),
        ("completion_criteria", []),
        ("completion_criteria", [{"condition": "test", "status": "done", "evidence": []}]),
        ("current_task", {"goal": "individual"}),
        ("history_sequence", True),
        ("constraints", "no holdout"),
        ("references", [{"target": "somewhere"}]),
        ("updated_at", "2026-11-06T00:00:00"),
        ("unexpected", "unsupported"),
    ],
)
def test_invalid_snapshot_leaves_existing_state_intact(tmp_path, state, capsys, field, value):
    path = update_state(tmp_path, state)
    original = path.read_bytes()
    state[field] = value
    source = tmp_path / "input.json"
    source.write_text(json.dumps(state))
    assert main(["state", "update", "--workspace", str(tmp_path), "--input", str(source)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "inquiry-lab:" in output.err
    assert path.read_bytes() == original
    assert not list(tmp_path.glob(".state-*"))


@pytest.mark.parametrize("source", ["{", "{}", "[]", '{"goal":"a","goal":"b"}', "NaN"])
def test_bad_json_never_creates_state(tmp_path, source, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(source))
    assert main(["state", "update", "--workspace", str(tmp_path)]) == 1
    assert capsys.readouterr().out == ""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["symlink", "dangling", "directory"])
def test_update_refuses_nonregular_state(tmp_path, state, kind):
    path = tmp_path / "state.json"
    target = tmp_path / "target"
    if kind == "directory":
        path.mkdir()
    else:
        if kind == "symlink":
            target.write_text("keep")
        path.symlink_to(target)
    with pytest.raises(ValueError, match="regular file"):
        update_state(tmp_path, state)
    if kind == "directory":
        assert path.is_dir()
    else:
        assert path.is_symlink()
        assert target.read_text() == "keep" if kind == "symlink" else not target.exists()


def test_update_validates_history_pointer_and_existing_workspace(tmp_path, state):
    with pytest.raises(ValueError, match="workspace"):
        update_state(tmp_path / "missing", state)
    state["history_sequence"] = 1
    with pytest.raises(OSError):
        update_state(tmp_path, state)
    assert list(tmp_path.iterdir()) == []


def test_failed_replacement_preserves_old_snapshot(tmp_path, state, monkeypatch):
    path = update_state(tmp_path, state)
    original = path.read_bytes()

    def fail_replace(self, target):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", fail_replace)
    state["next_action"] = "new action"
    with pytest.raises(OSError, match="disk full"):
        update_state(tmp_path, state)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_context_uses_explicit_workspace_and_reports_new_history(
    tmp_path, state, monkeypatch, capsys
):
    workspace = tmp_path / "selected"
    workspace.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    other_state = {**state, "goal": "UNRELATED ANALYSIS"}
    update_state(other, other_state)
    monkeypatch.chdir(other)
    path = update_state(workspace, state)
    before = path.read_bytes()
    assert main(["state", "context", "--workspace", str(workspace)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert "systemMessage" not in output
    hook = output["hookSpecificOutput"]
    assert hook["hookEventName"] == "SessionStart"
    assert state["goal"] in hook["additionalContext"]
    assert state["current_task"]["done_when"] in hook["additionalContext"]
    assert "UNRELATED ANALYSIS" not in hook["additionalContext"]
    record_entry(
        workspace,
        {
            "sequence": 2,
            "kind": "decision",
            "decision": ["条件を見直す"],
            "reason": ["新たな依頼"],
            "current_state": "比較を保留",
            "references": [],
        },
    )
    assert main(["state", "context", "--workspace", str(workspace)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert "最大番号は2" in output["systemMessage"]
    assert output["systemMessage"] in output["hookSpecificOutput"]["additionalContext"]
    assert path.read_bytes() == before
    state["history_sequence"] = 2
    update_state(workspace, state)
    assert main(["state", "context", "--workspace", str(workspace)]) == 0
    assert "systemMessage" not in json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("source", [None, "{", "{}"])
def test_context_returns_recovery_guidance_for_unavailable_state(tmp_path, source, capsys):
    path = tmp_path / "state.json"
    if source is not None:
        path.write_text(source)
    assert main(["state", "context", "--workspace", str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert "復元できません" in output["systemMessage"]
    assert "状態は未確認" in output["hookSpecificOutput"]["additionalContext"]
    assert path.read_text() == source if source is not None else not path.exists()
    assert main(["state", "show", "--workspace", str(tmp_path)]) == 1
    assert capsys.readouterr().out == ""


def test_large_context_points_to_full_state_instead_of_truncating(tmp_path, state, capsys):
    state["current_conclusion"] = ("long conclusion " * 1000).strip()
    update_state(tmp_path, state)
    assert main(["state", "context", "--workspace", str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "state show" in context
    assert "6000" in context
    assert "long conclusion" not in context
    assert len(context) < 1500


@pytest.mark.parametrize(
    "args", [["state"], ["state", "update"], ["state", "show"], ["state", "context"]]
)
def test_state_requires_action_and_workspace(args, capsys):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err
