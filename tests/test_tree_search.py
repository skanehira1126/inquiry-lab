import pytest

import inquiry_lab as il
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
