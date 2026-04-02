from orchid_ng.domain import IdeaCandidate, PairwiseJudgment
from orchid_ng.services.ranking import aggregate_pairwise_scores


def test_pairwise_aggregation_is_order_invariant() -> None:
    first = IdeaCandidate(
        idea_id="idea_a",
        title="A",
        summary="A summary",
        hypothesis="A hypothesis",
        mechanism="A mechanism",
        resource_cost="low",
    )
    second = IdeaCandidate(
        idea_id="idea_b",
        title="B",
        summary="B summary",
        hypothesis="B hypothesis",
        mechanism="B mechanism",
        resource_cost="low",
    )
    judgments = [
        PairwiseJudgment(
            judge_role="final",
            rubric="test",
            left_id="idea_a",
            right_id="idea_b",
            winner_id="idea_a",
            preferred_side="left",
        ),
        PairwiseJudgment(
            judge_role="final",
            rubric="test",
            left_id="idea_b",
            right_id="idea_a",
            winner_id="idea_a",
            preferred_side="right",
        ),
    ]
    scores = aggregate_pairwise_scores([first, second], judgments)
    assert scores == {"idea_a": 1.0, "idea_b": 0.0}
