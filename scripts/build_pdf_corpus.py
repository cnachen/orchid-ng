from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a lightweight Orchid corpus from local PDF papers."
    )
    parser.add_argument("--papers-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-pages", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_paths = sorted(args.papers_dir.glob("*.pdf"))
    if not pdf_paths:
        raise SystemExit(f"No PDF files found under {args.papers_dir}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for pdf_path in pdf_paths:
            record = build_record(pdf_path, max_pages=args.max_pages)
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(pdf_paths)} papers to {args.output}")


def build_record(pdf_path: Path, max_pages: int) -> dict[str, object]:
    reader = PdfReader(str(pdf_path))
    page_text = "\n".join(
        (reader.pages[index].extract_text() or "")
        for index in range(min(max_pages, len(reader.pages)))
    )
    normalized = normalize_text(page_text)
    title = extract_title(reader, normalized, pdf_path.stem)
    abstract = extract_abstract(normalized)
    year = infer_year(pdf_path.stem)
    venue = extract_venue(normalized)
    claims = abstract_to_claims(abstract)
    risks = infer_risks(abstract)
    applicability = infer_applicability(title, abstract)
    return {
        "paper_id": pdf_path.stem,
        "title": title,
        "abstract": abstract,
        "year": year,
        "venue": venue,
        "authors": [],
        "claims": claims,
        "assumptions": [],
        "risks": risks,
        "applicability": applicability,
    }


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def extract_title(reader: PdfReader, text: str, fallback: str) -> str:
    metadata_title = getattr(reader.metadata, "title", None)
    if isinstance(metadata_title, str):
        cleaned = normalize_inline(metadata_title)
        if cleaned and cleaned.lower() not in {
            "untitled",
            "microsoft word - document1",
        }:
            return cleaned

    lines = [normalize_inline(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    abstract_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.lower() in {"abstract", "summary"}
        ),
        None,
    )
    candidate_lines = (
        lines[:abstract_index] if abstract_index is not None else lines[:12]
    )
    filtered: list[str] = []
    for line in candidate_lines:
        lower = line.lower()
        if lower.startswith("published as"):
            continue
        if lower.startswith("to appear in"):
            continue
        if lower.startswith("arxiv:"):
            continue
        if "university" in lower or "research" in lower or "@" in lower:
            if filtered:
                break
            continue
        if re.search(r"\b\d{4}\b", line) and len(line.split()) > 8 and not filtered:
            continue
        filtered.append(line)
        if len(" ".join(filtered)) > 25 and len(filtered) >= 2:
            break
    title = normalize_inline(" ".join(filtered))
    return title or fallback


def extract_abstract(text: str) -> str:
    abstract_patterns = [
        re.compile(
            r"\babstract\b[:\s]*(.+?)(?=\n(?:1\s+introduction|introduction|keywords|index terms)\b)",
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r"\babstract\b[:\s]*(.+?)(?=\n[A-Z][A-Z ]{6,}\n)",
            re.IGNORECASE | re.DOTALL,
        ),
    ]
    for pattern in abstract_patterns:
        match = pattern.search(text)
        if match:
            return trim_abstract(match.group(1))

    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower() == "abstract":
            candidate = " ".join(lines[index + 1 : index + 10])
            return trim_abstract(candidate)
    return trim_abstract(text[:1600])


def trim_abstract(text: str) -> str:
    text = normalize_inline(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2000]


def normalize_inline(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def infer_year(stem: str) -> int | None:
    match = re.match(r"(\d{2})\d{2}-\d+", stem)
    if not match:
        return None
    year = int(match.group(1))
    return 2000 + year


def extract_venue(text: str) -> str | None:
    patterns = [
        re.compile(
            r"Published as a conference paper at ([A-Za-z0-9 .-]+)", re.IGNORECASE
        ),
        re.compile(r"To Appear in the ([^\n.]+)", re.IGNORECASE),
        re.compile(r"\b([A-Z]{2,}(?:\s+\d{4})?)\b"),
    ]
    for pattern in patterns[:2]:
        match = pattern.search(text)
        if match:
            return normalize_inline(match.group(1))
    return None


def abstract_to_claims(abstract: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", abstract)
    claims = [sentence.strip() for sentence in sentences if sentence.strip()]
    return claims[:2] if claims else [abstract]


def infer_risks(abstract: str) -> list[str]:
    lower = abstract.lower()
    risks: list[str] = []
    for marker in ("however", "but", "although", "despite"):
        if marker in lower:
            sentence = next(
                (
                    segment.strip()
                    for segment in re.split(r"(?<=[.!?])\s+", abstract)
                    if marker in segment.lower()
                ),
                "",
            )
            if sentence:
                risks.append(sentence)
                break
    return risks


def infer_applicability(title: str, abstract: str) -> list[str]:
    pool = f"{title} {abstract}".lower()
    mapping = {
        "ai-generated text detection": (
            "detect",
            "detection",
            "watermark",
            "generated text",
        ),
        "retrieval-assisted defense": ("retrieval", "defense"),
        "authorship and style analysis": ("authorship", "authorial", "style"),
        "toxic content moderation": ("toxic", "moderation"),
    }
    labels = [
        label
        for label, keywords in mapping.items()
        if any(keyword in pool for keyword in keywords)
    ]
    return labels or ["machine-generated text analysis"]


if __name__ == "__main__":
    main()
