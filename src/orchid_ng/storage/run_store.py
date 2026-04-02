from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from orchid_ng.domain import (
    EvaluationReport,
    EvidenceNote,
    IdeaCandidate,
    PairwiseJudgment,
    ResearchTopic,
    RunManifest,
)


class RunStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        topic: ResearchTopic,
        method_name: str,
        model_name: str,
        prompt_dir: Path,
        corpus_path: Path | None = None,
        run_id: str | None = None,
    ) -> "RunSession":
        actual_run_id = run_id or build_run_id(topic.title)
        manifest = RunManifest(
            run_id=actual_run_id,
            topic_id=topic.topic_id,
            method_name=method_name,
            model_name=model_name,
            corpus_path=str(corpus_path) if corpus_path else None,
            prompt_dir=str(prompt_dir),
        )
        session = RunSession(self.root_dir / actual_run_id, manifest)
        session.initialize(topic)
        return session

    def open_run(self, run_id: str) -> "RunSession":
        run_dir = self.root_dir / run_id
        manifest = RunManifest.model_validate_json(
            (run_dir / "manifest.json").read_text()
        )
        return RunSession(run_dir=run_dir, manifest=manifest)


class RunSession:
    def __init__(self, run_dir: Path, manifest: RunManifest) -> None:
        self.run_dir = run_dir
        self.manifest = manifest

    def initialize(self, topic: ResearchTopic) -> None:
        self._ensure_structure()
        self.write_manifest()
        self.write_topic(topic)
        self.write_background_evidence([])

    def update_status(self, status: str) -> None:
        self.manifest = self.manifest.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(UTC),
            }
        )
        self.write_manifest()

    def write_manifest(self) -> None:
        _write_json(self.run_dir / "manifest.json", self.manifest)

    def write_topic(self, topic: ResearchTopic) -> None:
        _write_json(self.run_dir / "topic.json", topic)

    def write_background_evidence(self, notes: list[EvidenceNote]) -> None:
        _write_json(self.run_dir / "evidence" / "background.json", notes)

    def write_idea_evidence(self, idea_id: str, notes: list[EvidenceNote]) -> None:
        _write_json(self.run_dir / "evidence" / f"idea_{idea_id}.json", notes)

    def write_seed_ideas(self, ideas: list[IdeaCandidate]) -> None:
        ideas_dir = self.run_dir / "ideas"
        for path in ideas_dir.glob("seed_*.json"):
            path.unlink()
        for idea in ideas:
            _write_json(ideas_dir / f"seed_{idea.idea_id}.json", idea)

    def write_search_judgments(
        self,
        round_index: int,
        judgments: list[PairwiseJudgment],
    ) -> None:
        _write_jsonl(
            self.run_dir / "judgments" / f"search_{round_index:03d}.jsonl", judgments
        )

    def write_search_round(
        self,
        round_index: int,
        resulting_ideas: list[IdeaCandidate],
        judgments: list[PairwiseJudgment],
    ) -> None:
        payload = {
            "round_index": round_index,
            "resulting_ideas": [_to_jsonable(idea) for idea in resulting_ideas],
            "judgments": [_to_jsonable(judgment) for judgment in judgments],
        }
        _write_plain_json(
            self.run_dir / "search" / f"round_{round_index:03d}.json", payload
        )

    def write_final_judgments(self, judgments: list[PairwiseJudgment]) -> None:
        _write_jsonl(self.run_dir / "judgments" / "final_pairwise.jsonl", judgments)

    def write_report(self, report: EvaluationReport) -> None:
        _write_json(self.run_dir / "reports" / "summary.json", report)

    def load_topic(self) -> ResearchTopic:
        return ResearchTopic.model_validate_json(
            (self.run_dir / "topic.json").read_text()
        )

    def load_seed_ideas(self) -> list[IdeaCandidate]:
        return [
            IdeaCandidate.model_validate_json(path.read_text())
            for path in sorted((self.run_dir / "ideas").glob("seed_*.json"))
        ]

    def load_latest_ideas(self) -> list[IdeaCandidate]:
        round_files = sorted((self.run_dir / "search").glob("round_*.json"))
        if not round_files:
            return self.load_seed_ideas()
        payload = json.loads(round_files[-1].read_text())
        return [
            IdeaCandidate.model_validate(item) for item in payload["resulting_ideas"]
        ]

    def load_report(self) -> EvaluationReport:
        return EvaluationReport.model_validate_json(
            (self.run_dir / "reports" / "summary.json").read_text()
        )

    def _ensure_structure(self) -> None:
        for relative in ("evidence", "ideas", "search", "judgments", "reports"):
            (self.run_dir / relative).mkdir(parents=True, exist_ok=True)


def build_run_id(topic_title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic_title.lower()).strip("-") or "run"
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{slug}-{timestamp}"


def _write_json(path: Path, payload: Any) -> None:
    _write_plain_json(path, _to_jsonable(payload))


def _write_plain_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(_to_jsonable(row), ensure_ascii=False) + "\n" for row in rows
        ),
        encoding="utf-8",
    )


def _to_jsonable(payload: Any) -> Any:
    if isinstance(payload, list):
        return [_to_jsonable(item) for item in payload]
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return payload
