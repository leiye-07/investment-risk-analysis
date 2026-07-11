from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_fixture(path: str | Path) -> list[dict[str, Any]]:
    fixture_path = Path(path)
    if not fixture_path.exists():
        return []
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.get("items", []))
    return []


def matches_query(item: dict[str, Any], query: str, context: dict) -> bool:
    entity = str(context.get("entity", "")).lower()
    haystack = " ".join(str(value) for value in item.values()).lower()
    if entity and entity in haystack:
        return True
    query_terms = [term for term in query.lower().split() if len(term) > 3]
    return any(term in haystack for term in query_terms)
