from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from retrieval.adapters.source_policy import SourcePolicy, source_domain


URL_PATTERN = re.compile(r"https?://[^\s<>)\"']+", re.I)
DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


class UrlFetcherAdapter:
    source_type = "url_fetcher"

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        source_policy: SourcePolicy | None = None,
        max_chunk_chars: int = 1400,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.source_policy = source_policy or SourcePolicy()
        self.max_chunk_chars = max_chunk_chars

    def search(self, query: str, context: dict) -> list[dict]:
        query_urls = URL_PATTERN.findall(query)
        urls = list(dict.fromkeys(query_urls or context.get("urls", [])))
        records: list[dict] = []
        for url in urls:
            records.extend(self.fetch(url, query=query))
        return records

    def fetch(self, url: str, query: str = "") -> list[dict]:
        retrieved_at = datetime.now(timezone.utc).isoformat()
        domain = source_domain(url)
        if not self.source_policy.allows(url):
            return [
                _retrieval_error(
                    url=url,
                    query=query,
                    retrieved_at=retrieved_at,
                    domain=domain,
                    message="URL rejected by source policy. Use SEC/company IR/reputable financial news/macro providers.",
                )
            ]

        try:
            request = Request(url, headers={"User-Agent": "investment-risk-analysis/0.1"})
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get("content-type", "")
                body = response.read(2_000_000)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return [
                _retrieval_error(
                    url=url,
                    query=query,
                    retrieved_at=retrieved_at,
                    domain=domain,
                    message=f"URL fetch failed: {exc}",
                )
            ]

        text, title = _extract_readable_text(body, content_type)
        if not text:
            return [
                _retrieval_error(
                    url=url,
                    query=query,
                    retrieved_at=retrieved_at,
                    domain=domain,
                    message="URL fetch succeeded but no readable text was extracted.",
                )
            ]

        chunks = _chunk_text(text, self.max_chunk_chars)
        date = _infer_date(text)
        return [
            {
                "source": domain,
                "source_type": self.source_type,
                "title": title,
                "date": date,
                "text": chunk,
                "url": url,
                "metadata": {
                    "domain": domain,
                    "retrieved_at": retrieved_at,
                    "query": query,
                    "adapter": self.source_type,
                    "chunk_index": index,
                    "content_type": content_type,
                },
                "confidence": 0.72,
            }
            for index, chunk in enumerate(chunks, start=1)
        ]


def records_from_search_results(results: list[dict[str, Any]], fetcher: UrlFetcherAdapter, query: str) -> list[dict]:
    records: list[dict] = []
    for result in results:
        url = str(result.get("url") or "")
        if not url:
            continue
        fetched = fetcher.fetch(url, query=query)
        for record in fetched:
            metadata = dict(record.get("metadata") or {})
            metadata.setdefault("search_title", result.get("title"))
            metadata.setdefault("search_snippet", result.get("snippet"))
            record["metadata"] = metadata
            records.append(record)
    return records


class _ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self._in_title = False
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "br", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        clean = " ".join(data.split())
        if not clean:
            return
        if self._in_title:
            self.title = clean if self.title is None else f"{self.title} {clean}"
        elif self._skip_depth == 0:
            self.parts.append(clean)


def _extract_readable_text(body: bytes, content_type: str) -> tuple[str, str | None]:
    encoding = "utf-8"
    match = re.search(r"charset=([\w.-]+)", content_type, re.I)
    if match:
        encoding = match.group(1)
    raw = body.decode(encoding, errors="replace")
    if "html" not in content_type.lower():
        return _clean_text(raw), None
    parser = _ReadableHTMLParser()
    parser.feed(raw)
    return _clean_text(" ".join(parser.parts)), parser.title


def _clean_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _chunk_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n|\.\s+", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph if paragraph.endswith(".") else f"{paragraph}."
        if current and len(current) + len(paragraph) + 1 > max_chars:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = f"{current} {paragraph}".strip()
    if current:
        chunks.append(current.strip())
    return chunks


def _infer_date(text: str) -> str:
    match = DATE_PATTERN.search(text)
    return match.group(1) if match else "unknown"


def _retrieval_error(url: str, query: str, retrieved_at: str, domain: str, message: str) -> dict:
    return {
        "source": "retrieval_error",
        "source_type": "retrieval_error",
        "title": "External retrieval failed",
        "date": "unknown",
        "text": message,
        "url": url,
        "metadata": {
            "domain": domain,
            "retrieved_at": retrieved_at,
            "query": query,
            "adapter": "url_fetcher",
            "retrieval_error": message,
            "critical": True,
        },
        "confidence": 0.0,
    }
