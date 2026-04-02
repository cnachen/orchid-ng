from __future__ import annotations

import re
from statistics import mean

from orchid_ng.domain import IdeaCandidate, ResearchTopic

STYLE_ALIGNMENT_PROFILE = {
    "questions": 4,
    "objectives": 4,
    "contributions": 5,
    "modules": 5,
    "keywords": 6,
    "research_areas": 3,
    "task_summary_words": 140,
    "method_summary_words": 148,
    "framework_words": 130,
    "required_conditions": 3,
    "open_risks": 3,
    "supporting_evidence_ids": 3,
}


def score_idea_alignment(idea: IdeaCandidate) -> float:
    components = [
        _presence_score(bool(idea.task_description.summary)),
        _presence_score(bool(idea.method.summary)),
        _presence_score(bool(idea.method.framework)),
        _presence_score(len(idea.method.modules) >= 5),
        _target_count_score(
            len(idea.task_description.questions),
            target=STYLE_ALIGNMENT_PROFILE["questions"],
            tolerance=1,
        ),
        _target_count_score(
            len(idea.task_description.research_objective),
            target=STYLE_ALIGNMENT_PROFILE["objectives"],
            tolerance=1,
        ),
        _target_count_score(
            len(idea.task_description.contributions),
            target=STYLE_ALIGNMENT_PROFILE["contributions"],
            tolerance=1,
        ),
        _target_count_score(
            len(idea.method.modules),
            target=STYLE_ALIGNMENT_PROFILE["modules"],
            tolerance=1,
        ),
        _target_count_score(
            len(idea.task_description.keywords),
            target=STYLE_ALIGNMENT_PROFILE["keywords"],
            tolerance=2,
        ),
        _target_count_score(
            len(idea.task_description.research_area),
            target=STYLE_ALIGNMENT_PROFILE["research_areas"],
            tolerance=1,
        ),
        _word_count_score(
            idea.task_description.summary,
            target=STYLE_ALIGNMENT_PROFILE["task_summary_words"],
            tolerance=22,
        ),
        _word_count_score(
            idea.method.summary,
            target=STYLE_ALIGNMENT_PROFILE["method_summary_words"],
            tolerance=16,
        ),
        _word_count_score(
            idea.method.framework,
            target=STYLE_ALIGNMENT_PROFILE["framework_words"],
            tolerance=15,
        ),
        _target_count_score(
            len(idea.required_conditions),
            target=STYLE_ALIGNMENT_PROFILE["required_conditions"],
            tolerance=1,
        ),
        _target_count_score(
            len(idea.open_risks),
            target=STYLE_ALIGNMENT_PROFILE["open_risks"],
            tolerance=1,
        ),
        _target_count_score(
            len(idea.supporting_evidence_ids),
            target=STYLE_ALIGNMENT_PROFILE["supporting_evidence_ids"],
            tolerance=2,
        ),
    ]
    return round(sum(components) / len(components) * 100, 2)


def rank_ideas_by_alignment(ideas: list[IdeaCandidate]) -> list[IdeaCandidate]:
    return sorted(
        ideas,
        key=lambda idea: (
            -score_idea_alignment(idea),
            -len(idea.method.modules),
            -len(idea.task_description.contributions),
            idea.idea_id,
        ),
    )


def select_idea_portfolio(
    ideas: list[IdeaCandidate],
    topic: ResearchTopic,
    target_size: int,
) -> list[IdeaCandidate]:
    if target_size <= 0:
        return []
    candidates = _deduplicate_by_similarity(ideas)
    if len(candidates) < target_size:
        selected_ids = {idea.idea_id for idea in candidates}
        selected_titles = {_normalize_title(idea.title) for idea in candidates}
        for idea in rank_ideas_by_alignment(ideas):
            if idea.idea_id in selected_ids:
                continue
            normalized_title = _normalize_title(idea.title)
            if normalized_title and normalized_title in selected_titles:
                continue
            candidates.append(idea)
            selected_ids.add(idea.idea_id)
            selected_titles.add(normalized_title)
            if len(candidates) >= target_size:
                break
    if len(candidates) <= target_size:
        return rank_ideas_by_alignment(candidates)

    selected: list[IdeaCandidate] = []
    while candidates and len(selected) < target_size:
        best_index = 0
        best_score = -1.0
        for index, idea in enumerate(candidates):
            alignment = score_idea_alignment(idea) / 100
            topicality = score_idea_topicality(idea, topic)
            evidence = min(len(idea.supporting_evidence_ids), 4) / 4
            structure = min(len(idea.method.modules), 6) / 6
            base_score = (
                0.5 * alignment + 0.25 * topicality + 0.15 * evidence + 0.1 * structure
            )
            diversity_penalty = (
                max(idea_similarity(idea, selected_idea) for selected_idea in selected)
                if selected
                else 0.0
            )
            portfolio_score = base_score - 0.35 * diversity_penalty
            if portfolio_score > best_score:
                best_score = portfolio_score
                best_index = index
        selected.append(candidates.pop(best_index))
    return selected


