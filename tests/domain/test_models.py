from orchid_ng.domain import IdeaCandidate, ResearchTopic


def test_research_topic_round_trip(topic: ResearchTopic) -> None:
    payload = topic.model_dump_json()
    restored = ResearchTopic.model_validate_json(payload)
    assert restored == topic


def test_idea_candidate_defaults() -> None:
    idea = IdeaCandidate(
        title="Evidence-grounded retrieval loop",
        summary="Use literature-derived constraints before idea generation.",
        hypothesis="Grounded constraints reduce fragile ideas.",
        mechanism="Retrieve risks and assumptions first, then ideate.",
        resource_cost="moderate",
    )
    assert idea.idea_id.startswith("idea_")
    assert idea.required_conditions == []
    assert idea.open_risks == []
    assert idea.supporting_evidence_ids == []
