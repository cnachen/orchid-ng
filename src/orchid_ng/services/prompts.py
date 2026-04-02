from __future__ import annotations

from pathlib import Path

from orchid_ng.domain import CritiqueAction, EvidenceNote, IdeaCandidate, ResearchTopic


class PromptLibrary:
    def __init__(self, prompt_dir: Path) -> None:
        self.prompt_dir = prompt_dir

    def render(self, name: str, **context: str) -> str:
        template_path = self.prompt_dir / f"{name}.md"
        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")
        template = template_path.read_text(encoding="utf-8")
        return template.format(**context)


def format_topic(topic: ResearchTopic) -> str:
    constraints = "\n".join(f"- {item}" for item in topic.constraints) or "- None"
    tags = ", ".join(topic.tags) or "none"
    return (
        f"Title: {topic.title}\n"
        f"Question: {topic.question}\n"
        f"Description: {topic.description or 'N/A'}\n"
        f"Constraints:\n{constraints}\n"
        f"Budget Tokens: {topic.budget_tokens}\n"
        f"Tags: {tags}"
    )


def format_evidence(notes: list[EvidenceNote]) -> str:
    if not notes:
        return "- No evidence notes available."
    blocks = []
    for note in notes:
        assumptions = "; ".join(note.assumptions) or "none"
        risks = "; ".join(note.risks) or "none"
        applicability = "; ".join(note.applicability) or "none"
        blocks.append(
            (
                f"- [{note.note_id}] claim={note.claim}\n"
                f"  sources={', '.join(note.source_ids) or 'none'}\n"
                f"  assumptions={assumptions}\n"
                f"  risks={risks}\n"
                f"  applicability={applicability}"
            )
        )
    return "\n".join(blocks)


def format_ideas(ideas: list[IdeaCandidate]) -> str:
    if not ideas:
        return "- No idea candidates available."
    blocks = []
    for idea in ideas:
        conditions = "; ".join(idea.required_conditions) or "none"
        risks = "; ".join(idea.open_risks) or "none"
        evidence_ids = ", ".join(idea.supporting_evidence_ids) or "none"
        questions = "; ".join(idea.task_description.questions[:4]) or "none"
        objectives = "; ".join(idea.task_description.research_objective[:4]) or "none"
        contributions = "; ".join(idea.task_description.contributions[:4]) or "none"
        modules = "; ".join(module.name for module in idea.method.modules[:6]) or "none"
        blocks.append(
            (
                f"- [{idea.idea_id}] {idea.title}\n"
                f"  task_summary={idea.task_description.summary or idea.summary}\n"
                f"  hypothesis={idea.hypothesis}\n"
                f"  method_summary={idea.method.summary or idea.mechanism}\n"
                f"  questions={questions}\n"
                f"  objectives={objectives}\n"
                f"  contributions={contributions}\n"
                f"  modules={modules}\n"
                f"  framework={idea.method.framework or 'none'}\n"
                f"  required_conditions={conditions}\n"
                f"  resource_cost={idea.resource_cost}\n"
                f"  open_risks={risks}\n"
                f"  supporting_evidence_ids={evidence_ids}"
            )
        )
    return "\n".join(blocks)


def format_actions(actions: list[CritiqueAction]) -> str:
    if not actions:
        return "- No critique actions."
    return "\n".join(
        f"- {action.action_type}: {action.instruction}" for action in actions
    )


def format_alignment_gaps(gaps: list[str]) -> str:
    if not gaps:
        return "- No explicit alignment gaps detected."
    return "\n".join(f"- {gap}" for gap in gaps)
