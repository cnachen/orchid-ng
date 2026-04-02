from orchid_ng.integrations import CorpusStore


def test_corpus_search_is_stable(corpus_path) -> None:
    store = CorpusStore.from_path(corpus_path)
    results = store.search("grounding feasibility retrieval", top_k=2)
    assert results[0].paper_id == "paper_grounding"


def test_corpus_validate_counts_records(corpus_path) -> None:
    store = CorpusStore.from_path(corpus_path)
    report = store.validate()
    assert report.record_count == 3
    assert report.duplicate_ids == []
    assert report.records_without_claims == []


def test_corpus_search_prefers_title_and_claim_matches(corpus_path) -> None:
    store = CorpusStore.from_path(corpus_path)
    results = store.search("pairwise critique preference search", top_k=2)
    assert results[0].paper_id == "paper_search"
