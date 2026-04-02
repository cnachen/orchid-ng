from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

from build_pdf_corpus import build_record
from orchid_ng.config import Settings
from orchid_ng.domain import ResearchTopic
from orchid_ng.services.alignment import (
    build_alignment_report,
    portfolio_diversity_metrics,
)
from orchid_ng.storage import RunStore
from orchid_ng.workflows.evaluate import run_evaluation
from orchid_ng.workflows.ideate import run_ideation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an automated ideation -> analysis loop against the fixed Orchid style contract."
    )
    parser.add_argument("--papers-dir", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--title", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--model", required=True)
    parser.add_argument("--desired-idea-count", type=int, default=4)
    parser.add_argument("--budget-tokens", type=int, default=20_000)
    parser.add_argument("--search-rounds", type=int, default=2)
    parser.add_argument("--background-evidence-limit", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--max-candidates-per-iteration", type=int, default=3)
    return parser.parse_args()


@dataclass(frozen=True)
class OptimizationConfig:
    search_rounds: int
    background_evidence_limit: int
    desired_idea_count: int

    def key(self) -> tuple[int, int, int]:
        return (
            self.search_rounds,
            self.background_evidence_limit,
            self.desired_idea_count,
        )

    @classmethod
    def model_validate(cls, payload: dict[str, object]) -> "OptimizationConfig":
        return cls(
            search_rounds=int(payload["search_rounds"]),
            background_evidence_limit=int(payload["background_evidence_limit"]),
            desired_idea_count=int(payload["desired_idea_count"]),
        )


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    corpus_path = project_root / "build" / "papers_corpus.jsonl"
    build_corpus(args.papers_dir, corpus_path, max_pages=args.max_pages)

    topic = ResearchTopic(
        title=args.title,
        question=args.question,
        description=args.description,
        constraints=args.constraint,
        tags=args.tag,
        desired_idea_count=args.desired_idea_count,
        budget_tokens=args.budget_tokens,
    )

    current_candidates = initial_candidates(
        desired_idea_count=args.desired_idea_count,
        search_rounds=args.search_rounds,
        background_evidence_limit=args.background_evidence_limit,
    )
    seen_keys: set[tuple[int, int, int]] = set()
    iteration_reports: list[dict[str, object]] = []
    all_run_reports: list[dict[str, object]] = []
    best_report: dict[str, object] | None = None

    for iteration_index in range(1, args.iterations + 1):
        batch = [
            config for config in current_candidates if config.key() not in seen_keys
        ][: args.max_candidates_per_iteration]
        if not batch:
            break

        batch_reports: list[dict[str, object]] = []
        for config in batch:
            seen_keys.add(config.key())
            candidate_topic = topic.model_copy(
                update={"desired_idea_count": config.desired_idea_count}
            )
            settings = Settings(
                project_root=project_root,
                corpus_path=corpus_path,
                model_name=args.model,
                judge_model_name=args.model,
                search_rounds=config.search_rounds,
                background_evidence_limit=config.background_evidence_limit,
            )
            manifest = run_ideation(
                topic=candidate_topic,
                settings=settings,
                method_name="orchid",
                run_id=None,
            )
            evaluation_report = run_evaluation(
                run_id=manifest.run_id, settings=settings
            )
            run_store = RunStore(settings.runs_dir)
            run_session = run_store.open_run(manifest.run_id)
            ideas = run_session.load_latest_ideas()
            alignment_report = build_alignment_report(
                run_id=manifest.run_id,
                ideas=ideas,
            )
            alignment_path = (
                settings.runs_dir / manifest.run_id / "reports" / "style_alignment.json"
            )
            alignment_path.write_text(
                json.dumps(alignment_report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            run_report = build_run_report(
                config=config,
                manifest_run_id=manifest.run_id,
                ideas=ideas,
                alignment_report=alignment_report,
                evaluation_report=evaluation_report,
            )
            batch_reports.append(run_report)
            all_run_reports.append(run_report)
            if (
                best_report is None
                or run_report["objective_score"] > best_report["objective_score"]
            ):
                best_report = run_report
            write_summary(
                project_root=project_root,
                corpus_path=corpus_path,
                iteration_reports=iteration_reports,
                all_run_reports=all_run_reports,
                best_report=best_report,
            )

        iteration_reports.append(
            {
                "iteration": iteration_index,
                "candidate_configs": [asdict(config) for config in batch],
                "run_reports": batch_reports,
                "best_run_id": max(
                    batch_reports, key=lambda item: item["objective_score"]
                )["run_id"],
            }
        )
        write_summary(
            project_root=project_root,
            corpus_path=corpus_path,
            iteration_reports=iteration_reports,
            all_run_reports=all_run_reports,
            best_report=best_report,
        )
        current_candidates = propose_next_candidates(
            best_config=OptimizationConfig.model_validate(best_report["config"]),
            best_report=best_report,
        )

    summary = write_summary(
        project_root=project_root,
        corpus_path=corpus_path,
        iteration_reports=iteration_reports,
        all_run_reports=all_run_reports,
        best_report=best_report,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def initial_candidates(
    desired_idea_count: int,
    search_rounds: int,
    background_evidence_limit: int,
) -> list[OptimizationConfig]:
    candidates = [
        OptimizationConfig(
            search_rounds=search_rounds,
            background_evidence_limit=background_evidence_limit,
            desired_idea_count=desired_idea_count,
        ),
        OptimizationConfig(
            search_rounds=min(search_rounds + 1, 3),
            background_evidence_limit=background_evidence_limit,
            desired_idea_count=desired_idea_count,
        ),
        OptimizationConfig(
            search_rounds=search_rounds,
            background_evidence_limit=min(background_evidence_limit + 1, 8),
            desired_idea_count=desired_idea_count,
        ),
        OptimizationConfig(
            search_rounds=search_rounds,
            background_evidence_limit=background_evidence_limit,
            desired_idea_count=min(desired_idea_count + 1, 5),
        ),
    ]
    return sorted(set(candidates), key=lambda item: item.key())


def build_run_report(
    config: OptimizationConfig,
    manifest_run_id: str,
    ideas,
    alignment_report: dict[str, object],
    evaluation_report,
) -> dict[str, object]:
    top_idea_id = evaluation_report.overall_preference_order[0]
    top_factors = evaluation_report.upstream_factors.get(top_idea_id, {})
    factor_average = round(mean(top_factors.values()), 4) if top_factors else 0.0
    pairwise_score = evaluation_report.pairwise_scores.get(top_idea_id, 0.0)
    diversity = portfolio_diversity_metrics(ideas)
    alignment_score = float(alignment_report["overall_alignment_score"])
    count_fidelity = 1.0 - abs(len(ideas) - config.desired_idea_count) / max(
        config.desired_idea_count,
        1,
    )
    objective_score = round(
        0.6 * alignment_score
        + 0.2 * factor_average * 10
        + 0.1 * pairwise_score * 100
        + 0.05 * diversity["title_diversity_score"] * 100
        + 0.05 * count_fidelity * 100,
        2,
    )
    top_idea_title = next(
        (idea.title for idea in ideas if idea.idea_id == top_idea_id),
        top_idea_id,
    )
    gap_counts = summarize_gap_counts(alignment_report)
    return {
        "run_id": manifest_run_id,
        "config": asdict(config),
        "overall_alignment_score": alignment_score,
        "objective_score": objective_score,
        "top_idea_id": top_idea_id,
        "top_idea_title": top_idea_title,
        "top_idea_pairwise_score": round(pairwise_score, 4),
        "top_idea_factor_average": factor_average,
        "portfolio_metrics": diversity,
        "count_fidelity": round(count_fidelity, 4),
        "gap_counts": gap_counts,
    }


def write_summary(
    project_root: Path,
    corpus_path: Path,
    iteration_reports: list[dict[str, object]],
    all_run_reports: list[dict[str, object]],
    best_report: dict[str, object] | None,
) -> dict[str, object]:
    summary = {
        "corpus_path": str(corpus_path),
        "iterations": iteration_reports,
        "loop_reports": all_run_reports,
        "best_run": best_report,
    }
    output_path = project_root / "build" / "optimization_report.json"
    output_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def summarize_gap_counts(alignment_report: dict[str, object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for idea_report in alignment_report.get("idea_reports", []):
        for gap in idea_report.get("gaps", []):
            counts[gap] = counts.get(gap, 0) + 1
    return counts


def propose_next_candidates(
    best_config: OptimizationConfig,
    best_report: dict[str, object],
) -> list[OptimizationConfig]:
    candidates = {
        OptimizationConfig(
            search_rounds=best_config.search_rounds,
            background_evidence_limit=best_config.background_evidence_limit,
            desired_idea_count=best_config.desired_idea_count,
        )
    }
    gap_counts = best_report.get("gap_counts", {})

    search_rounds = best_config.search_rounds
    if gap_counts.get("framework description lacks pipeline detail", 0):
        search_rounds = min(search_rounds + 1, 3)

    background_evidence_limit = best_config.background_evidence_limit
    if gap_counts.get("evidence grounding is too weak", 0):
        background_evidence_limit = min(background_evidence_limit + 2, 8)

    desired_idea_count = best_config.desired_idea_count
    if gap_counts:
        desired_idea_count = min(desired_idea_count + 1, 5)

    candidates.update(
        {
            OptimizationConfig(
                search_rounds=search_rounds,
                background_evidence_limit=background_evidence_limit,
                desired_idea_count=desired_idea_count,
            ),
            OptimizationConfig(
                search_rounds=min(search_rounds + 1, 3),
                background_evidence_limit=background_evidence_limit,
                desired_idea_count=desired_idea_count,
            ),
            OptimizationConfig(
                search_rounds=max(search_rounds - 1, 1),
                background_evidence_limit=min(background_evidence_limit + 1, 8),
                desired_idea_count=desired_idea_count,
            ),
        }
    )
    return sorted(candidates, key=lambda item: item.key())


def build_corpus(papers_dir: Path, output_path: Path, max_pages: int) -> None:
    pdf_paths = sorted(papers_dir.glob("*.pdf"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for pdf_path in pdf_paths:
            handle.write(
                json.dumps(
                    build_record(pdf_path, max_pages=max_pages), ensure_ascii=False
                )
                + "\n"
            )


if __name__ == "__main__":
    main()
