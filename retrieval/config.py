from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


RetrievalMode = Literal["live", "fixture", "hybrid"]


@dataclass(frozen=True)
class RetrievalConfig:
    mode: RetrievalMode = "live"
    timeout_seconds: float = 10.0
    max_search_results: int = 5


def load_retrieval_config(mode: str | None = None) -> RetrievalConfig:
    configured = (mode or os.getenv("RETRIEVAL_MODE") or "live").strip().lower()
    if configured not in {"live", "fixture", "hybrid"}:
        raise ValueError("RETRIEVAL_MODE must be one of: live, fixture, hybrid")
    return RetrievalConfig(mode=configured)  # type: ignore[arg-type]
