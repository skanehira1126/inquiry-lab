import json

import pytest

import inquiry_lab as il
from inquiry_lab.cli import main
from inquiry_lab.exceptions import InvalidSearchFilterError
from inquiry_lab.tree_map import HypothesisNode
from inquiry_lab.tree_map import ResearchNode


@pytest.fixture
def tree():
    tree = il.tree(core_id="C", goal="誤差の要因を調べる")
    tree.add(HypothesisNode(id="H1", parent="C", hypothesis="季節差がある", status="Active"))
    tree.add(HypothesisNode(id="H2", parent="H1", hypothesis="冬に偏る"))
    tree.add(HypothesisNode(id="H3", parent="C", hypothesis="地域差がある"))
    tree.add(ResearchNode(id="R1", parent="H1", question="月別の誤差は？"))
    tree.add(
        ResearchNode(
            id="R2",
            parent="H2",
            question="冬の誤差は？",
            status="Blocked",
            result="1月のデータが未着",
            references=[{"id": "ref1", "content": "runs/001/result.md"}],
        )
    )
    return tree


@pytest.mark.parametrize(
    ("filters", "expected_ids"),
    [
        ({"node_type": "hypothesis"}, ["H1", "H2", "H3"]),
        ({"node_type": "hypothesis", "status": "Todo"}, ["H2", "H3"]),
        ({"node_type": "research", "status": "Blocked"}, ["R2"]),
        ({"node_type": "research", "status": "Done"}, []),
    ],
)
def test_search_returns_all_matching_nodes(tree, filters, expected_ids):
    matches = tree.search(**filters)

    assert isinstance(matches, list)
    assert sorted(matches, key=lambda node: node.id) == [tree.get(key) for key in expected_ids]


@pytest.mark.parametrize(
    "filters",
    [
        {"node_type": "unknown"},
        {"node_type": "hypothesis", "status": "Blocked"},
        {"node_type": "research", "status": "Pending"},
        {"node_type": "research", "status": "misspelled"},
    ],
)
def test_search_rejects_invalid_filters(filters):
    tree = il.tree(core_id="C", goal="目的")

    with pytest.raises(InvalidSearchFilterError):
        tree.search(**filters)


def test_search_requires_node_type():
    tree = il.tree(core_id="C", goal="目的")

    with pytest.raises(TypeError):
        tree.search(status="Todo")


@pytest.fixture
def tree_file(tree, tmp_path):
    path = tmp_path / "tree.json"
    tree.update(hypothesis={"id": "H2", "status": "Active"})
    tree.dump(path)
    return path


@pytest.mark.parametrize(
    ("options", "expected_ids"),
    [
        ([], {"H1", "H2", "H3", "R1", "R2"}),
        (["--children-of", "H1"], {"H2", "R1"}),
        (["--children-of", "H1", "--type", "research"], {"R1"}),
        (["--descendants-of", "H1"], {"H2", "R1", "R2"}),
        (["--descendants-of", "H1", "--status", "Blocked"], {"R2"}),
        (["--descendants-of", "H3", "--status", "Blocked"], set()),
        (["--descendants-of", "R2"], set()),
    ],
)
def test_search_cli_selects_nodes_in_scope(tree_file, capsys, options, expected_ids):
    original = tree_file.read_bytes()
    assert main(["tree", "search", str(tree_file), *options, "--json"]) == 0
    records = json.loads(capsys.readouterr().out)
    assert {node["id"] for node in records} == expected_ids
    if "R2" in expected_ids:
        research = next(node for node in records if node["id"] == "R2")
        assert research["type"] == "research"
        assert research["references"] == [{"id": "ref1", "content": "runs/001/result.md"}]
    assert tree_file.read_bytes() == original


@pytest.mark.parametrize(
    ("options", "visible", "including_pruned"),
    [
        ([], {"H3"}, {"H1", "H2", "H3", "R1", "R2"}),
        (["--children-of", "H2"], set(), {"R2"}),
        (["--descendants-of", "H1", "--type", "research", "--status", "Blocked"], set(), {"R2"}),
    ],
)
def test_search_cli_excludes_pruned_branches(
    tree_file, capsys, options, visible, including_pruned
):
    tree = il.load_tree(tree_file)
    tree.update(hypothesis={"id": "H1", "status": "Pruned"})
    tree.dump(tree_file)

    command = ["tree", "search", str(tree_file), *options, "--json"]
    assert main(command) == 0
    assert {row["id"] for row in json.loads(capsys.readouterr().out)} == visible
    assert main([*command, "--include-pruned-branch"]) == 0
    assert {row["id"] for row in json.loads(capsys.readouterr().out)} == including_pruned


def test_search_cli_prints_summary_or_no_matches(tree_file, capsys):
    command = ["tree", "search", str(tree_file)]
    assert main([*command, "--status", "Blocked"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "ID\tTYPE\tSTATUS\tPARENT\tTEXT",
        "R2\tresearch\tBlocked\tH2\t冬の誤差は？",
    ]
    assert main([*command, "--children-of", "R2"]) == 0
    assert capsys.readouterr().out.strip() == "該当なし"


@pytest.mark.parametrize(
    "node_id,node_type", [("C", "core"), ("H1", "hypothesis"), ("R2", "research")]
)
def test_details_cli_prints_one_complete_record(tree_file, tree, capsys, node_id, node_type):
    assert main(["tree", "details", str(tree_file), node_id]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "type": node_type,
        **tree.get(node_id).model_dump(),
    }


def test_ancestors_cli_returns_parent_to_core(tree_file, capsys):
    command = ["tree", "ancestors", str(tree_file)]
    assert main([*command, "R2", "--json"]) == 0
    assert [row["id"] for row in json.loads(capsys.readouterr().out)] == ["H2", "H1", "C"]
    assert main([*command, "R2"]) == 0
    assert (
        capsys.readouterr().out.splitlines()[-1] == "C\tcore\tin_progress\t-\t誤差の要因を調べる"
    )
    assert main([*command, "C", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []


@pytest.mark.parametrize(
    "options",
    [
        ["--type", "research", "--status", "Pending"],
        ["--status", "unknown"],
        ["--children-of", "H1", "--descendants-of", "H2"],
    ],
)
def test_search_cli_rejects_invalid_filters(tree_file, capsys, options):
    with pytest.raises(SystemExit) as error:
        main(["tree", "search", str(tree_file), *options])
    assert error.value.code == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "command,options",
    [
        ("details", []),
        ("ancestors", []),
        ("search", ["--children-of"]),
        ("search", ["--descendants-of"]),
    ],
)
def test_tree_queries_reject_unknown_ids(tree_file, capsys, command, options):
    assert main(["tree", command, str(tree_file), *options, "missing"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "missing" in output.err
