from typing import Literal
from typing import Required
from typing import TypedDict

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


CoreStatus = Literal["in_progress", "completed", "stopped", "blocked"]
HypothesisStatus = Literal["Todo", "Active", "Fixed", "Pruned", "Pending"]
ResearchStatus = Literal["Todo", "Active", "Running", "Done", "Blocked"]


class Evidence(TypedDict):
    id: str
    finding: str
    node_ids: list[str]


class CoreChanges(TypedDict, total=False):
    add_items: list[Evidence]
    status: CoreStatus
    delete_item_ids: list[str]


class CoreNode(BaseModel):
    id: str = Field(..., description="Core ID")
    goal: str = Field(..., description="分析の目的")
    evidence_items: list[Evidence] = Field(
        default_factory=list, description="goalを支持する結果群"
    )
    status: CoreStatus = Field(
        default="in_progress", description="goalテーマに対する分析取り組みの状態"
    )

    model_config = ConfigDict(validate_assignment=True)

    def update(self, content: CoreChanges):
        if add_items := content.get("add_items", None):
            self.add_evidence(add_items)

        if "status" in content:
            self.update_status(content["status"])

        if delete_item_ids := content.get("delete_item_ids", None):
            self.delete_evidence(delete_item_ids)

    def update_status(
        self,
        status: CoreStatus,
    ):
        self.status = status

    def add_evidence(self, add_items: list[Evidence]):
        id_list = [item["id"] for item in add_items]
        if len(id_list) != len(list(set(id_list))):
            raise ValueError("add_items contains duplicate evidence IDs")

        for evidence in add_items:
            if evidence["id"] in [e["id"] for e in self.evidence_items]:
                raise ValueError(f"id '{evidence['id']}' already exists.")

        self.evidence_items = [*self.evidence_items, *add_items]

    def delete_evidence(self, evidence_ids: list[str]):
        self.evidence_items = [
            evidence for evidence in self.evidence_items if evidence["id"] not in evidence_ids
        ]


class HypothesisChanges(TypedDict, total=False):
    result: str | None
    status: HypothesisStatus


class TreeHypothesisChange(HypothesisChanges):
    id: Required[str]


class HypothesisNode(BaseModel):
    """
    Statusについて
    - Todo: 生成状態
    - Active: 調査すると決めたNode
    - Fixed: 決定した意思決定. 仮説が支持されないという結果も含める
    - Pruned: 追わない枝
    """

    id: str = Field(..., description="仮説のNode ID")
    parent: str = Field(..., description="親のNode ID")
    hypothesis: str = Field(..., description="このNodeが担当する仮説")
    constraints: list[str] = Field(
        default_factory=list, description="この仮説の調査に適用する制約"
    )
    result: str | None = Field(None, description="仮説に対する結論")
    status: HypothesisStatus = Field("Todo", description="このNodeの状態")
    model_config = ConfigDict(validate_assignment=True)

    def update(self, content: HypothesisChanges):
        if "result" in content:
            self.result = content["result"]

        if "status" in content:
            self.status = content["status"]


class Reference(TypedDict):
    id: str
    content: str


class ResearchChanges(TypedDict, total=False):
    result: str | None
    status: ResearchStatus
    add_items: list[Reference]
    delete_item_ids: list[str]


class TreeResearchChange(ResearchChanges):
    id: Required[str]


class ResearchNode(BaseModel):
    id: str = Field(..., description="調査Node ID")
    parent: str = Field(..., description="この調査Nodeを生成した仮説NodeのID")
    question: str = Field(..., description="この調査Nodeの問")
    result: str | None = Field(None, description="questionに対する結論")
    status: ResearchStatus = Field("Todo", description="このNodeの状態")
    references: list[Reference] = Field(
        default_factory=list, description="この結果を参照するための情報参照先"
    )
    model_config = ConfigDict(validate_assignment=True)

    def update(self, content: ResearchChanges):
        if add_items := content.get("add_items", None):
            self.add_references(add_items)

        if "result" in content:
            self.result = content["result"]

        if "status" in content:
            self.status = content["status"]

        if delete_item_ids := content.get("delete_item_ids", None):
            self.delete_references(delete_item_ids)

    def add_references(self, add_items: list[Reference]):
        id_list = [item["id"] for item in add_items]
        if len(id_list) != len(list(set(id_list))):
            raise ValueError("add_items contains duplicate reference IDs")

        for ref in add_items:
            if ref["id"] in [r["id"] for r in self.references]:
                raise ValueError(f"id '{ref['id']}' already exists.")

        self.references = [*self.references, *add_items]

    def delete_references(self, reference_ids: list[str]):
        self.references = [ref for ref in self.references if ref["id"] not in reference_ids]
