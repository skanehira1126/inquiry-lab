import pytest

from inquiry_lab.exceptions import InvalidConnectionError
from inquiry_lab.exceptions import ParentNotFoundError
from inquiry_lab.tree_map import CoreNode
from inquiry_lab.tree_map import HypothesisNode
from inquiry_lab.tree_map import ResearchNode
from inquiry_lab.tree_map.tree import InquiryTree


def test_traverse_branch_from_core_and_back():
    tree = InquiryTree("Core-001", "予測誤差を説明する")
    core = tree.get("Core-001")
    hypothesis = HypothesisNode(id="H1", parent=core.id, hypothesis="季節性がある")
    refinement = HypothesisNode(id="H2", parent="H1", hypothesis="冬に偏る")
    survey = ResearchNode(id="R1", parent="H1", question="月別の誤差は？")
    winter = ResearchNode(id="R2", parent="H2", question="冬の誤差は？")
    for node in (hypothesis, refinement, survey, winter):
        tree.add(node)

    assert tree.get("R2") == winter
    assert tree.children_of(core.id) == [hypothesis]
    assert tree.children_of("H1") == [refinement, survey]
    assert tree.children_of("R1") == []
    assert tree.ancestors_of("R2") == [refinement, hypothesis, core]
    assert tree.ancestors_of(core.id) == []


def test_duplicate_id_preserves_existing_node():
    tree = InquiryTree("C", "目的")
    with pytest.raises(ValueError, match="C"):
        tree.add(HypothesisNode(id="C", parent="C", hypothesis="仮説"))
    assert tree.get("C") == CoreNode(id="C", goal="目的")


@pytest.mark.parametrize(
    ("node", "error"),
    [
        (HypothesisNode(id="new", parent="missing", hypothesis="仮説"), ParentNotFoundError),
        (ResearchNode(id="new", parent="C", question="問い"), InvalidConnectionError),
        (HypothesisNode(id="new", parent="R", hypothesis="仮説"), InvalidConnectionError),
        (ResearchNode(id="new", parent="R", question="問い"), InvalidConnectionError),
    ],
)
def test_invalid_parent_leaves_candidate_unregistered(node, error):
    tree = InquiryTree("C", "目的")
    tree.add(HypothesisNode(id="H", parent="C", hypothesis="仮説"))
    tree.add(ResearchNode(id="R", parent="H", question="問い"))
    with pytest.raises(error):
        tree.add(node)
    with pytest.raises(KeyError):
        tree.get(node.id)


@pytest.mark.parametrize("lookup", [InquiryTree.children_of, InquiryTree.ancestors_of])
def test_traversal_rejects_unknown_id(lookup):
    with pytest.raises(KeyError):
        lookup(InquiryTree("C", "目的"), "missing")


def test_core_retains_findings_and_evidence_ids_in_json():
    findings = [
        {"finding": "冬に誤差が大きい", "node_ids": ["H1", "R1"]},
        {"finding": "夏は安定している", "node_ids": ["R2"]},
    ]
    core = CoreNode(id="C", goal="目的", evidence_items=findings)
    assert CoreNode.model_validate_json(core.model_dump_json()).evidence_items == findings
