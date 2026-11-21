import json

from pydantic import ValidationError
import pytest

import inquiry_lab as il
from inquiry_lab.exceptions import DuplicateNodeIdError
from inquiry_lab.exceptions import InvalidConnectionError
from inquiry_lab.exceptions import InvalidTreeFormatError
from inquiry_lab.exceptions import NodeNotFoundError
from inquiry_lab.exceptions import ParentNotFoundError
from inquiry_lab.tree_map import CoreNode
from inquiry_lab.tree_map import HypothesisNode
from inquiry_lab.tree_map import ResearchNode
from inquiry_lab.tree_map import load_tree
from inquiry_lab.tree_map.tree import InquiryTree


def test_traverse_branch_from_core_and_back():
    tree = InquiryTree(CoreNode(id="Core-001", goal="予測誤差を説明する"))
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
    tree = InquiryTree(CoreNode(id="C", goal="目的"))
    with pytest.raises(DuplicateNodeIdError, match="C"):
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
    tree = InquiryTree(CoreNode(id="C", goal="目的"))
    tree.add(HypothesisNode(id="H", parent="C", hypothesis="仮説"))
    tree.add(ResearchNode(id="R", parent="H", question="問い"))
    with pytest.raises(error):
        tree.add(node)
    with pytest.raises(KeyError):
        tree.get(node.id)


@pytest.mark.parametrize("lookup", [InquiryTree.children_of, InquiryTree.ancestors_of])
def test_traversal_rejects_unknown_id(lookup):
    with pytest.raises(NodeNotFoundError):
        lookup(InquiryTree(CoreNode(id="C", goal="目的")), "missing")


def test_core_retains_updated_findings_in_order_in_json():
    winter = {"id": "F1", "finding": "冬に誤差が大きい", "node_ids": ["H1", "R1"]}
    summer = {"id": "F2", "finding": "夏は安定している", "node_ids": ["R2"]}
    autumn = {"id": "F3", "finding": "秋は観測が少ない", "node_ids": ["R3"]}
    core = CoreNode(id="C", goal="目的", status="blocked", evidence_items=[winter, summer])

    core.update({"add_items": [autumn], "delete_item_ids": ["F1"]})

    restored = CoreNode.model_validate_json(core.model_dump_json())
    assert restored.evidence_items == [summer, autumn]
    assert restored.status == "blocked"


@pytest.mark.parametrize(
    ("last_id", "message"),
    [("F2", "duplicate"), ("F1", "F1")],
    ids=["duplicate-in-batch", "already-registered"],
)
def test_core_add_evidence_rejects_duplicate_batch_without_adding_items(last_id, message):
    existing = {"id": "F1", "finding": "既存の結果", "node_ids": ["R1"]}
    core = CoreNode(id="C", goal="目的", evidence_items=[existing])

    with pytest.raises(ValueError, match=message):
        core.add_evidence(
            [
                {"id": "F2", "finding": "追加候補", "node_ids": ["R2"]},
                {"id": last_id, "finding": "重複する候補", "node_ids": ["R3"]},
            ]
        )

    assert core.evidence_items == [existing]


@pytest.mark.parametrize("status", ["", None])
def test_core_update_rejects_explicit_invalid_status(status):
    core = CoreNode(id="C", goal="目的")
    with pytest.raises(ValidationError, match="status"):
        core.update({"status": status})
    assert core.status == "in_progress"


def test_core_update_rejects_evidence_without_node_ids():
    core = CoreNode(id="C", goal="目的")
    with pytest.raises(ValidationError, match="node_ids"):
        core.update({"add_items": [{"id": "F1", "finding": "出典が未指定"}]})
    assert core.evidence_items == []


def test_tree_rejects_unknown_evidence_node_before_applying_core_changes():
    tree = il.tree("C", "目的")
    tree.add(HypothesisNode(id="H1", parent="C", hypothesis="季節差がある"))
    findings = [
        {"id": "F1", "finding": "冬の観測", "node_ids": ["H1"]},
        {"id": "F2", "finding": "夏の観測", "node_ids": ["R999"]},
    ]

    with pytest.raises(NodeNotFoundError, match="R999"):
        tree.update(core={"status": "completed", "add_items": findings})

    assert tree.core.evidence_items == []
    assert tree.core.status == "in_progress"


def test_tree_updates_preserve_target_ids_and_replace_selected_references():
    tree = il.tree(core_id="C", goal="目的")
    hypothesis = HypothesisNode(id="H", parent="C", hypothesis="季節差がある")
    research = ResearchNode(
        id="R",
        parent="H",
        question="月別の誤差は？",
        references=[{"id": "old", "content": "runs/001/result.md"}],
    )
    tree.add(hypothesis)
    tree.add(research)
    reference = {"id": "new", "content": "runs/002/result.md"}
    hypothesis_change = {"id": "H", "status": "Active"}
    research_change = {"id": "R", "add_items": [reference], "delete_item_ids": ["old"]}

    tree.update(hypothesis=hypothesis_change, research=research_change)

    assert hypothesis.status == "Active"
    assert research.references == [reference]
    assert hypothesis_change["id"] == "H"
    assert research_change["id"] == "R"


def test_public_tree_factories_round_trip(tmp_path):
    tree = il.tree(core_id="C", goal="目的")
    core = tree.get("C")
    core.status = "completed"
    path = tmp_path / "tree.json"
    tree.dump(path)

    assert il.load_tree(path).get("C") == CoreNode(id="C", goal="目的", status="completed")


def test_load_tree_accepts_a_child_listed_before_its_parent(tmp_path):
    source = {
        "core": {"id": "C", "goal": "目的"},
        "nodes": [
            {"type": "research", "id": "R", "parent": "H", "question": "問い"},
            {"type": "hypothesis", "id": "H", "parent": "C", "hypothesis": "仮説"},
        ],
    }
    path = tmp_path / "tree.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    restored = load_tree(path)

    assert [node.id for node in restored.ancestors_of("R")] == ["H", "C"]


@pytest.mark.parametrize(
    ("nodes", "error", "detail"),
    [
        ({}, InvalidTreeFormatError, "nodes"),
        ([{"type": "unknown"}], InvalidTreeFormatError, "type"),
        ([{"type": "research", "id": "R", "parent": "H"}], InvalidTreeFormatError, "question"),
        (
            [{"type": "hypothesis", "id": "C", "parent": "C", "hypothesis": "a"}],
            DuplicateNodeIdError,
            "C",
        ),
        (
            [{"type": "hypothesis", "id": "H", "parent": "missing", "hypothesis": "a"}],
            ParentNotFoundError,
            "missing",
        ),
        (
            [{"type": "hypothesis", "id": "H", "parent": "H", "hypothesis": "a"}],
            InvalidConnectionError,
            "H",
        ),
    ],
)
def test_load_tree_reports_invalid_tree_data(tmp_path, nodes, error, detail):
    path = tmp_path / "tree.json"
    path.write_text(json.dumps({"core": {"id": "C", "goal": "目的"}, "nodes": nodes}))
    with pytest.raises(error, match=detail):
        il.load_tree(path)


def test_load_tree_preserves_file_and_json_errors(tmp_path):
    path = tmp_path / "tree.json"
    with pytest.raises(FileNotFoundError):
        il.load_tree(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        il.load_tree(path)
