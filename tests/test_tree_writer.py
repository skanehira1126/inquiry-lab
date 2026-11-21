import errno
import json
import signal

import pytest

from inquiry_lab.tree_map import CoreNode
from inquiry_lab.tree_map import HypothesisNode
from inquiry_lab.tree_map import ResearchNode
from inquiry_lab.tree_map.tree import InquiryTree
from inquiry_lab.tree_map.tree import TreeWriter


def test_writer_dumps_core_without_children():
    tree = InquiryTree(CoreNode(id="目的", goal="誤差を説明する"))

    snapshot = TreeWriter(tree, mode="python").dump()

    assert snapshot["core"]["id"] == "目的"
    assert snapshot["core"]["goal"] == "誤差を説明する"
    assert snapshot["core"]["status"] == "in_progress"
    assert snapshot["core"]["evidence_items"] == []
    assert snapshot["nodes"] == []


def test_dump_preserves_findings_and_typed_parent_links(tmp_path):
    tree = InquiryTree(CoreNode(id="C", goal="誤差を説明する"))
    tree.add(HypothesisNode(id="a", parent="C", hypothesis="季節差がある"))
    tree.add(
        HypothesisNode(
            id="b", parent="a", hypothesis="冬に偏る", status="Pending", result="再観測が必要"
        )
    )
    tree.add(
        ResearchNode(
            id="c",
            parent="b",
            question="冬の誤差は？",
            status="Blocked",
            result="1月の観測が欠けている",
            references=[{"id": "ref1", "content": "runs/001/result.md"}],
        )
    )
    finding = {"id": "F1", "finding": "冬の評価には欠測がある", "node_ids": ["b", "c"]}
    tree.update(core={"status": "stopped", "add_items": [finding]})

    path = tmp_path / "tree.json"
    tree.dump(path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    for snapshot in (saved, tree.dump_dict()):
        assert snapshot["core"]["id"] == "C"
        assert snapshot["core"]["goal"] == "誤差を説明する"
        assert snapshot["core"]["status"] == "stopped"
        assert snapshot["core"]["evidence_items"] == [finding]
        assert isinstance(snapshot["nodes"], list)
        root_hypothesis, refinement, research = sorted(snapshot["nodes"], key=lambda n: n["id"])
        assert root_hypothesis["id"] == "a"
        assert root_hypothesis["type"] == "hypothesis"
        assert root_hypothesis["parent"] == "C"
        assert root_hypothesis["result"] is None
        assert refinement["id"] == "b"
        assert refinement["type"] == "hypothesis"
        assert refinement["parent"] == "a"
        assert refinement["hypothesis"] == "冬に偏る"
        assert refinement["result"] == "再観測が必要"
        assert refinement["status"] == "Pending"
        assert research["id"] == "c"
        assert research["type"] == "research"
        assert research["parent"] == "b"
        assert research["question"] == "冬の誤差は？"
        assert research["result"] == "1月の観測が欠けている"
        assert research["status"] == "Blocked"
        assert research["references"] == [{"id": "ref1", "content": "runs/001/result.md"}]


def test_dump_retains_explicit_hypothesis_constraints(tmp_path):
    tree = InquiryTree(CoreNode(id="C", goal="誤差を説明する"))
    tree.add(
        HypothesisNode(
            id="H", parent="C", hypothesis="季節差がある", constraints=["評価期間をそろえる"]
        )
    )

    path = tmp_path / "tree.json"
    tree.dump(path)
    (hypothesis,) = json.loads(path.read_text(encoding="utf-8"))["nodes"]
    assert hypothesis["constraints"] == ["評価期間をそろえる"]


def test_failed_dump_preserves_previous_file(tmp_path):
    resource = pytest.importorskip("resource")
    path = tmp_path / "tree.json"
    tree = InquiryTree(CoreNode(id="C", goal="目的"))
    tree.dump(path)
    previous = path.read_bytes()
    tree.add(HypothesisNode(id="H", parent="C", hypothesis="a" * 4096))

    # Force a real write failure regardless of how the JSON is serialized or buffered.
    limits = resource.getrlimit(resource.RLIMIT_FSIZE)
    handler = signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, (len(previous), limits[1]))
        with pytest.raises(OSError) as error:
            tree.dump(path)
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, limits)
        signal.signal(signal.SIGXFSZ, handler)

    assert error.value.errno == errno.EFBIG
    assert path.read_bytes() == previous
