from __future__ import annotations

from itertools import combinations

from orchid_ng.config import Settings
from orchid_ng.domain import EvaluationReport, IdeaCandidate
from orchid_ng.integrations import LiteLLMModelClient, ModelClient
from orchid_ng.services.judging import FinalJudge
from orchid_ng.services.prompts import PromptLibrary
from orchid_ng.services.ranking import build_evaluation_report
from orchid_ng.storage import RunStore


def run_evaluation(
    run_id: str,
    settings: Settings,
    judge_model_client: ModelClient | None = None,
) -> EvaluationReport:
    settings.ensure_directories()
    store = RunStore(settings.runs_dir)
    run_session = store.open_run(run_id)
    ideas = run_session.load_latest_ideas()
    prompt_library = PromptLibrary(settings.prompt_dir)
    model_client = judge_model_client or LiteLLMModelClient(settings.judge_model_name)
    final_judge = FinalJudge(model_client, prompt_library)
    judgments = [
        final_judge.compare(
            left, right, rubric="Which idea deserves next-step validation budget?"
        )
        for left, right in _blind_pairs(ideas)
    ]
    run_session.write_final_judgments(judgments)
    report = build_evaluation_report(
        run_id=run_session.manifest.run_id,
        method_name=run_session.manifest.method_name,
        ideas=ideas,
        judgments=judgments,
    )
    run_session.write_report(report)
    run_session.update_status("evaluated")
    return report


def _blind_pairs(ideas: list[IdeaCandidate]):
    for index, (first, second) in enumerate(combinations(ideas, 2), start=1):
        yield (second, first) if index % 2 == 0 else (first, second)
