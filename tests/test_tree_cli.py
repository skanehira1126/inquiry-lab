from concurrent.futures import ThreadPoolExecutor
import json

import pytest

import inquiry_lab as il
from inquiry_lab.cli import main
from inquiry_lab.tree_map import HypothesisNode
from inquiry_lab.tree_map import ResearchNode


@pytest.fixture
def tree_file(tmp_path):
    tree = il.tree("C", "誤差の要因を調べる")
    tree.add(HypothesisNode(id="H1", parent="C", hypothesis="季節差がある", result="暫定結論"))
    tree.add(ResearchNode(id="R1", parent="H1", question="冬の誤差は？", result="未集計"))
    path = tmp_path / "tree.json"
    tree.dump(path)
    return path


def test_tree_cli_adds_a_branch_to_an_existing_tree(tree_file, capsys):
    add = ["tree", "add-hypothesis", str(tree_file)]
    assert main([*add, "H2", "--core", "--hypothesis", "季節差がある"]) == 0
    assert (
        main(
            [
                *add,
                "H3",
                "--parent",
                "H2",
                "--hypothesis",
                "冬に偏る",
                "--constraint",
                "同じ期間",
                "--constraint",
                "同じ地域",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "tree",
                "add-research",
                str(tree_file),
                "R2",
                "--parent",
                "H3",
                "--question",
                "月別の誤差は？",
            ]
        )
        == 0
    )
    tree = il.load_tree(tree_file)
    assert tree.get("H2") == HypothesisNode(id="H2", parent="C", hypothesis="季節差がある")
    assert tree.get("H3") == HypothesisNode(
        id="H3", parent="H2", hypothesis="冬に偏る", constraints=["同じ期間", "同じ地域"]
    )
    assert tree.get("R2") == ResearchNode(id="R2", parent="H3", question="月別の誤差は？")
    output = capsys.readouterr()
    assert output.out.splitlines() == [str(tree_file)] * 3
    assert output.err == ""


@pytest.mark.parametrize(
    ("command", "args"),
    [
        ("add-hypothesis", ["H2", "--hypothesis", "仮説"]),
        ("add-hypothesis", ["H2", "--hypothesis", "仮説", "--parent", "H1", "--core"]),
        ("add-research", ["R2", "--question", "問い", "--core"]),
        ("add-research", ["R2", "--question", "問い"]),
    ],
)
def test_tree_add_requires_one_valid_parent_option(tree_file, command, args):
    original = tree_file.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(["tree", command, str(tree_file), *args])
    assert error.value.code == 2
    assert tree_file.read_bytes() == original


@pytest.mark.parametrize(
    ("command", "args", "detail"),
    [
        ("add-hypothesis", ["H1", "--core", "--hypothesis", "重複"], "H1"),
        ("add-hypothesis", ["H2", "--parent", "missing", "--hypothesis", "仮説"], "missing"),
        ("add-hypothesis", ["H2", "--parent", "R1", "--hypothesis", "仮説"], "R1"),
        ("add-research", ["R2", "--parent", "C", "--question", "問い"], "C"),
    ],
)
def test_tree_add_rejects_invalid_nodes_before_saving(tree_file, capsys, command, args, detail):
    original = tree_file.read_bytes()
    assert main(["tree", command, str(tree_file), *args]) == 1
    output = capsys.readouterr()
    assert detail in output.err
    assert output.out == ""
    assert tree_file.read_bytes() == original


def test_tree_cli_updates_research_fields_and_references(tree_file, capsys):
    command = ["tree", "update", str(tree_file), "research", "R1"]
    assert main([*command, "--status", "Running"]) == 0
    assert il.load_tree(tree_file).get("R1").result == "未集計"
    assert (
        main(
            [
                *command,
                "--status",
                "Done",
                "--result",
                "冬季に集中",
                "--add-reference",
                "ref1",
                "報告 1.md",
                "--add-reference",
                "ref2",
                "図2.png",
            ]
        )
        == 0
    )
    node = il.load_tree(tree_file).get("R1")
    assert (node.status, node.result) == ("Done", "冬季に集中")
    assert node.references == [
        {"id": "ref1", "content": "報告 1.md"},
        {"id": "ref2", "content": "図2.png"},
    ]
    assert main([*command, "--clear-result", "--delete-reference", "ref1"]) == 0
    node = il.load_tree(tree_file).get("R1")
    assert node.status == "Done"
    assert node.result is None
    assert node.references == [{"id": "ref2", "content": "図2.png"}]
    output = capsys.readouterr()
    assert output.out.splitlines() == [str(tree_file)] * 3
    assert output.err == ""


