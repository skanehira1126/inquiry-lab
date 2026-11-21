import argparse
from collections.abc import Generator
from collections.abc import Sequence
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Unpack
from typing import get_args

from inquiry_lab.tree_map import load_tree
from inquiry_lab.tree_map import tree as new_tree
from inquiry_lab.tree_map.node import CoreChanges
from inquiry_lab.tree_map.node import CoreNode
from inquiry_lab.tree_map.node import CoreStatus
from inquiry_lab.tree_map.node import HypothesisChanges
from inquiry_lab.tree_map.node import HypothesisNode
from inquiry_lab.tree_map.node import HypothesisStatus
from inquiry_lab.tree_map.node import ResearchChanges
from inquiry_lab.tree_map.node import ResearchNode
from inquiry_lab.tree_map.node import ResearchStatus
from inquiry_lab.tree_map.node import TreeHypothesisChange
from inquiry_lab.tree_map.node import TreeResearchChange
from inquiry_lab.tree_map.tree import InquiryTree
from inquiry_lab.tree_map.tree import SearchType
from inquiry_lab.tree_map.tree import tree_lock


class TreeArgumentError(ValueError):
    """The supplied options do not describe a node update."""


@contextmanager
def _edit_tree(path: Path) -> Generator[InquiryTree, None, None]:
    path = path.resolve(strict=True)
    with tree_lock(path):
        tree = load_tree(path)
        yield tree
        tree._dump_locked(path)
    print(path)


def cli_tree_init(path: Path, core_id: str, goal: str) -> None:
    path = path.parent.resolve() / path.name
    with tree_lock(path):
        if path.is_symlink() or path.exists():
            raise FileExistsError(f"Tree destination already exists: {path}")
        new_tree(core_id, goal)._dump_locked(path)
    print(path)


def cli_tree_status(path: Path, hypothesis_id: str) -> None:
    status = load_tree(path).status(path, hypothesis_id)
    print(json.dumps(status, ensure_ascii=False, indent=2))


def cli_add_hypothesis(
    path: Path, node_id: str, parent: str | None, hypothesis: str, constraints: list[str]
) -> None:
    with _edit_tree(path) as tree:
        tree.add(
            HypothesisNode(
                id=node_id,
                parent=tree.core_id if parent is None else parent,
                hypothesis=hypothesis,
                constraints=constraints,
            )
        )


def cli_add_research(path: Path, node_id: str, parent: str, question: str) -> None:
    with _edit_tree(path) as tree:
        tree.add(ResearchNode(id=node_id, parent=parent, question=question))


def _save_update(
    path: Path,
    *,
    core: CoreChanges | None = None,
    hypothesis: TreeHypothesisChange | None = None,
    research: TreeResearchChange | None = None,
) -> None:
    if not (core or (hypothesis and len(hypothesis) > 1) or (research and len(research) > 1)):
        raise TreeArgumentError("specify at least one update option")
    with _edit_tree(path) as tree:
        tree.update(core=core, hypothesis=hypothesis, research=research)


def cli_update_core(
    path: Path, add_evidence: list[list[str]] | None = None, **changes: Unpack[CoreChanges]
) -> None:
    if add_evidence:
        if any(len(item) < 2 for item in add_evidence):
            raise TreeArgumentError("--add-evidence requires ID FINDING [NODE_ID ...]")
        changes["add_items"] = [
            {"id": key, "finding": finding, "node_ids": nodes}
            for key, finding, *nodes in add_evidence
        ]
    _save_update(path, core=changes)


def cli_update_hypothesis(path: Path, node_id: str, **changes: Unpack[HypothesisChanges]) -> None:
    _save_update(path, hypothesis={"id": node_id, **changes})


def cli_update_research(
    path: Path,
    node_id: str,
    add_reference: list[list[str]] | None = None,
    **changes: Unpack[ResearchChanges],
) -> None:
    if add_reference:
        changes["add_items"] = [{"id": key, "content": value} for key, value in add_reference]
    _save_update(path, research={"id": node_id, **changes})


def _summary(node: CoreNode | HypothesisNode | ResearchNode) -> tuple[str, str, str, str, str]:
    if isinstance(node, CoreNode):
        return node.id, "core", node.status, "-", node.goal
    if isinstance(node, HypothesisNode):
        return node.id, "hypothesis", node.status, node.parent, node.hypothesis
    return node.id, "research", node.status, node.parent, node.question


def _node_record(node: CoreNode | HypothesisNode | ResearchNode) -> dict:
    return {"type": _summary(node)[1], **node.model_dump(mode="json")}


def _print_nodes(nodes: Sequence[CoreNode | HypothesisNode | ResearchNode], as_json: bool) -> None:
    if as_json:
        print(json.dumps([_node_record(node) for node in nodes], ensure_ascii=False, indent=2))
    elif nodes:
        print("ID\tTYPE\tSTATUS\tPARENT\tTEXT")
        for node in nodes:
            print("\t".join(" ".join(field.split()) for field in _summary(node)))
    else:
        print("該当なし")


def cli_tree_search(
    path: Path,
    node_type: SearchType | None,
    status: str | None,
    children_of: str | None,
    descendants_of: str | None,
    as_json: bool,
) -> None:
    nodes = load_tree(path).search(
        node_type, status, children_of=children_of, descendants_of=descendants_of
    )
    _print_nodes(nodes, as_json)


