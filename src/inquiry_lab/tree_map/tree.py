from inquiry_lab.exceptions import InvalidConnectionError
from inquiry_lab.exceptions import ParentNotFoundError
from inquiry_lab.tree_map.node import CoreNode
from inquiry_lab.tree_map.node import HypothesisNode
from inquiry_lab.tree_map.node import ResearchNode


BasicNodes = HypothesisNode | ResearchNode


class InquiryTree:
    def __init__(self, core_id: str, goal: str):
        self._nodes: dict[str, CoreNode | HypothesisNode | ResearchNode] = {}
        self.core_id = core_id

        self._nodes[core_id] = CoreNode(
            id=core_id,
            goal=goal,
        )

    def add(self, node: BasicNodes):
        if node.id in self._nodes:
            raise ValueError(f"Node ID {node.id!r} is already in use.")
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
        node = self._nodes[node_id]
        return node

    def children_of(self, node_id: str) -> list[BasicNodes]:
        node = self.get(node_id)
        return [
            n for n in self._nodes.values() if not isinstance(n, CoreNode) and n.parent == node.id
        ]

    def ancestors_of(self, node_id: str) -> list[CoreNode | BasicNodes]:
        node = self.get(node_id)

        ancestors = []
        while not isinstance(node, CoreNode):
            node = self.get(node.parent)
            ancestors.append(node)
        return ancestors
