from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from orchid_ng.domain import PaperRecord


class CorpusValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_count: int
    file_count: int
    duplicate_ids: list[str] = Field(default_factory=list)
    records_without_claims: list[str] = Field(default_factory=list)
    records_without_risks: list[str] = Field(default_factory=list)


class CorpusStore:
    def __init__(
        self, records: list[PaperRecord], source_path: Path | None = None
    ) -> None:
        self._records = records
        self.source_path = source_path

    @classmethod
    def empty(cls) -> "CorpusStore":
        return cls([])

    @classmethod
    def from_path(cls, path: Path) -> "CorpusStore":
        path = path.resolve()
        files = (
            [path]
            if path.is_file()
            else sorted(path.glob("*.jsonl")) + sorted(path.glob("*.json"))
        )
        if not files:
            raise FileNotFoundError(f"No corpus files found under {path}")
        records: list[PaperRecord] = []
        for file_path in files:
            if file_path.suffix == ".jsonl":
                for line in file_path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        records.append(PaperRecord.model_validate_json(line))
            elif file_path.suffix == ".json":
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    records.extend(PaperRecord.model_validate(item) for item in payload)
                else:
                    raise ValueError(f"{file_path} must contain a JSON array")
        return cls(records=records, source_path=path)

    @property
    def records(self) -> list[PaperRecord]:
        return list(self._records)

    def search(self, query: str, top_k: int) -> list[PaperRecord]:
        if not self._records or top_k <= 0:
            return []
        query_tokens = set(_tokenize(query))
        scored_records = []
        for record in self._records:
            haystack = " ".join(
                [
                    record.title,
                    record.abstract,
                    " ".join(record.claims),
                    " ".join(record.assumptions),
                    " ".join(record.risks),
                    " ".join(record.applicability),
                ]
            )
            haystack_tokens = set(_tokenize(haystack))
            overlap = len(query_tokens & haystack_tokens)
            recency_bonus = (record.year or 0) / 10_000
            score = overlap + recency_bonus
            scored_records.append((score, record))
        scored_records.sort(
            key=lambda item: (-item[0], -(item[1].year or 0), item[1].paper_id)
        )
        return [record for score, record in scored_records if score > 0][:top_k]

    def validate(self) -> CorpusValidationReport:
        duplicate_ids = sorted(
            _find_duplicates(record.paper_id for record in self._records)
        )
        return CorpusValidationReport(
            record_count=len(self._records),
            file_count=1
            if self.source_path and self.source_path.is_file()
            else len(self._source_files()),
            duplicate_ids=duplicate_ids,
            records_without_claims=sorted(
                record.paper_id for record in self._records if not record.claims
            ),
            records_without_risks=sorted(
                record.paper_id for record in self._records if not record.risks
            ),
        )

    def _source_files(self) -> list[Path]:
        if self.source_path is None:
            return []
        if self.source_path.is_file():
            return [self.source_path]
        return sorted(self.source_path.glob("*.jsonl")) + sorted(
            self.source_path.glob("*.json")
        )


def _find_duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return duplicates


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())
