from orchid_ng.integrations import CorpusStore
from orchid_ng.services.evidence import EvidenceBuilder


def test_evidence_builder_builds_background_notes(topic, corpus_path) -> None:
    builder = EvidenceBuilder(CorpusStore.from_path(corpus_path), top_k=2)
    notes = builder.build_background(topic)
    assert notes
    assert notes[0].evidence_type == "background"
    assert notes[0].source_ids
