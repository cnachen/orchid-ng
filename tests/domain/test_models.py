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


def test_idea_candidate_style_normalization_caps_counts() -> None:
    idea = IdeaCandidate(
        title="Cross-Document Style Drift Analysis via Local Embedding Entropy Calibration",
        summary=" ".join(["Detailed"] * 145),
        hypothesis="Entropy-calibrated drift analysis reduces false positives.",
        mechanism=" ".join(["Mechanism"] * 145),
        task_description={
            "summary": " ".join(["Task"] * 145),
            "keywords": ["a", "b", "c", "d", "e", "f", "g"],
            "research_area": ["nlp", "ml", "evaluation", "robustness"],
            "questions": ["Q1", "Q2", "Q3", "Q4", "Q5"],
            "research_objective": ["O1", "O2", "O3", "O4", "O5"],
            "contributions": ["C1", "C2", "C3", "C4", "C5", "C6"],
        },
        required_conditions=["A", "B", "C", "D"],
        open_risks=["R1", "R2", "R3", "R4"],
        supporting_evidence_ids=["e1", "e2", "e3", "e4"],
        resource_cost="moderate",
    )

    assert len(idea.task_description.keywords) == 6
    assert len(idea.task_description.research_area) == 3
    assert len(idea.task_description.questions) == 4
    assert len(idea.task_description.research_objective) == 4
    assert len(idea.task_description.contributions) == 5
    assert len(idea.required_conditions) == 3
    assert len(idea.open_risks) == 3
    assert len(idea.supporting_evidence_ids) == 3
