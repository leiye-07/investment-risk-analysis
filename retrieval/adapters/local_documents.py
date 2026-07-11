from __future__ import annotations

import re
from pathlib import Path


SECTION_PATTERN = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)


class LocalDocumentRetriever:
    source_type = "local_documents"

    def __init__(self, documents_dir: str | Path = "data/documents") -> None:
        self.documents_dir = Path(documents_dir)

    def search(self, query: str, context: dict) -> list[dict]:
        documents = self._load_documents()
        if not documents:
            return []

        records: list[dict] = []
        entity = str(context.get("entity", ""))
        for path, text in documents:
            for chunk, section in _chunk_document(text):
                score = _score_chunk(chunk, path, query, entity)
                if score <= 0:
                    continue
                records.append(
                    {
                        "source": path.name,
                        "source_type": self.source_type,
                        "title": section or path.stem,
                        "date": _infer_date(path.name, chunk),
                        "text": chunk,
                        "url": None,
                        "section": section,
                        "confidence": min(0.99, 0.45 + score / 20),
                        "metadata": {
                            "path": str(path),
                            "retrieval_score": score,
                            "adapter": self.source_type,
                        },
                    }
                )
        records.sort(key=lambda item: item["metadata"]["retrieval_score"], reverse=True)
        return records

    def _load_documents(self) -> list[tuple[Path, str]]:
        if not self.documents_dir.exists():
            return []
        files: list[tuple[Path, str]] = []
        for path in sorted(self.documents_dir.glob("**/*")):
            if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
                files.append((path, path.read_text(encoding="utf-8")))
        return files


def _chunk_document(text: str, max_chars: int = 1400) -> list[tuple[str, str | None]]:
    sections = list(SECTION_PATTERN.finditer(text))
    if not sections:
        return [(chunk.strip(), None) for chunk in _window(text, max_chars) if chunk.strip()]

    chunks: list[tuple[str, str | None]] = []
    for index, match in enumerate(sections):
        start = match.end()
        end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
        section_text = text[start:end].strip()
        for chunk in _window(section_text, max_chars):
            if chunk.strip():
                chunks.append((chunk.strip(), match.group(1).strip()))
    return chunks


def _window(text: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 > max_chars and current:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def _score_chunk(chunk: str, path: Path, query: str, entity: str) -> int:
    haystack = f"{path.name} {chunk}".lower()
    query_terms = {part for part in query.lower().split() if len(part) > 3}
    terms = query_terms | ({entity.lower()} if entity else set())
    score = sum(1 for term in terms if term and term in haystack)
    risk_terms = [
        "risk",
        "decline",
        "pressure",
        "competition",
        "debt",
        "liquidity",
        "margin",
        "supply",
        "demand",
        "regulatory",
        "cash flow",
        "revenue",
    ]
    score += sum(2 for term in risk_terms if term in haystack)
    return score


def _infer_date(filename: str, text: str) -> str:
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", f"{filename} {text}")
    return match.group(1) if match else "unknown"
