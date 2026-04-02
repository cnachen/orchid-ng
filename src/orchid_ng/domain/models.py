from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _join_fragments(fragments: list[str]) -> str:
    return " ".join(fragment.strip() for fragment in fragments if fragment.strip())


def _trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip()


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_items: list[str] = []
    for item in items:
        normalized = " ".join(item.split()).strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique_items.append(normalized)
    return unique_items


def _truncate_list(items: list[str], limit: int) -> list[str]:
    return _dedupe_preserve(items)[:limit]


def _keyword_phrase(text: str) -> str:
    stopwords = {
        "a",
        "an",
        "and",
        "for",
        "the",
        "of",
        "to",
        "via",
        "with",
        "using",
        "in",
        "on",
        "by",
    }
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in stopwords
    ]
    return "-".join(tokens[:3]) if tokens else ""


class OrchidModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


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


class TaskDescription(OrchidModel):
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    research_area: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    research_objective: list[str] = Field(default_factory=list)
    contributions: list[str] = Field(default_factory=list)


class MethodModule(OrchidModel):
    name: str
    description: str | list[str]
    structure: str | list[str] = ""
    key_formula_or_operation: str | list[str] = Field(
        default="",
        alias="key formula or operation",
        serialization_alias="key formula or operation",
    )
    input: str | list[str] = ""
    output: str | list[str] = ""

    @model_validator(mode="after")
    def normalize_formula_field(self) -> "MethodModule":
        for field_name in (
            "description",
            "structure",
            "key_formula_or_operation",
            "input",
            "output",
        ):
            value = getattr(self, field_name)
            if isinstance(value, list):
                setattr(self, field_name, " ".join(value))
        return self


class MethodDescription(OrchidModel):
    summary: str = ""
    modules: list[MethodModule] = Field(
        default_factory=list,
        alias="Modules",
        serialization_alias="Modules",
    )
    framework: str = ""


class ConstraintProfile(OrchidModel):
    time: str = ""
    physical: str = ""
    moral: str = ""


