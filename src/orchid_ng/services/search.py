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
from orchid_ng.services.alignment import alignment_gaps, select_idea_portfolio
from orchid_ng.services.ideation import deduplicate_ideas, notes_to_ids
from orchid_ng.services.prompts import (
    PromptLibrary,
    format_actions,
    format_alignment_gaps,
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
        evidence_builder=None,
        max_rounds: int = 1,
    ) -> None:
        self.model_client = model_client
        self.prompt_library = prompt_library
        self.search_judge = search_judge
        self.evidence_builder = evidence_builder
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
                    run_store=run_store,
                )
                next_generation.extend([winner, refined])
            current_ideas = select_idea_portfolio(
                deduplicate_ideas(next_generation), topic, len(ideas)
            )
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
        run_store,
    ) -> IdeaCandidate:
        idea_evidence = _merge_evidence_notes(
            background_evidence,
            run_store.load_idea_evidence(winner.idea_id),
            run_store.load_idea_evidence(peer.idea_id),
        )
        prompt = self.prompt_library.render(
            "refine_idea",
            topic_block=format_topic(topic),
            winner_block=format_ideas([winner]),
            peer_block=format_ideas([peer]),
            evidence_block=format_evidence(idea_evidence),
            gap_block=format_alignment_gaps(
                list(dict.fromkeys([*alignment_gaps(winner), *alignment_gaps(peer)]))
            ),
            actions_block=format_actions(actions),
        )
        refined = self.model_client.generate(prompt, IdeaCandidate)
        provenance = list(dict.fromkeys([*winner.provenance, "search_refine"]))
        candidate = refined.model_copy(
            update={
                "idea_id": make_id("idea"),
                "method_name": winner.method_name,
                "parent_idea_id": winner.idea_id,
                "round_index": winner.round_index + 1,
                "provenance": provenance,
            }
        )
        if self.evidence_builder is None:
            supporting_evidence_ids = list(
                dict.fromkeys(
                    [
                        *winner.supporting_evidence_ids,
                        *candidate.supporting_evidence_ids,
                    ]
                )
            )
            return candidate.model_copy(
                update={"supporting_evidence_ids": supporting_evidence_ids[:3]}
            )
        refined_notes = self.evidence_builder.build_for_idea(candidate)
        run_store.write_idea_evidence(candidate.idea_id, refined_notes)
        supporting_evidence_ids = list(
            dict.fromkeys(
                [*winner.supporting_evidence_ids, *notes_to_ids(refined_notes)]
            )
        )
        return candidate.model_copy(
            update={"supporting_evidence_ids": supporting_evidence_ids[:3]}
        )


def pair_ideas(ideas: list[IdeaCandidate]):
    iterator = iter(ideas)
    return zip_longest(iterator, iterator)


def _merge_evidence_notes(*note_groups: list[EvidenceNote]) -> list[EvidenceNote]:
    merged: list[EvidenceNote] = []
    seen_note_ids: set[str] = set()
    for note_group in note_groups:
        for note in note_group:
            if note.note_id in seen_note_ids:
                continue
            seen_note_ids.add(note.note_id)
            merged.append(note)
    return merged