def cli_tree_details(path: Path, node_id: str) -> None:
    print(json.dumps(_node_record(load_tree(path).get(node_id)), ensure_ascii=False, indent=2))


def cli_tree_ancestors(path: Path, node_id: str, as_json: bool) -> None:
    _print_nodes(load_tree(path).ancestors_of(node_id), as_json)


def register_tree_commands(tree: argparse.ArgumentParser) -> None:
    actions = tree.add_subparsers(required=True)
    init = actions.add_parser("init", help="create a new tree with its core goal")
    init.add_argument("path", type=Path)
    init.add_argument("--core-id", required=True)
    init.add_argument("--goal", required=True)
    init.set_defaults(func=cli_tree_init)
    status = actions.add_parser("status", help="show the assigned hypothesis and its research")
    status.add_argument("path", type=Path, metavar="TREE")
    status.add_argument("hypothesis_id", metavar="HYPOTHESIS_ID")
    status.set_defaults(func=cli_tree_status)
    search = actions.add_parser("search", help="find hypothesis and research nodes")
    search.add_argument("path", type=Path, help="existing tree JSON file")
    search.add_argument("--type", dest="node_type", choices=get_args(SearchType))
    search.add_argument("--status", help="exact, case-sensitive node status")
    scope = search.add_mutually_exclusive_group()
    scope.add_argument("--children-of", metavar="ID", help="search direct children")
    scope.add_argument("--descendants-of", metavar="ID", help="search descendants at all depths")
    search.add_argument("--json", dest="as_json", action="store_true", help="print complete nodes")
    search.set_defaults(func=cli_tree_search)
    details = actions.add_parser("details", help="show one complete node as JSON")
    details.add_argument("path", type=Path)
    details.add_argument("node_id", metavar="NODE_ID")
    details.set_defaults(func=cli_tree_details)
    ancestors = actions.add_parser(
        "ancestors", help="list ancestors from immediate parent to core"
    )
    ancestors.add_argument("path", type=Path)
    ancestors.add_argument("node_id", metavar="NODE_ID")
    ancestors.add_argument(
        "--json", dest="as_json", action="store_true", help="print complete nodes"
    )
    ancestors.set_defaults(func=cli_tree_ancestors)
    add_hypothesis = actions.add_parser("add-hypothesis", help="add a hypothesis to a saved tree")
    add_hypothesis.add_argument("path", type=Path, help="existing tree JSON file")
    add_hypothesis.add_argument("node_id", metavar="NODE_ID")
    parent = add_hypothesis.add_mutually_exclusive_group(required=True)
    parent.add_argument("--parent", metavar="ID", default=argparse.SUPPRESS)
    parent.add_argument(
        "--core",
        dest="parent",
        action="store_const",
        const=None,
        default=argparse.SUPPRESS,
        help="attach directly to the tree's core",
    )
    add_hypothesis.add_argument("--hypothesis", required=True)
    add_hypothesis.add_argument(
        "--constraint",
        dest="constraints",
        action="append",
        default=[],
        help="constraint for this hypothesis (repeatable)",
    )
    add_hypothesis.set_defaults(func=cli_add_hypothesis)

    add_research = actions.add_parser("add-research", help="add a research node to a hypothesis")
    add_research.add_argument("path", type=Path, help="existing tree JSON file")
    add_research.add_argument("node_id", metavar="NODE_ID")
    add_research.add_argument("--parent", metavar="ID", required=True, help="parent hypothesis ID")
    add_research.add_argument("--question", required=True)
    add_research.set_defaults(func=cli_add_research)

    update = actions.add_parser("update", help="update one saved node")
    update.add_argument("path", type=Path, help="existing tree JSON file")
    targets = update.add_subparsers(required=True)
    core = targets.add_parser("core", argument_default=argparse.SUPPRESS)
    core.add_argument("--status", choices=get_args(CoreStatus))
    core.add_argument(
        "--add-evidence",
        nargs="+",
        action="append",
        metavar="VALUE",
        help="append ID FINDING [NODE_ID ...] (repeatable)",
    )
    core.add_argument("--delete-evidence", dest="delete_item_ids", action="append", metavar="ID")
    core.set_defaults(func=cli_update_core)

    hypothesis = targets.add_parser("hypothesis", argument_default=argparse.SUPPRESS)
    hypothesis.add_argument("--status", choices=get_args(HypothesisStatus))
    hypothesis.set_defaults(func=cli_update_hypothesis)
    research = targets.add_parser("research", argument_default=argparse.SUPPRESS)
    research.add_argument("--status", choices=get_args(ResearchStatus))
    research.add_argument("--add-reference", nargs=2, action="append", metavar=("ID", "CONTENT"))
    research.add_argument(
        "--delete-reference", dest="delete_item_ids", action="append", metavar="ID"
    )
    research.set_defaults(func=cli_update_research)
    for target in (hypothesis, research):
        target.add_argument("node_id", metavar="NODE_ID")
        result = target.add_mutually_exclusive_group()
        result.add_argument("--result", help="set the node's result")
        result.add_argument(
            "--clear-result",
            dest="result",
            action="store_const",
            const=None,
            help="clear the saved result",
        )
