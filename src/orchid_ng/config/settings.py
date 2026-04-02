from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT_DIR = PACKAGE_ROOT / "prompts"


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_root: Path = Field(default_factory=Path.cwd)
    runs_dir: Path | None = None
    prompt_dir: Path = DEFAULT_PROMPT_DIR
    corpus_path: Path | None = None
    model_name: str = "gpt-4.1-mini"
    search_model_name: str | None = None
    judge_model_name: str | None = None
    background_evidence_limit: int = 5
    search_rounds: int = 1
    random_seed: int = 7

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        self.project_root = self.project_root.resolve()
        self.runs_dir = (self.runs_dir or self.project_root / "runs").resolve()
        self.prompt_dir = self.prompt_dir.resolve()
        if self.corpus_path is not None:
            self.corpus_path = self.corpus_path.resolve()
        if self.search_model_name is None:
            self.search_model_name = self.model_name
        if self.judge_model_name is None:
            self.judge_model_name = self.model_name
        return self

    def ensure_directories(self) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
