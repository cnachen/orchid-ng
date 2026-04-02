from __future__ import annotations

from orchid_ng.domain import (
    EvidenceNote,
    EvidenceType,
    IdeaCandidate,
    PaperRecord,
    ResearchTopic,
)
from orchid_ng.integrations.corpus import CorpusStore


class EvidenceBuilder:
    def __init__(self, corpus_store: CorpusStore, top_k: int = 5) -> None:
        self.corpus_store = corpus_store
        self.top_k = top_k

    def build_background(self, topic: ResearchTopic) -> list[EvidenceNote]:
        query = " ".join([topic.title, topic.question, topic.description, *topic.tags])
        papers = self.corpus_store.search(query=query, top_k=self.top_k)
        return _deduplicate_notes(
            [_paper_to_note(paper, EvidenceType.BACKGROUND) for paper in papers]
        )

    def build_for_idea(self, idea: IdeaCandidate) -> list[EvidenceNote]:
        query = " ".join([idea.title, idea.summary, idea.hypothesis, idea.mechanism])
        papers = self.corpus_store.search(query=query, top_k=self.top_k)
        return _deduplicate_notes(
            [_paper_to_note(paper, EvidenceType.IDEA_SPECIFIC) for paper in papers]
        )


def _paper_to_note(paper: PaperRecord, evidence_type: EvidenceType) -> EvidenceNote:
    claim = paper.claims[0] if paper.claims else paper.abstract
    applicability = paper.applicability or ([paper.venue] if paper.venue else [])
    return EvidenceNote(
        claim=claim,
        evidence_type=evidence_type,
        source_ids=[paper.paper_id],
        assumptions=paper.assumptions,
        risks=paper.risks,
        applicability=applicability,
        rationale=f"Derived from literature snapshot paper: {paper.title}",
    )


def _deduplicate_notes(notes: list[EvidenceNote]) -> list[EvidenceNote]:
    seen: set[str] = set()
    unique_notes: list[EvidenceNote] = []
    for note in notes:
        fingerprint = note.claim.strip().lower()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique_notes.append(note)
    return unique_notes
