from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest

import inquiry_lab as il
from inquiry_lab.cli import main
from inquiry_lab.tree_map import HypothesisNode
from inquiry_lab.tree_map import ResearchNode


@pytest.fixture
def tree(tmp_path):
    path = tmp_path / "共有 tree.json"
    tree = il.tree("C", "予測誤差を説明する")
    tree.add(HypothesisNode(id="H1", parent="C", hypothesis="冬に偏る", constraints=["同じ店舗"]))
    tree.add(HypothesisNode(id="H2", parent="H1", hypothesis="積雪日に偏る"))
    tree.add(ResearchNode(id="R1", parent="H1", question="春との差は？"))
    tree.add(ResearchNode(id="R2", parent="H2", question="積雪日の差は？"))
    tree.dump(path)
    return path


def start(state, tree, hypothesis="H1"):
    return main(["state", "start", str(state), "--tree", str(tree), "--hypothesis", hypothesis])


def test_worker_lifecycle_reads_live_tree_and_keeps_workers_independent(tree, capsys, monkeypatch):
    monkeypatch.chdir(tree.parent)
    a = Path("agents/A/state.json")
    b = Path("agents/B/state.json")
    assert start(a, tree.name) == 0
    assert Path(capsys.readouterr().out.strip()) == a.resolve()
    binding = a.read_bytes()
    assert json.loads(binding) == {"tree_path": "../../共有 tree.json", "hypothesis_id": "H1"}
    assert start(b, tree, "H2") == 0
    other = b.read_bytes()
    assert (
        main(
            [
                "tree",
                "update",
                str(tree),
                "research",
                "R1",
                "--status",
                "Blocked",
                "--result",
                "入力待ち",
                "--add-reference",
                "ref",
                "runs/001/result.md",
            ]
        )
        == 0
    )
    assert main(["tree", "update", str(tree), "hypothesis", "H1", "--status", "Pruned"]) == 0
    capsys.readouterr()
    tree_bytes = tree.read_bytes()
    assert a.read_bytes() == binding

    monkeypatch.chdir(a.parent)
    assert main(["state", "show", "state.json"]) == 0
    view = json.loads(capsys.readouterr().out)
    assert view["tree_path"] == str(tree)
    assert view["core"] == {"id": "C", "goal": "予測誤差を説明する"}
    assert view["hypothesis"]["id"] == "H1"
    assert view["hypothesis"]["status"] == "Pruned"
    assert view["hypothesis"]["constraints"] == ["同じ店舗"]
    assert view["research_nodes"] == [
        {
            "id": "R1",
            "question": "春との差は？",
            "status": "Blocked",
            "result": "入力待ち",
            "references": [{"id": "ref", "content": "runs/001/result.md"}],
        }
    ]
    assert main(["state", "update", "state.json", "--hypothesis", "H2"]) == 0
    capsys.readouterr()
    assert main(["state", "show", "state.json"]) == 0
    switched = json.loads(capsys.readouterr().out)
    assert switched["hypothesis"]["id"] == "H2"
    assert [n["id"] for n in switched["research_nodes"]] == ["R2"]
    assert main(["state", "finish", "state.json"]) == 0
    assert not Path("state.json").exists()
    assert (tree.parent / b).read_bytes() == other
    assert tree.read_bytes() == tree_bytes


@pytest.mark.parametrize("hypothesis", ["C", "R1", "missing"])
def test_invalid_assignment_does_not_create_or_change_state(tree, hypothesis, capsys):
    state = tree.parent / "worker" / "state.json"
    assert start(state, tree, hypothesis) == 1
    assert not state.parent.exists()
    assert start(state, tree) == 0
    before = state.read_bytes()
    assert main(["state", "update", str(state), "--hypothesis", hypothesis]) == 1
    assert hypothesis in capsys.readouterr().err
    assert state.read_bytes() == before


def test_start_refuses_existing_assignment_under_contention(tree):
    state = tree.parent / "worker" / "state.json"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda h: start(state, tree, h), ["H1", "H2"]))
    assert sorted(results) == [0, 1]
    winner = ["H1", "H2"][results.index(0)]
    assert json.loads(state.read_text())["hypothesis_id"] == winner


@pytest.mark.parametrize("kind", ["unrelated", "symlink", "dangling"])
def test_state_mutations_protect_unrelated_files(tree, kind):
    state = tree.parent / "state.json"
    before = tree.read_bytes()
    if kind == "unrelated":
        state.write_bytes(before)
    else:
        state.symlink_to(tree if kind == "symlink" else tree.parent / "missing")
    assert start(state, tree) == 1
    assert main(["state", "update", str(state), "--hypothesis", "H2"]) == 1
    assert main(["state", "finish", str(state)]) == 1
    assert tree.read_bytes() == before
    if kind == "unrelated":
        assert state.read_bytes() == before
    else:
        assert state.is_symlink()


def test_finish_releases_assignment_even_when_tree_is_unavailable(tree):
    state = tree.parent / "state.json"
    assert start(state, tree) == 0
    tree.rename(tree.with_name("archived.json"))
    assert main(["state", "show", str(state)]) == 1
    assert main(["state", "update", str(state), "--hypothesis", "H2"]) == 1
    assert json.loads(state.read_text())["hypothesis_id"] == "H1"
    assert main(["state", "finish", str(state)]) == 0
    assert not state.exists()


def test_failed_state_replace_preserves_assignment(tree, monkeypatch):
    state = tree.parent / "state.json"
    assert start(state, tree) == 0
    original = state.read_bytes()

    def fail_replace(self, target):
        raise OSError("out of space")

    monkeypatch.setattr(Path, "replace", fail_replace)
    assert main(["state", "update", str(state), "--hypothesis", "H2"]) == 1
    assert state.read_bytes() == original
