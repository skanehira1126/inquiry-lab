__all__ = [
    "CoreNode",
    "HypothesisNode",
    "ResearchNode",
]
from collections import defaultdict
from collections import deque
import json
from pathlib import Path

from pydantic import BaseModel
from pydantic import ValidationError

from inquiry_lab.exceptions import DuplicateNodeIdError
from inquiry_lab.exceptions import InvalidConnectionError
from inquiry_lab.exceptions import InvalidTreeFormatError
from inquiry_lab.exceptions import ParentNotFoundError
from inquiry_lab.tree_map.node import CoreNode
from inquiry_lab.tree_map.node import HypothesisNode
from inquiry_lab.tree_map.node import ResearchNode
from inquiry_lab.tree_map.tree import InquiryTree


def tree(core_id: str, goal: str):
    return InquiryTree(CoreNode(id=core_id, goal=goal))


class _SavedTree(BaseModel):
    core: CoreNode
    nodes: list[dict]


def _load_node(fields: dict, index: int) -> ResearchNode | HypothesisNode:
    node_type = fields.pop("type", None)
    if node_type == "research":
        model = ResearchNode
    elif node_type == "hypothesis":
        model = HypothesisNode
    else:
        raise InvalidTreeFormatError(
            f"nodes[{index}].type must be 'research' or 'hypothesis', got {node_type!r}"
        )
    try:
        return model.model_validate(fields)
    except ValidationError as error:
        raise InvalidTreeFormatError(f"nodes[{index}]: {error}") from error


def load_tree(file_path: str | Path) -> InquiryTree:
    with open(file_path, encoding="utf-8") as stream:
        source = json.load(stream)
    try:
        saved = _SavedTree.model_validate(source)
    except ValidationError as error:
        raise InvalidTreeFormatError(str(error)) from error

    tree = InquiryTree(saved.core)
    children = defaultdict(list)
    known_ids = {tree.core_id}
    for index, fields in enumerate(saved.nodes):
        node = _load_node(fields, index)
        if node.id in known_ids:
            raise DuplicateNodeIdError(f"Node ID {node.id!r} is already in use.")
        known_ids.add(node.id)
        children[node.parent].append(node)

    # treeに存在するnode idをdequeで管理すると扱いやすい
    queue = deque([tree.core_id])
    while queue:
        parent_id = queue.popleft()
        for child in children.pop(parent_id, []):
            tree.add(child)
            queue.append(child.id)

    if children:
        if missing := children.keys() - known_ids:
            raise ParentNotFoundError(f"Missing parent IDs: {sorted(missing)}")
        unreachable_nodes = [node.id for group in children.values() for node in group]
        raise InvalidConnectionError(f"Nodes unreachable from Core: {unreachable_nodes}")

    return tree
