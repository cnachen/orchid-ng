from __future__ import annotations

from orchid_ng.config import Settings
from orchid_ng.domain import ResearchTopic, RunManifest
from orchid_ng.integrations import CorpusStore, LiteLLMModelClient, ModelClient
from orchid_ng.services.evidence import EvidenceBuilder
from orchid_ng.services.ideation import build_idea_method
from orchid_ng.services.judging import SearchJudge
from orchid_ng.services.prompts import PromptLibrary
from orchid_ng.services.search import SearchRefiner
from orchid_ng.storage import RunStore


def run_ideation(
    topic: ResearchTopic,
    settings: Settings,
    method_name: str = "orchid",
    run_id: str | None = None,
    model_client: ModelClient | None = None,
    search_model_client: ModelClient | None = None,
    corpus_store: CorpusStore | None = None,
) -> RunManifest:
    settings.ensure_directories()
    store = RunStore(settings.runs_dir)
    run_session = store.create_run(
        topic=topic,
        method_name=method_name,
        model_name=settings.model_name,
        prompt_dir=settings.prompt_dir,
        corpus_path=settings.corpus_path,
        run_id=run_id,
    )
    prompt_library = PromptLibrary(settings.prompt_dir)
    corpus = corpus_store or (
        CorpusStore.from_path(settings.corpus_path)
        if settings.corpus_path
        else CorpusStore.empty()
    )
    generation_model = model_client or LiteLLMModelClient(settings.model_name)
    search_model = search_model_client or generation_model
    evidence_builder = EvidenceBuilder(corpus, top_k=settings.background_evidence_limit)
    search_judge = SearchJudge(search_model, prompt_library)
    search_refiner = SearchRefiner(
        model_client=generation_model,
        prompt_library=prompt_library,
        search_judge=search_judge,
        evidence_builder=evidence_builder,
        max_rounds=settings.search_rounds,
    )
    method = build_idea_method(
        method_name,
        model_client=generation_model,
        prompt_library=prompt_library,
        evidence_builder=evidence_builder,
        search_refiner=search_refiner,
    )
    method.run(topic=topic, budget=topic.budget_tokens, run_store=run_session)
    run_session.update_status("ideated")
    return run_session.manifest
