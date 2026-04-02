from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class OrchidModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceType(StrEnum):
    BACKGROUND = "background"
    IDEA_SPECIFIC = "idea_specific"


class CritiqueActionType(StrEnum):
    ADD_EVIDENCE = "add_evidence"
    NARROW_CLAIM = "narrow_claim"
    CLARIFY_ASSUMPTION = "clarify_assumption"
    DROP_DEPENDENCY = "drop_dependency"
    MERGE_IDEAS = "merge_ideas"


class ResearchTopic(OrchidModel):
    topic_id: str = Field(default_factory=lambda: make_id("topic"))
    title: str
    question: str
    description: str = ""
    constraints: list[str] = Field(default_factory=list)
    budget_tokens: int = 20_000
    desired_idea_count: int = 2
    tags: list[str] = Field(default_factory=list)


class PaperRecord(OrchidModel):
    paper_id: str
    title: str
    abstract: str
    year: int | None = None
    venue: str | None = None
    authors: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)


class EvidenceNote(OrchidModel):
    note_id: str = Field(default_factory=lambda: make_id("evidence"))
    claim: str
    evidence_type: EvidenceType
    source_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)
    rationale: str = ""


class IdeaCandidate(OrchidModel):
    idea_id: str = Field(default_factory=lambda: make_id("idea"))
    title: str
    summary: str
    hypothesis: str
    mechanism: str
    required_conditions: list[str] = Field(default_factory=list)
    resource_cost: str
    open_risks: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    method_name: str = ""
    parent_idea_id: str | None = None
    round_index: int = 0
    provenance: list[str] = Field(default_factory=list)


class CritiqueAction(OrchidModel):
    action_id: str = Field(default_factory=lambda: make_id("action"))
    action_type: CritiqueActionType
    target_idea_id: str | None = None
    instruction: str
    rationale: str = ""


class PairwiseJudgment(OrchidModel):
    judgment_id: str = Field(default_factory=lambda: make_id("judgment"))
    judge_role: Literal["search", "final"]
    rubric: str
    left_id: str
    right_id: str
    winner_id: str | None = None
    preferred_side: Literal["left", "right", "tie"]
    critique: str = ""
    next_actions: list[CritiqueAction] = Field(default_factory=list)
    factor_scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    reasons: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationReport(OrchidModel):
    run_id: str
    method_name: str
    evaluated_idea_ids: list[str]
    pairwise_scores: dict[str, float]
    upstream_factors: dict[str, dict[str, float]]
    downstream_outcomes: dict[str, float] = Field(default_factory=dict)
    overall_preference_order: list[str]
    pairwise_judgment_count: int
    summary: str


class RunManifest(OrchidModel):
    run_id: str
    topic_id: str
    method_name: str
    status: Literal["created", "ideated", "evaluated"] = "created"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model_name: str
    corpus_path: str | None = None
    prompt_dir: str


class ExecutionResult(OrchidModel):
    run_id: str
    status: Literal["not_started", "planned", "completed"] = "not_started"
    notes: str = ""
    metrics: dict[str, float] = Field(default_factory=dict)
