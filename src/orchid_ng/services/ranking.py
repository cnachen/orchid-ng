from __future__ import annotations

from collections import defaultdict

from orchid_ng.domain import EvaluationReport, IdeaCandidate, PairwiseJudgment

FACTOR_NAMES = ("novelty", "soundness", "feasibility", "clarity", "grounding")


def aggregate_pairwise_scores(
    ideas: list[IdeaCandidate],
    judgments: list[PairwiseJudgment],
) -> dict[str, float]:
    wins = defaultdict(float)
    appearances = defaultdict(int)
    for idea in ideas:
        wins[idea.idea_id] = 0.0
        appearances[idea.idea_id] = 0
    for judgment in judgments:
        appearances[judgment.left_id] += 1
        appearances[judgment.right_id] += 1
        if judgment.winner_id == judgment.left_id:
            wins[judgment.left_id] += 1.0
        elif judgment.winner_id == judgment.right_id:
            wins[judgment.right_id] += 1.0
        else:
            wins[judgment.left_id] += 0.5
            wins[judgment.right_id] += 0.5
    return {
        idea.idea_id: round(
            wins[idea.idea_id] / appearances[idea.idea_id]
            if appearances[idea.idea_id]
            else 1.0,
            4,
        )
        for idea in ideas
    }


def aggregate_factor_scores(
    ideas: list[IdeaCandidate],
    judgments: list[PairwiseJudgment],
) -> dict[str, dict[str, float]]:
    totals = {idea.idea_id: defaultdict(float) for idea in ideas}
    counts = defaultdict(int)
    for judgment in judgments:
        for idea_id, score_map in judgment.factor_scores.items():
            if idea_id not in totals:
                continue
            counts[idea_id] += 1
            for factor_name, value in score_map.items():
                totals[idea_id][factor_name] += value
    aggregated: dict[str, dict[str, float]] = {}
    for idea in ideas:
        idea_counts = counts[idea.idea_id]
        aggregated[idea.idea_id] = {
            factor_name: round(
                totals[idea.idea_id][factor_name] / idea_counts if idea_counts else 0.0,
                4,
            )
            for factor_name in FACTOR_NAMES
        }
    return aggregated


def build_evaluation_report(
    run_id: str,
    method_name: str,
    ideas: list[IdeaCandidate],
    judgments: list[PairwiseJudgment],
) -> EvaluationReport:
    pairwise_scores = aggregate_pairwise_scores(ideas, judgments)
    upstream_factors = aggregate_factor_scores(ideas, judgments)
    overall_preference_order = [
        idea_id
        for idea_id, _score in sorted(
            pairwise_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    top_idea = overall_preference_order[0] if overall_preference_order else "none"
    summary = (
        f"Evaluated {len(ideas)} ideas with {len(judgments)} pairwise judgments. "
        f"Top idea: {top_idea}."
    )
    return EvaluationReport(
        run_id=run_id,
        method_name=method_name,
        evaluated_idea_ids=[idea.idea_id for idea in ideas],
        pairwise_scores=pairwise_scores,
        upstream_factors=upstream_factors,
        overall_preference_order=overall_preference_order,
        pairwise_judgment_count=len(judgments),
        summary=summary,
    )
