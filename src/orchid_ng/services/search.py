from __future__ import annotations

from itertools import zip_longest

from orchid_ng.domain import (
    CritiqueAction,
    CritiqueActionType,
    EvidenceNote,
    IdeaCandidate,
    ResearchTopic,
    make_id,
)
from orchid_ng.services.ideation import deduplicate_ideas
from orchid_ng.services.prompts import (
    PromptLibrary,
    format_actions,
    format_evidence,
    format_ideas,
    format_topic,
)

ACTION_RULES: list[tuple[CritiqueActionType, tuple[str, ...]]] = [
    (CritiqueActionType.MERGE_IDEAS, ("merge", "combine", "hybrid")),
    (CritiqueActionType.ADD_EVIDENCE, ("evidence", "ground", "citation", "support")),
    (CritiqueActionType.NARROW_CLAIM, ("narrow", "scope", "specific", "focused")),
    (
        CritiqueActionType.CLARIFY_ASSUMPTION,
        ("assumption", "precondition", "prerequisite", "explicit"),
    ),
    (
        CritiqueActionType.DROP_DEPENDENCY,
        ("drop", "remove", "simplify", "compute", "dependency", "resource"),
    ),
]


def parse_critique_actions(
    critique: str, target_idea_id: str | None
) -> list[CritiqueAction]:
    lower_critique = critique.lower()
    actions: list[CritiqueAction] = []
    for action_type, keywords in ACTION_RULES:
        if any(keyword in lower_critique for keyword in keywords):
            actions.append(
                CritiqueAction(
                    action_type=action_type,
                    target_idea_id=target_idea_id,
                    instruction=critique.strip(),
                    rationale=f"Matched critique keywords: {', '.join(keywords)}",
                )
            )
    if actions:
        return actions
    return [
        CritiqueAction(
            action_type=CritiqueActionType.CLARIFY_ASSUMPTION,
            target_idea_id=target_idea_id,
            instruction=critique.strip() or "Clarify the key hidden assumptions.",
            rationale="Fallback action when no explicit critique keywords were found.",
        )
    ]


class SearchRefiner:
    def __init__(
        self,
        model_client,
        prompt_library: PromptLibrary,
        search_judge,
        max_rounds: int = 1,
    ) -> None:
        self.model_client = model_client
        self.prompt_library = prompt_library
        self.search_judge = search_judge
        self.max_rounds = max_rounds

    def refine(
        self,
        topic: ResearchTopic,
        ideas: list[IdeaCandidate],
        background_evidence: list[EvidenceNote],
        run_store,
    ) -> list[IdeaCandidate]:
        current_ideas = deduplicate_ideas(ideas)
        for round_index in range(1, self.max_rounds + 1):
            if len(current_ideas) < 2:
                break
            next_generation: list[IdeaCandidate] = []
            round_judgments = []
            for left_idea, right_idea in pair_ideas(current_ideas):
                if right_idea is None:
                    next_generation.append(left_idea)
                    continue
                judgment = self.search_judge.compare(
                    left_idea,
                    right_idea,
                    rubric="Decide which idea deserves the next refinement budget.",
                )
                round_judgments.append(judgment)
                winner = (
                    left_idea if judgment.winner_id == left_idea.idea_id else right_idea
                )
                peer = right_idea if winner.idea_id == left_idea.idea_id else left_idea
                if judgment.winner_id is None:
                    winner = left_idea
                    peer = right_idea
                refined = self._refine_winner(
                    topic=topic,
                    winner=winner,
                    peer=peer,
                    background_evidence=background_evidence,
                    actions=judgment.next_actions,
                )
                next_generation.extend([winner, refined])
            current_ideas = deduplicate_ideas(next_generation)[: len(ideas)]
            run_store.write_search_judgments(round_index, round_judgments)
            run_store.write_search_round(round_index, current_ideas, round_judgments)
        return current_ideas

    def _refine_winner(
        self,
        topic: ResearchTopic,
        winner: IdeaCandidate,
        peer: IdeaCandidate,
        background_evidence: list[EvidenceNote],
        actions: list[CritiqueAction],
    ) -> IdeaCandidate:
        prompt = self.prompt_library.render(
            "refine_idea",
            topic_block=format_topic(topic),
            winner_block=format_ideas([winner]),
            peer_block=format_ideas([peer]),
            evidence_block=format_evidence(background_evidence),
            actions_block=format_actions(actions),
        )
        refined = self.model_client.generate(prompt, IdeaCandidate)
        supporting_evidence_ids = list(
            dict.fromkeys(
                [
                    *winner.supporting_evidence_ids,
                    *refined.supporting_evidence_ids,
                ]
            )
        )
        provenance = list(dict.fromkeys([*winner.provenance, "search_refine"]))
        return refined.model_copy(
            update={
                "idea_id": make_id("idea"),
                "method_name": winner.method_name,
                "parent_idea_id": winner.idea_id,
                "round_index": winner.round_index + 1,
                "supporting_evidence_ids": supporting_evidence_ids,
                "provenance": provenance,
            }
        )


def pair_ideas(ideas: list[IdeaCandidate]):
    iterator = iter(ideas)
    return zip_longest(iterator, iterator)
