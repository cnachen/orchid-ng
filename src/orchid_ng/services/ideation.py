from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from orchid_ng.domain import IdeaCandidate, ResearchTopic, make_id
from orchid_ng.services.evidence import EvidenceBuilder
from orchid_ng.services.prompts import PromptLibrary, format_evidence, format_topic


class IdeaBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ideas: list[IdeaCandidate] = Field(default_factory=list)


class IdeaMethod:
    name = "base"

    def run(self, topic: ResearchTopic, budget: int, run_store) -> list[IdeaCandidate]:
        raise NotImplementedError


class BaseIdeaMethod(IdeaMethod):
    def __init__(
        self,
        model_client,
        prompt_library: PromptLibrary,
        evidence_builder: EvidenceBuilder,
        search_refiner=None,
    ) -> None:
        self.model_client = model_client
        self.prompt_library = prompt_library
        self.evidence_builder = evidence_builder
        self.search_refiner = search_refiner

    def _generate_seed_ideas(
        self,
        topic: ResearchTopic,
        background_notes,
        budget: int,
    ) -> list[IdeaCandidate]:
        prompt = self.prompt_library.render(
            "seed_ideas",
            topic_block=format_topic(topic),
            background_block=format_evidence(background_notes),
            idea_count=str(topic.desired_idea_count),
            budget=str(budget),
            method_name=self.name,
        )
        response = self.model_client.generate(prompt, IdeaBatch)
        seeds: list[IdeaCandidate] = []
        for idea in response.ideas:
            seeds.append(
                idea.model_copy(
                    update={
                        "idea_id": make_id("idea"),
                        "method_name": self.name,
                        "round_index": 0,
                        "provenance": ["seed_generation"],
                    }
                )
            )
        return deduplicate_ideas(seeds)[: topic.desired_idea_count]

    def _attach_idea_evidence(
        self, ideas: list[IdeaCandidate], run_store
    ) -> list[IdeaCandidate]:
        enriched: list[IdeaCandidate] = []
        for idea in ideas:
            notes = self.evidence_builder.build_for_idea(idea)
            run_store.write_idea_evidence(idea.idea_id, notes)
            evidence_ids = notes_to_ids(notes)
            enriched.append(
                idea.model_copy(
                    update={
                        "supporting_evidence_ids": idea.supporting_evidence_ids
                        or evidence_ids,
                    }
                )
            )
        return enriched


class RawBackboneMethod(BaseIdeaMethod):
    name = "raw_backbone"

    def run(self, topic: ResearchTopic, budget: int, run_store) -> list[IdeaCandidate]:
        run_store.write_background_evidence([])
        ideas = self._generate_seed_ideas(topic, background_notes=[], budget=budget)
        run_store.write_seed_ideas(ideas)
        return ideas


class RetrievalOnlyMethod(BaseIdeaMethod):
    name = "retrieval_only"

    def run(self, topic: ResearchTopic, budget: int, run_store) -> list[IdeaCandidate]:
        background = self.evidence_builder.build_background(topic)
        run_store.write_background_evidence(background)
        ideas = self._generate_seed_ideas(
            topic, background_notes=background, budget=budget
        )
        ideas = self._attach_idea_evidence(ideas, run_store)
        run_store.write_seed_ideas(ideas)
        return ideas


class OrchidMethod(BaseIdeaMethod):
    name = "orchid"

    def run(self, topic: ResearchTopic, budget: int, run_store) -> list[IdeaCandidate]:
        background = self.evidence_builder.build_background(topic)
        run_store.write_background_evidence(background)
        ideas = self._generate_seed_ideas(
            topic, background_notes=background, budget=budget
        )
        ideas = self._attach_idea_evidence(ideas, run_store)
        run_store.write_seed_ideas(ideas)
        if self.search_refiner is None:
            return ideas
        refined = self.search_refiner.refine(
            topic=topic,
            ideas=ideas,
            background_evidence=background,
            run_store=run_store,
        )
        return refined


def build_idea_method(name: str, **dependencies) -> IdeaMethod:
    registry: dict[str, Callable[..., IdeaMethod]] = {
        "raw_backbone": RawBackboneMethod,
        "retrieval_only": RetrievalOnlyMethod,
        "orchid": OrchidMethod,
    }
    if name not in registry:
        available = ", ".join(sorted(registry))
        raise ValueError(f"Unknown idea method: {name}. Available methods: {available}")
    return registry[name](**dependencies)


def deduplicate_ideas(ideas: list[IdeaCandidate]) -> list[IdeaCandidate]:
    seen: set[str] = set()
    unique_ideas: list[IdeaCandidate] = []
    for idea in ideas:
        fingerprint = (
            " ".join([idea.title, idea.summary, idea.hypothesis]).strip().lower()
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique_ideas.append(idea)
    return unique_ideas


def notes_to_ids(notes) -> list[str]:
    return [note.note_id for note in notes]
