import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
from typing import get_args

from inquiry_lab.exceptions import DuplicateNodeIdError
from inquiry_lab.exceptions import InvalidConnectionError
from inquiry_lab.exceptions import InvalidSearchFilterError
from inquiry_lab.exceptions import NodeNotFoundError
from inquiry_lab.exceptions import NodeTypeError
from inquiry_lab.exceptions import ParentNotFoundError
from inquiry_lab.tree_map.node import CoreChanges
from inquiry_lab.tree_map.node import CoreNode
from inquiry_lab.tree_map.node import HypothesisNode
from inquiry_lab.tree_map.node import HypothesisStatus
from inquiry_lab.tree_map.node import ResearchNode
from inquiry_lab.tree_map.node import ResearchStatus
from inquiry_lab.tree_map.node import TreeHypothesisChange
from inquiry_lab.tree_map.node import TreeResearchChange


BasicNodes = HypothesisNode | ResearchNode
SearchType = Literal["hypothesis", "research"]


class InquiryTree:
    def __init__(self, core_node: CoreNode):
        self._nodes: dict[str, CoreNode | HypothesisNode | ResearchNode] = {}
        self.core_id = core_node.id

        self._nodes[core_node.id] = core_node

    def add(self, node: BasicNodes):
        if node.id in self._nodes:
            raise DuplicateNodeIdError(f"Node ID {node.id!r} is already in use.")
        if node.parent not in self._nodes:
            raise ParentNotFoundError(
                f"Cannot add {node.id!r}: parent {node.parent!r} was not found."
            )

        parent_node = self.get(node.parent)
        if isinstance(parent_node, ResearchNode):
            raise InvalidConnectionError(
                f"Cannot add {node.id!r} under research node {parent_node.id!r}: "
                "research nodes cannot have children."
            )
        if isinstance(parent_node, CoreNode) and isinstance(node, ResearchNode):
            raise InvalidConnectionError(
                f"Cannot add research node {node.id!r} under core {parent_node.id!r}: "
                "research nodes require a hypothesis parent."
            )

        self._nodes[node.id] = node

    def get(self, node_id: str) -> CoreNode | BasicNodes:
        try:
            return self._nodes[node_id]
        except KeyError as error:
            raise NodeNotFoundError(node_id) from error

    def update(
        self,
        core: CoreChanges | None = None,
        hypothesis: TreeHypothesisChange | None = None,
        research: TreeResearchChange | None = None,
    ):
        if core is not None:
            core_node = self.get(self.core_id)
            if isinstance(core_node, CoreNode):
                core_node.update(core)
            else:
                raise NodeTypeError(f"Node {self.core_id!r} must be CoreNode.")

        if hypothesis is not None:
            node_id = hypothesis["id"]
            hypothesis_node = self.get(node_id)
            if isinstance(hypothesis_node, HypothesisNode):
                hypothesis_node.update(hypothesis)
            else:
                raise NodeTypeError(f"Node {node_id!r} must be HypothesisNode.")

        if research is not None:
            node_id = research["id"]
            research_node = self.get(node_id)
            if isinstance(research_node, ResearchNode):
                research_node.update(research)
            else:
                raise NodeTypeError(f"Node {node_id!r} must be ResearchNode.")

    def search(
        self,
        node_type: SearchType | None,
        status: str | None = None,
        *,
        children_of: str | None = None,
        descendants_of: str | None = None,
    ) -> list[BasicNodes]:
        if node_type == "hypothesis":
            node_class = HypothesisNode
            valid_status = get_args(HypothesisStatus)
        elif node_type == "research":
            node_class = ResearchNode
            valid_status = get_args(ResearchStatus)
        elif node_type is None:
            node_class = BasicNodes
            valid_status = (*get_args(HypothesisStatus), *get_args(ResearchStatus))
        else:
            raise InvalidSearchFilterError(
                f"node_type must be hypothesis or research, not {node_type}"
            )
        if status is not None and status not in valid_status:
            choices = ", ".join(dict.fromkeys(valid_status))
            raise InvalidSearchFilterError(
                f"Invalid status {status!r}. Expected one of: {choices}"
            )

        if children_of is not None and descendants_of is not None:
            raise InvalidSearchFilterError("children_of and descendants_of are mutually exclusive")
        if children_of is not None:
            candidates = self.children_of(children_of)
        elif descendants_of is not None:
            candidates = self.descendants_of(descendants_of)
        else:
            candidates = [n for n in self._nodes.values() if not isinstance(n, CoreNode)]
        return [
            n
            for n in candidates
            if isinstance(n, node_class) and (status is None or n.status == status)
        ]

    def children_of(self, node_id: str) -> list[BasicNodes]:
        node = self.get(node_id)
        return [
            n for n in self._nodes.values() if not isinstance(n, CoreNode) and n.parent == node.id
        ]

    def descendants_of(self, node_id: str) -> list[BasicNodes]:
        reached = {self.get(node_id).id}
        descendants = []
        # add() registers parents before their children, including when loading a saved tree.
        for node in self._nodes.values():
            if not isinstance(node, CoreNode) and node.parent in reached:
                reached.add(node.id)
                descendants.append(node)
        return descendants

    def ancestors_of(self, node_id: str) -> list[CoreNode | BasicNodes]:
        node = self.get(node_id)

        ancestors = []
        while not isinstance(node, CoreNode):
            node = self.get(node.parent)
            ancestors.append(node)
        return ancestors

    def dump(self, file_path: str | Path) -> None:
        destination = Path(file_path).resolve()
        if destination.exists() and not destination.is_file():
            raise OSError(f"Expected a regular file: {destination}")

        output = TreeWriter(self, mode="json").dump()
        with TemporaryDirectory(dir=destination.parent, prefix=".tree-") as temporary:
            staged = Path(temporary) / "tree.json"
            with staged.open("w", encoding="utf-8") as stream:
                json.dump(output, stream)
            if destination.is_file():
                staged.chmod(destination.stat().st_mode & 0o777)
            staged.replace(destination)

    def dump_dict(self):
        writer = TreeWriter(self, mode="python")
        output = writer.dump()

        return output


class TreeWriter:
    def __init__(self, tree: InquiryTree, mode: Literal["python", "json"]):
        self.tree = tree
        self.mode = mode

    def dump(self):
        return {
            "core": self.dump_core(),
            "nodes": self.dump_nodes(),
        }

    def dump_core(self) -> dict:
        core = self.tree.get(self.tree.core_id)
        return core.model_dump(mode=self.mode)

    def dump_nodes(self) -> list[dict]:
        nodes = []
        for node_id, node in self.tree._nodes.items():
            if node_id == self.tree.core_id:
                continue

            node_dict = node.model_dump(mode=self.mode)
            if isinstance(node, ResearchNode):
                node_dict["type"] = "research"
            elif isinstance(node, HypothesisNode):
                node_dict["type"] = "hypothesis"
            else:
                raise TypeError(f"Unknown node type: {type(node)!r}")
            nodes.append(node_dict)

        return nodes
