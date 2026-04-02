from __future__ import annotations

import json
from pathlib import Path

import typer

from orchid_ng.config.settings import Settings
from orchid_ng.domain import ResearchTopic
from orchid_ng.integrations.corpus import CorpusStore
from orchid_ng.storage.run_store import RunStore
from orchid_ng.workflows.evaluate import run_evaluation
from orchid_ng.workflows.ideate import run_ideation

app = typer.Typer(help="Orchid v1 research ideation toolkit.")
corpus_app = typer.Typer(help="Corpus validation helpers.")
ideate_app = typer.Typer(help="Generate ideas for an open research topic.")
evaluate_app = typer.Typer(help="Run pairwise final evaluation.")
report_app = typer.Typer(help="Inspect saved run reports.")

app.add_typer(corpus_app, name="corpus")
app.add_typer(ideate_app, name="ideate")
app.add_typer(evaluate_app, name="evaluate")
app.add_typer(report_app, name="report")


@corpus_app.command("validate")
def validate_corpus(
    corpus: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=True),
) -> None:
    store = CorpusStore.from_path(corpus)
    report = store.validate()
    typer.echo(
        json.dumps(
            report.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
    )


@ideate_app.command("run")
def ideate_run(
    title: str = typer.Option(..., help="Broad research topic title."),
    question: str = typer.Option(..., help="Research question to explore."),
    description: str = typer.Option("", help="Optional context for the topic."),
    constraint: list[str] = typer.Option(
        None,
        "--constraint",
        help="Constraint to respect during ideation. Repeat for multiple values.",
    ),
    tag: list[str] = typer.Option(
        None,
        "--tag",
        help="Optional tags for the topic. Repeat for multiple values.",
    ),
    corpus: Path | None = typer.Option(
        None,
        exists=True,
        file_okay=True,
        dir_okay=True,
        help="Frozen literature snapshot as JSON or JSONL.",
    ),
    method: str = typer.Option("orchid", help="Idea generation method."),
    model: str = typer.Option("gpt-4o-mini", help="Generation model."),
    run_id: str | None = typer.Option(None, help="Optional custom run id."),
    desired_idea_count: int = typer.Option(2, min=1, help="Seed idea count."),
    budget_tokens: int = typer.Option(20_000, min=1, help="Budget hint."),
    search_rounds: int = typer.Option(1, min=0, help="Search refinement rounds."),
    project_root: Path = typer.Option(
        Path.cwd(),
        file_okay=False,
        dir_okay=True,
        help="Workspace root that contains runs/.",
    ),
) -> None:
    settings = Settings(
        project_root=project_root,
        corpus_path=corpus,
        model_name=model,
        search_rounds=search_rounds,
    )
    topic = ResearchTopic(
        title=title,
        question=question,
        description=description,
        constraints=constraint or [],
        tags=tag or [],
        desired_idea_count=desired_idea_count,
        budget_tokens=budget_tokens,
    )
    manifest = run_ideation(topic, settings, method_name=method, run_id=run_id)
    typer.echo(f"run_id={manifest.run_id}")
    typer.echo(f"status={manifest.status}")
    typer.echo(f"method={manifest.method_name}")


@evaluate_app.command("run")
def evaluate_run(
    run_id: str = typer.Option(..., help="Run identifier under runs/."),
    judge_model: str = typer.Option("gpt-5.2", help="Judge model."),
    project_root: Path = typer.Option(
        Path.cwd(),
        file_okay=False,
        dir_okay=True,
        help="Workspace root that contains runs/.",
    ),
) -> None:
    settings = Settings(project_root=project_root, model_name=judge_model)
    report = run_evaluation(run_id=run_id, settings=settings)
    typer.echo(f"run_id={report.run_id}")
    typer.echo(f"top_idea={report.overall_preference_order[0]}")
    typer.echo(f"pairwise_judgments={report.pairwise_judgment_count}")


@report_app.command("show")
def show_report(
    run_id: str = typer.Option(..., help="Run identifier under runs/."),
    project_root: Path = typer.Option(
        Path.cwd(),
        file_okay=False,
        dir_okay=True,
        help="Workspace root that contains runs/.",
    ),
) -> None:
    store = RunStore(Settings(project_root=project_root).runs_dir)
    run_session = store.open_run(run_id)
    report = run_session.load_report()
    typer.echo(
        json.dumps(
            report.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
    )


def main() -> None:
    app()