class IdeaCandidate(OrchidModel):
    idea_id: str = Field(default_factory=lambda: make_id("idea"))
    title: str
    summary: str = ""
    hypothesis: str = ""
    mechanism: str = ""
    task_description: TaskDescription = Field(default_factory=TaskDescription)
    method: MethodDescription = Field(default_factory=MethodDescription)
    constraints: ConstraintProfile = Field(default_factory=ConstraintProfile)
    required_conditions: list[str] = Field(default_factory=list)
    resource_cost: str = ""
    open_risks: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    method_name: str = ""
    parent_idea_id: str | None = None
    round_index: int = 0
    provenance: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def synchronize_legacy_fields(self) -> "IdeaCandidate":
        if not self.summary and self.task_description.summary:
            self.summary = self.task_description.summary
        if self.summary and not self.task_description.summary:
            self.task_description.summary = self.summary

        if not self.mechanism and self.method.summary:
            self.mechanism = self.method.summary
        if self.mechanism and not self.method.summary:
            self.method.summary = self.mechanism

        if not self.hypothesis:
            if self.task_description.research_objective:
                self.hypothesis = self.task_description.research_objective[0]
            elif self.task_description.questions:
                self.hypothesis = self.task_description.questions[0]
            else:
                self.hypothesis = self.summary

        has_explicit_card_structure = any(
            [
                self.task_description.questions,
                self.task_description.research_objective,
                self.task_description.contributions,
                self.method.modules,
            ]
        )

        if has_explicit_card_structure and len(self.task_description.questions) > 4:
            self.task_description.questions = _truncate_list(
                self.task_description.questions, 4
            )
        elif has_explicit_card_structure and len(self.task_description.questions) < 4:
            question_candidates = [
                *self.task_description.questions,
                f"What failure mode is {self.title.lower()} trying to resolve?",
                f"Which operating constraints make {self.title.lower()} necessary?",
                f"How should the central mechanism in {self.title.lower()} be evaluated?",
                f"What ablations would verify the key assumption behind {self.title.lower()}?",
            ]
            self.task_description.questions = _truncate_list(question_candidates, 4)

        if (
            has_explicit_card_structure
            and len(self.task_description.research_objective) > 4
        ):
            self.task_description.research_objective = _truncate_list(
                self.task_description.research_objective,
                4,
            )
        elif (
            has_explicit_card_structure
            and len(self.task_description.research_objective) < 4
        ):
            objective_candidates = [
                *self.task_description.research_objective,
                *[
                    question.rstrip("?").replace("How should", "Develop")
                    for question in self.task_description.questions[:2]
                ],
                "Quantify performance under the stated operating constraints.",
                "Produce an interpretable implementation and evaluation plan.",
            ]
            self.task_description.research_objective = _truncate_list(
                objective_candidates,
                4,
            )

        if has_explicit_card_structure or self.required_conditions:
            condition_candidates = list(self.required_conditions)
            if not condition_candidates and self.task_description.research_objective:
                condition_candidates.extend(
                    self.task_description.research_objective[:3]
                )
            condition_candidates.extend(
                item
                for item in [
                    "Access to the local frozen literature snapshot",
                    self.constraints.time,
                    self.constraints.physical,
                ]
                if item
            )
            self.required_conditions = _truncate_list(condition_candidates, 3)

        if has_explicit_card_structure or self.open_risks:
            risk_candidates = list(self.open_risks)
            if not risk_candidates and any(
                [
                    self.constraints.time,
                    self.constraints.physical,
                    self.constraints.moral,
                ]
            ):
                risk_candidates.extend(
                    item
                    for item in [
                        self.constraints.time,
                        self.constraints.physical,
                        self.constraints.moral,
                    ]
                    if item
                )
            risk_candidates.extend(
                [
                    "Threshold calibration may fail under domain shift.",
                    "The proposed signal may overfit to a narrow writing style.",
                    "Evaluation may under-cover edge cases in the target population.",
                ]
            )
            self.open_risks = _truncate_list(risk_candidates, 3)

        if has_explicit_card_structure and len(self.task_description.contributions) < 5:
            contribution_candidates = [
                *self.task_description.contributions,
                *[
                    f"A benchmark-oriented implementation and evaluation plan for {objective.rstrip('.')}"
                    for objective in self.task_description.research_objective[:2]
                ],
            ]
            if self.method.modules:
                contribution_candidates.append(
                    "A five-module implementation blueprint with explicit component interfaces."
                )
            contribution_candidates.append(
                "A targeted error analysis covering failure modes on the intended user population."
            )
            self.task_description.contributions = _truncate_list(
                contribution_candidates, 5
            )
        elif len(self.task_description.contributions) > 5:
            self.task_description.contributions = _truncate_list(
                self.task_description.contributions,
                5,
            )

        if has_explicit_card_structure and len(self.task_description.keywords) < 6:
            keyword_candidates = _dedupe_preserve(
                [
                    *self.task_description.keywords,
                    _keyword_phrase(self.title),
                    _keyword_phrase(self.hypothesis),
                    *[
                        _keyword_phrase(module.name)
                        for module in self.method.modules[:3]
                    ],
                    *[
                        _keyword_phrase(area)
                        for area in self.task_description.research_area
                    ],
                ]
            )
            fallback_keywords = [
                "robustness",
                "evaluation",
                "calibration",
                "grounding",
            ]
            self.task_description.keywords = _truncate_list(
                [*keyword_candidates, *fallback_keywords],
                6,
            )
        elif len(self.task_description.keywords) > 6:
            self.task_description.keywords = _truncate_list(
                self.task_description.keywords,
                6,
            )

        if has_explicit_card_structure and len(self.task_description.research_area) < 3:
            pool = " ".join(
                [
                    self.title,
                    self.summary,
                    self.hypothesis,
                    self.mechanism,
                    *self.task_description.keywords,
                ]
            ).lower()
            area_candidates = list(self.task_description.research_area)
            if any(token in pool for token in ("text", "language", "writing")):
                area_candidates.append("Natural Language Processing")
            if any(
                token in pool for token in ("detection", "classification", "threshold")
            ):
                area_candidates.append("Machine Learning")
            if any(token in pool for token in ("robust", "fair", "evaluation", "risk")):
                area_candidates.append("Evaluation and Robustness")
            self.task_description.research_area = _truncate_list(area_candidates, 3)
        elif len(self.task_description.research_area) > 3:
            self.task_description.research_area = _truncate_list(
                self.task_description.research_area,
                3,
            )

        self.supporting_evidence_ids = _truncate_list(self.supporting_evidence_ids, 3)

        if (
            len(self.task_description.summary.split()) < 130
            or len(self.task_description.summary.split()) > 150
        ):
            question_block = (
                "Key research questions include: "
                + "; ".join(self.task_description.questions[:2])
                + "."
                if self.task_description.questions
                else ""
            )
            objective_block = (
                "The main objectives are: "
                + "; ".join(self.task_description.research_objective[:2])
                + "."
                if self.task_description.research_objective
                else ""
            )
            contribution_block = (
                "Expected contributions include: "
                + "; ".join(self.task_description.contributions[:2])
                + "."
                if self.task_description.contributions
                else ""
            )
            constraint_block = (
                "The operating constraints are: "
                + "; ".join(
                    item
                    for item in [
                        self.constraints.time,
                        self.constraints.physical,
                        self.constraints.moral,
                    ]
                    if item
                )
                + "."
                if any(
                    [
                        self.constraints.time,
                        self.constraints.physical,
                        self.constraints.moral,
                    ]
                )
                else ""
            )
            self.task_description.summary = _trim_words(
                _join_fragments(
                    [
                        self.summary,
                        self.hypothesis,
                        question_block,
                        objective_block,
                        contribution_block,
                        constraint_block,
                    ]
                ),
                max_words=150,
            )
            self.summary = self.task_description.summary

        if (
            len(self.method.summary.split()) < 135
            or len(self.method.summary.split()) > 150
        ):
            module_block = (
                "Key modules are: "
                + "; ".join(
                    f"{module.name}: {module.description}"
                    for module in self.method.modules[:5]
                )
                + "."
                if self.method.modules
                else ""
            )
            evaluation_block = (
                "The design should stay realistic under "
                + (self.resource_cost or "moderate compute")
                + " and preserve interpretability for downstream evaluation."
            )
            self.method.summary = _trim_words(
                _join_fragments(
                    [
                        self.mechanism,
                        module_block,
                        self.method.framework,
                        evaluation_block,
                    ]
                ),
                max_words=150,
            )
            self.mechanism = self.method.summary

        if self.method.modules and (
            len(self.method.framework.split()) < 120
            or len(self.method.framework.split()) > 135
        ):
            ordered_steps = [
                f"{index}) {module.name}: {module.description}"
                for index, module in enumerate(self.method.modules, start=1)
            ]
            tail = (
                f"Evaluation should account for {self.resource_cost} resource usage and risks such as "
                + "; ".join(self.open_risks[:3])
                + "."
                if self.open_risks
                else ""
            )
            conditions = (
                "Deployment assumes " + "; ".join(self.required_conditions[:3]) + "."
                if self.required_conditions
                else ""
            )
            self.method.framework = _trim_words(
                _join_fragments(
                    [
                        "The proposed pipeline proceeds as follows.",
                        *ordered_steps,
                        conditions,
                        tail,
                    ]
                ),
                max_words=135,
            )

        return self


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
