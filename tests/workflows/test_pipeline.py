from orchid_ng.integrations import CorpusStore, FakeModelClient
from orchid_ng.workflows.evaluate import run_evaluation
from orchid_ng.workflows.ideate import run_ideation


def test_ideate_evaluate_pipeline_writes_run_artifacts(
    topic,
    settings,
    corpus_path,
) -> None:
    client = FakeModelClient(
        [
            {
                "ideas": [
                    {
                        "title": "Constraint-aware retrieval planner",
                        "summary": "Retrieve assumptions and risks before proposing ideas.",
                        "hypothesis": "Explicit constraints improve feasibility.",
                        "mechanism": "Build evidence notes first and prompt ideation with them.",
                        "required_conditions": ["Literature snapshot available"],
                        "resource_cost": "moderate",
                        "open_risks": ["May reduce novelty if retrieval dominates"],
                    },
                    {
                        "title": "Critique-only ranking loop",
                        "summary": "Use pairwise critique to rank ideas without evidence grounding.",
                        "hypothesis": "Critique alone can repair weak ideas.",
                        "mechanism": "Generate many ideas and keep refining the winner.",
                        "required_conditions": ["Strong judge model"],
                        "resource_cost": "moderate",
                        "open_risks": ["May hallucinate fixes without evidence"],
                    },
                ]
            },
            {
                "preferred_side": "left",
                "critique": "Add stronger evidence and narrow the scope to a concrete retrieval policy.",
            },
            {
                "title": "Focused constraint-aware retrieval planner",
                "summary": "Retrieve assumptions, risks, and applicability notes before generating narrow improvement ideas.",
                "hypothesis": "Grounding the search with explicit constraints improves survivability.",
                "mechanism": "Use background evidence plus critique-guided refinement to tighten the claim.",
                "required_conditions": [
                    "Frozen literature snapshot",
                    "Pairwise judge with critique",
                ],
                "resource_cost": "moderate",
                "open_risks": ["Could become too conservative"],
            },
            {
                "preferred_side": "right",
                "reasoning": "The refined idea is better grounded and keeps the scope realistic.",
                "left_scores": {
                    "novelty": 3.4,
                    "soundness": 3.8,
                    "feasibility": 4.0,
                    "clarity": 3.9,
                    "grounding": 4.1,
                },
                "right_scores": {
                    "novelty": 3.5,
                    "soundness": 4.3,
                    "feasibility": 4.4,
                    "clarity": 4.2,
                    "grounding": 4.5,
                },
            },
        ]
    )
    manifest = run_ideation(
        topic=topic,
        settings=settings,
        run_id="test-run",
        model_client=client,
        search_model_client=client,
        corpus_store=CorpusStore.from_path(corpus_path),
    )
    assert manifest.status == "ideated"

    report = run_evaluation(
        run_id="test-run",
        settings=settings,
        judge_model_client=client,
    )

    run_dir = settings.runs_dir / "test-run"
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "topic.json").exists()
    assert (run_dir / "evidence" / "background.json").exists()
    assert len(list((run_dir / "evidence").glob("idea_*.json"))) >= 2
    assert len(list((run_dir / "ideas").glob("seed_*.json"))) == 2
    assert (run_dir / "search" / "round_001.json").exists()
    assert (run_dir / "judgments" / "search_001.jsonl").exists()
    assert (run_dir / "judgments" / "final_pairwise.jsonl").exists()
    assert (run_dir / "reports" / "summary.json").exists()
    assert report.pairwise_judgment_count == 1
    assert report.overall_preference_order[0] in report.evaluated_idea_ids
