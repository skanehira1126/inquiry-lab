from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class Evidence(TypedDict):
    finding: str
    node_ids: list[str]


class CoreNode(BaseModel):
    id: str = Field(..., description="Core ID")
    goal: str = Field(..., description="分析の目的")
    evidence_items: list[Evidence] = Field(
        default_factory=list, description="goalを支持する結果群"
    )
    status: Literal["in_progress", "completed", "stopped", "blocked"] = Field(
        default="in_progress", description="goalテーマに対する分析取り組みの状態"
    )


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
    result: str | None = Field(None, description="仮説に対する結論")
    status: Literal["Todo", "Active", "Fixed", "Pruned"] = Field(
        "Todo", description="このNodeの状態"
    )
    history: list[str] = Field(default_factory=list, description="結論の更新履歴")


class ResearchNode(BaseModel):
    id: str = Field(..., description="調査Node ID")
    parent: str = Field(..., description="この調査Nodeを生成した仮説NodeのID")
    question: str = Field(..., description="この調査Nodeの問")
    result: str | None = Field(None, description="questionに対する結論")
    status: Literal["Todo", "Active", "Running", "Done", "Pruned"] = Field(
        "Todo", description="このNodeの状態"
    )
    references: list[str] = Field(
        default_factory=list, description="この結果を参照するための情報参照先"
    )
