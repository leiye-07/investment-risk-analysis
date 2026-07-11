from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


TRUSTED_DOMAINS = {
    "sec.gov",
    "www.sec.gov",
    "nasdaq.com",
    "www.nasdaq.com",
    "nyse.com",
    "www.nyse.com",
    "federalreserve.gov",
    "www.federalreserve.gov",
    "bea.gov",
    "www.bea.gov",
    "bls.gov",
    "www.bls.gov",
    "treasury.gov",
    "www.treasury.gov",
    "reuters.com",
    "www.reuters.com",
    "apnews.com",
    "www.apnews.com",
    "wsj.com",
    "www.wsj.com",
    "ft.com",
    "www.ft.com",
    "cnbc.com",
    "www.cnbc.com",
    "marketwatch.com",
    "www.marketwatch.com",
    "morningstar.com",
    "www.morningstar.com",
    "spglobal.com",
    "www.spglobal.com",
}


@dataclass(frozen=True)
class SourcePolicy:
    trusted_domains: set[str] = field(default_factory=lambda: set(TRUSTED_DOMAINS))
    allow_investor_relations_paths: bool = True

    def allows(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = _hostname(parsed.netloc)
        if not parsed.scheme.startswith("http") or not domain:
            return False
        if domain in {item.removeprefix("www.") for item in self.trusted_domains}:
            return True
        if self.allow_investor_relations_paths:
            labels = domain.split(".")
            path = parsed.path.lower()
            if labels[0] in {"ir", "investor", "investors"}:
                return True
            if any(part in path for part in ("/investor", "/investors", "/financials", "/sec-filings")):
                return True
        return False


def source_domain(url: str) -> str:
    return _hostname(urlparse(url).netloc)


def _hostname(netloc: str) -> str:
    return netloc.lower().split("@")[-1].split(":")[0].removeprefix("www.")