def alignment_gaps(idea: IdeaCandidate) -> list[str]:
    gaps: list[str] = []
    if len(idea.method.modules) < 5:
        gaps.append("method modules are too shallow")
    if len(idea.method.modules) > 6:
        gaps.append("method modules should be tighter")
    if len(idea.task_description.questions) < 4:
        gaps.append("research questions are missing or underspecified")
    if len(idea.task_description.research_objective) < 4:
        gaps.append("research objectives are missing or underspecified")
    if len(idea.task_description.contributions) < 5:
        gaps.append("contributions are missing or underspecified")

    task_summary_words = len(idea.task_description.summary.split())
    if task_summary_words < 125:
        gaps.append("task summary lacks benchmark-style detail")
    if task_summary_words > 155:
        gaps.append("task summary is too long and should be tightened")

    method_summary_words = len(idea.method.summary.split())
    if method_summary_words < 135:
        gaps.append("method summary lacks concrete technical detail")
    if method_summary_words > 155:
        gaps.append("method summary is too long and should be tightened")

    framework_words = len(idea.method.framework.split())
    if framework_words < 118:
        gaps.append("framework description lacks pipeline detail")
    if framework_words > 140:
        gaps.append("framework description is too long and should be tightened")

    if len(idea.supporting_evidence_ids) < 2:
        gaps.append("evidence grounding is too weak")
    if len(idea.task_description.keywords) < 6:
        gaps.append("keywords are too sparse")
    if len(idea.task_description.research_area) < 3:
        gaps.append("research areas are too sparse")
    if len(idea.required_conditions) < 3:
        gaps.append("required conditions are too vague")
    return gaps


def build_alignment_report(
    run_id: str,
    ideas: list[IdeaCandidate],
) -> dict[str, object]:
    diversity = portfolio_diversity_metrics(ideas)
    scored_ideas = [
        {
            "idea_id": idea.idea_id,
            "title": idea.title,
            "alignment_score": score_idea_alignment(idea),
            "gaps": alignment_gaps(idea),
            "task_summary_words": len(idea.task_description.summary.split()),
            "method_summary_words": len(idea.method.summary.split()),
            "framework_words": len(idea.method.framework.split()),
            "module_count": len(idea.method.modules),
            "question_count": len(idea.task_description.questions),
            "objective_count": len(idea.task_description.research_objective),
            "contribution_count": len(idea.task_description.contributions),
        }
        for idea in ideas
    ]
    overall_score = (
        round(mean(item["alignment_score"] for item in scored_ideas), 2)
        if scored_ideas
        else 0.0
    )
    return {
        "run_id": run_id,
        "overall_alignment_score": overall_score,
        "style_profile": dict(STYLE_ALIGNMENT_PROFILE),
        "portfolio_metrics": diversity,
        "idea_reports": scored_ideas,
    }


def _presence_score(present: bool) -> float:
    return 1.0 if present else 0.0


def _target_count_score(value: int, target: int, tolerance: int) -> float:
    return max(0.0, 1.0 - abs(value - target) / max(tolerance, 1))


def _word_count_score(text: str, target: int, tolerance: int) -> float:
    value = len(text.split())
    return max(0.0, 1.0 - abs(value - target) / max(tolerance, 1))


def score_idea_topicality(idea: IdeaCandidate, topic: ResearchTopic) -> float:
    topic_tokens = set(_tokenize(_topic_text(topic)))
    if not topic_tokens:
        return 0.0
    idea_tokens = set(_tokenize(_idea_text(idea)))
    return len(topic_tokens & idea_tokens) / len(topic_tokens)


def idea_similarity(left: IdeaCandidate, right: IdeaCandidate) -> float:
    left_tokens = set(_tokenize(_idea_text(left)))
    right_tokens = set(_tokenize(_idea_text(right)))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def portfolio_diversity_metrics(ideas: list[IdeaCandidate]) -> dict[str, float]:
    if not ideas:
        return {
            "idea_count": 0,
            "unique_title_count": 0,
            "duplicate_title_count": 0,
            "avg_pairwise_similarity": 0.0,
            "title_diversity_score": 0.0,
        }
    similarities = [
        idea_similarity(left, right)
        for index, left in enumerate(ideas)
        for right in ideas[index + 1 :]
    ]
    unique_titles = {idea.title.strip().lower() for idea in ideas if idea.title.strip()}
    title_diversity = len(unique_titles) / len(ideas)
    return {
        "idea_count": len(ideas),
        "unique_title_count": len(unique_titles),
        "duplicate_title_count": len(ideas) - len(unique_titles),
        "avg_pairwise_similarity": round(mean(similarities), 4)
        if similarities
        else 0.0,
        "title_diversity_score": round(title_diversity, 4),
    }


def _deduplicate_by_similarity(ideas: list[IdeaCandidate]) -> list[IdeaCandidate]:
    selected: list[IdeaCandidate] = []
    for idea in rank_ideas_by_alignment(ideas):
        if any(_is_near_duplicate(idea, existing) for existing in selected):
            continue
        selected.append(idea)
    return selected


def _is_near_duplicate(left: IdeaCandidate, right: IdeaCandidate) -> bool:
    left_title = _normalize_title(left.title)
    right_title = _normalize_title(right.title)
    if left_title and left_title == right_title:
        return True
    return idea_similarity(left, right) >= 0.9


def _normalize_title(title: str) -> str:
    return " ".join(_tokenize(title))


def _idea_text(idea: IdeaCandidate) -> str:
    return " ".join(
        [
            idea.title,
            idea.summary,
            idea.hypothesis,
            idea.mechanism,
            idea.task_description.summary,
            " ".join(idea.task_description.keywords),
            " ".join(idea.task_description.research_area),
            " ".join(idea.task_description.questions),
            " ".join(idea.task_description.research_objective),
            " ".join(idea.task_description.contributions),
            idea.method.summary,
            idea.method.framework,
            " ".join(module.name for module in idea.method.modules),
            " ".join(module.description for module in idea.method.modules),
        ]
    )


def _topic_text(topic: ResearchTopic) -> str:
    return " ".join(
        [
            topic.title,
            topic.question,
            topic.description,
            *topic.constraints,
            *topic.tags,
        ]
    )


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())
