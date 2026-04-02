from orchid_ng.domain import (
    IdeaCandidate,
    MethodDescription,
    MethodModule,
    ResearchTopic,
    TaskDescription,
    make_id,
)
from orchid_ng.services.alignment import (
    alignment_gaps,
    score_idea_alignment,
    select_idea_portfolio,
)


def test_alignment_score_prefers_richer_ideas() -> None:
    sparse = IdeaCandidate(
        title="Sparse",
        summary="Short idea.",
        hypothesis="Short hypothesis.",
        mechanism="Short mechanism.",
        resource_cost="low",
    )
    rich = IdeaCandidate(
        title="Rich Idea",
        task_description=TaskDescription(
            summary=" ".join(["Detailed"] * 140),
            keywords=[
                "retrieval",
                "calibration",
                "benchmark",
                "nlp",
                "detection",
                "risk",
            ],
            research_area=[
                "Natural Language Processing",
                "Machine Learning",
                "Evaluation",
            ],
            questions=["Q1", "Q2", "Q3", "Q4"],
            research_objective=["O1", "O2", "O3", "O4"],
            contributions=["C1", "C2", "C3", "C4", "C5"],
        ),
        method=MethodDescription(
            summary=" ".join(["Method"] * 148),
            Modules=[MethodModule(name=f"M{i}", description="desc") for i in range(5)],
            framework=" ".join(["Framework"] * 130),
        ),
        required_conditions=["A", "B", "C"],
        open_risks=["R1", "R2", "R3"],
        supporting_evidence_ids=["e1", "e2", "e3"],
        resource_cost="moderate",
    )

    assert score_idea_alignment(rich) > score_idea_alignment(sparse)
    assert alignment_gaps(sparse)
    assert not alignment_gaps(rich)


def test_select_idea_portfolio_avoids_near_duplicates() -> None:
    topic = ResearchTopic(
        title="AI text detection",
        question="How can retrieval improve false-positive robustness?",
    )
    duplicate_a = IdeaCandidate(
        title="Retrieval-Calibrated Thresholding for AI Detection",
        task_description=TaskDescription(
            summary=" ".join(["Detailed"] * 140),
            questions=["Q1", "Q2", "Q3", "Q4"],
            research_objective=["O1", "O2", "O3", "O4"],
            contributions=["C1", "C2", "C3", "C4"],
        ),
        method=MethodDescription(
            summary=" ".join(["Method"] * 148),
            Modules=[MethodModule(name=f"M{i}", description="desc") for i in range(5)],
            framework=" ".join(["Framework"] * 130),
        ),
        supporting_evidence_ids=["e1", "e2", "e3"],
    )
    duplicate_b = duplicate_a.model_copy(
        update={
            "title": "Retrieval-Calibrated Thresholding for AI Detection",
            "summary": duplicate_a.summary + " Extra wording.",
        }
    )
    distinct = duplicate_a.model_copy(
        update={
            "title": "Contrastive Segment Consistency Auditing for AI Detection",
            "hypothesis": "Segment-level consistency signals can catch paraphrased AI text.",
            "method": MethodDescription(
                summary=" ".join(["Auditing"] * 148),
                Modules=[
                    MethodModule(name="Segment Encoder", description="desc"),
                    MethodModule(name="Anchor Retriever", description="desc"),
                    MethodModule(name="Consistency Graph", description="desc"),
                    MethodModule(name="Variance Scorer", description="desc"),
                    MethodModule(name="Decision Layer", description="desc"),
                ],
                framework=" ".join(["Auditing"] * 130),
            ),
        }
    )

    selected = select_idea_portfolio(
        [duplicate_a, duplicate_b, distinct],
        topic=topic,
        target_size=2,
    )

    titles = {idea.title for idea in selected}
    assert len(selected) == 2
    assert "Contrastive Segment Consistency Auditing for AI Detection" in titles


def test_select_idea_portfolio_backfills_to_target_size() -> None:
    topic = ResearchTopic(
        title="AI text detection",
        question="How can retrieval improve false-positive robustness?",
    )
    base = IdeaCandidate(
        title="Retrieval-Calibrated Thresholding for AI Detection",
        task_description=TaskDescription(
            summary=" ".join(["Detailed"] * 140),
            keywords=[
                "retrieval",
                "calibration",
                "benchmark",
                "nlp",
                "detection",
                "risk",
            ],
            research_area=[
                "Natural Language Processing",
                "Machine Learning",
                "Evaluation",
            ],
            questions=["Q1", "Q2", "Q3", "Q4"],
            research_objective=["O1", "O2", "O3", "O4"],
            contributions=["C1", "C2", "C3", "C4", "C5"],
        ),
        method=MethodDescription(
            summary=" ".join(["Method"] * 148),
            Modules=[MethodModule(name=f"M{i}", description="desc") for i in range(5)],
            framework=" ".join(["Framework"] * 130),
        ),
        required_conditions=["A", "B", "C"],
        open_risks=["R1", "R2", "R3"],
        supporting_evidence_ids=["e1", "e2", "e3"],
        resource_cost="moderate",
    )
    similar_a = base.model_copy(
        update={
            "idea_id": make_id("idea"),
            "title": "Segment Drift Calibration for AI Detection",
        }
    )
    similar_b = base.model_copy(
        update={
            "idea_id": make_id("idea"),
            "title": "Human-Style Provenance Mapping for AI Detection",
        }
    )
    similar_c = base.model_copy(
        update={
            "idea_id": make_id("idea"),
            "title": "Latent Error Auditing for AI Detection",
        }
    )

    selected = select_idea_portfolio(
        [base, similar_a, similar_b, similar_c],
        topic=topic,
        target_size=4,
    )

    assert len(selected) == 4