def test_tree_cli_updates_core_and_hypothesis(tree_file):
    command = ["tree", "update", str(tree_file)]
    assert (
        main(
            [
                *command,
                "core",
                "--status",
                "completed",
                "--add-evidence",
                "F1",
                "冬季に集中",
                "H1",
                "R1",
            ]
        )
        == 0
    )
    core = il.load_tree(tree_file).get("C")
    assert core.status == "completed"
    assert core.evidence_items == [{"id": "F1", "finding": "冬季に集中", "node_ids": ["H1", "R1"]}]
    assert main([*command, "core", "--delete-evidence", "F1"]) == 0
    assert main([*command, "hypothesis", "H1", "--status", "Pending", "--clear-result"]) == 0
    tree = il.load_tree(tree_file)
    assert tree.get("C").evidence_items == []
    assert tree.get("H1").status == "Pending"
    assert tree.get("H1").result is None
    assert tree.get("R1").result == "未集計"


@pytest.mark.parametrize(
    "args, detail",
    [
        (["research", "missing", "--status", "Done"], "missing"),
        (["hypothesis", "R1", "--clear-result"], "HypothesisNode"),
        (
            ["research", "R1", "--add-reference", "ref", "a", "--add-reference", "ref", "b"],
            "duplicate",
        ),
    ],
)
def test_tree_cli_failed_update_preserves_file(tree_file, capsys, args, detail):
    original = tree_file.read_bytes()
    assert main(["tree", "update", str(tree_file), *args]) == 1
    output = capsys.readouterr()
    assert detail in output.err
    assert output.out == ""
    assert tree_file.read_bytes() == original


@pytest.mark.parametrize(
    "args",
    [
        ["core", "--status", "Done"],
        ["core", "--clear-result"],
        ["research", "R1"],
        ["hypothesis", "H1", "--result", "", "--clear-result"],
        ["research", "R1", "--add-reference", "ref"],
        ["core", "--add-evidence", "F1"],
    ],
)
def test_tree_cli_invalid_arguments_preserve_file(tree_file, args):
    original = tree_file.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(["tree", "update", str(tree_file), *args])
    assert error.value.code == 2
    assert tree_file.read_bytes() == original


def test_concurrent_tree_cli_updates_keep_both_references(tree_file):
    command = ["tree", "update", str(tree_file), "research", "R1", "--add-reference"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(main, [[*command, "a", "A.md"], [*command, "b", "B.md"]]))
    assert results == [0, 0]
    assert {ref["id"] for ref in il.load_tree(tree_file).get("R1").references} == {"a", "b"}


def test_new_tree_and_read_only_hypothesis_status(tmp_path, capsys):
    path = tmp_path / "tree.json"
    init = ["tree", "init", str(path), "--core-id", "C", "--goal", "問い"]
    assert main(init) == 0
    assert capsys.readouterr().out.strip() == str(path)
    assert main(["tree", "add-hypothesis", str(path), "H", "--core", "--hypothesis", "予想"]) == 0
    before = path.read_bytes()
    capsys.readouterr()
    assert main(["tree", "status", str(path), "H"]) == 0
    view = json.loads(capsys.readouterr().out)
    assert view["tree_path"] == str(path)
    assert view["core"] == {"id": "C", "goal": "問い"}
    assert view["hypothesis"]["id"] == "H"
    assert view["research_nodes"] == []
    assert main(init) == 1
    assert path.read_bytes() == before
    assert list(tmp_path.rglob("*.json")) == [path]
