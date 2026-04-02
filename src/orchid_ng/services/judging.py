from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from orchid_ng.domain import IdeaCandidate, PairwiseJudgment
from orchid_ng.services.prompts import PromptLibrary, format_ideas
from orchid_ng.services.search import parse_critique_actions


class FactorScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    novelty: float
    soundness: float
    feasibility: float
    clarity: float
    grounding: float


class SearchJudgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_side: Literal["left", "right", "tie"]
    critique: str


class FinalJudgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_side: Literal["left", "right", "tie"]
    reasoning: str
    left_scores: FactorScores
    right_scores: FactorScores


class SearchJudge:
    def __init__(self, model_client, prompt_library: PromptLibrary) -> None:
        self.model_client = model_client
        self.prompt_library = prompt_library

    def compare(
        self, left: IdeaCandidate, right: IdeaCandidate, rubric: str
    ) -> PairwiseJudgment:
        prompt = self.prompt_library.render(
            "search_judge",
            rubric=rubric,
            left_block=format_ideas([left]),
            right_block=format_ideas([right]),
        )
        response = self.model_client.generate(prompt, SearchJudgeResponse)
        winner_id = _winner_id(response.preferred_side, left, right)
        actions = parse_critique_actions(response.critique, target_idea_id=winner_id)
        return PairwiseJudgment(
            judge_role="search",
            rubric=rubric,
            left_id=left.idea_id,
            right_id=right.idea_id,
            winner_id=winner_id,
            preferred_side=response.preferred_side,
            critique=response.critique,
            next_actions=actions,
            reasons={"overall": response.critique},
            metadata={"judge_model": self.model_client.model_name},
        )


class FinalJudge:
    def __init__(self, model_client, prompt_library: PromptLibrary) -> None:
        self.model_client = model_client
        self.prompt_library = prompt_library

    def compare(
        self, left: IdeaCandidate, right: IdeaCandidate, rubric: str
    ) -> PairwiseJudgment:
        prompt = self.prompt_library.render(
            "final_judge",
            rubric=rubric,
            left_block=format_ideas([left]),
            right_block=format_ideas([right]),
        )
        response = self.model_client.generate(prompt, FinalJudgeResponse)
        winner_id = _winner_id(response.preferred_side, left, right)
        factor_scores = {
            left.idea_id: response.left_scores.model_dump(mode="json"),
            right.idea_id: response.right_scores.model_dump(mode="json"),
        }
        return PairwiseJudgment(
            judge_role="final",
            rubric=rubric,
            left_id=left.idea_id,
            right_id=right.idea_id,
            winner_id=winner_id,
            preferred_side=response.preferred_side,
            critique=response.reasoning,
            factor_scores=factor_scores,
            reasons={"overall": response.reasoning},
            metadata={"judge_model": self.model_client.model_name},
        )


def _winner_id(
    preferred_side: Literal["left", "right", "tie"],
    left: IdeaCandidate,
    right: IdeaCandidate,
) -> str | None:
    if preferred_side == "left":
        return left.idea_id
    if preferred_side == "right":
        return right.idea_id
    return None
