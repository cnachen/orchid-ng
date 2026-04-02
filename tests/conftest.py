from __future__ import annotations

from pathlib import Path

import pytest

from orchid_ng.config import Settings
from orchid_ng.domain import ResearchTopic

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = REPO_ROOT / "src" / "orchid_ng" / "prompts"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def corpus_path() -> Path:
    return FIXTURES_DIR / "corpus.jsonl"


@pytest.fixture
def topic() -> ResearchTopic:
    return ResearchTopic(
        title="Grounded Open-Ended Ideation",
        question="How can retrieval improve feasible science ideas without collapsing novelty?",
        description="Research prototype for science ideation.",
        constraints=[
            "Use a frozen literature snapshot",
            "Stay within moderate compute",
        ],
        tags=["science", "retrieval", "evaluation"],
        desired_idea_count=2,
        budget_tokens=8_000,
    )


@pytest.fixture
def settings(tmp_path: Path, corpus_path: Path) -> Settings:
    return Settings(
        project_root=tmp_path,
        prompt_dir=PROMPT_DIR,
        corpus_path=corpus_path,
        model_name="fake-model",
        search_model_name="fake-model",
        judge_model_name="fake-model",
        search_rounds=1,
    )
