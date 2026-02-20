# Phase 1: Semantic Scholar Browser Module

## Goal

Create `agent/browsing/manual/sources/semantic_scholar.py` — a `ManualSource`-compatible
client that resolves DOIs/URLs, fetches paper metadata, citations, and SPECTER2 embeddings
from the Semantic Scholar API.

## New File

**`agent/browsing/manual/sources/semantic_scholar.py`**

```python
import os
import time
import requests
from dataclasses import dataclass, field
from typing import List, Optional, Iterator
from .base import SearchItem, ManualSource

SS_BASE = "https://api.semanticscholar.org/graph/v1"
SS_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

PAPER_FIELDS = "paperId,externalIds,title,abstract,year,authors,citationCount,referenceCount,fieldsOfStudy,embedding"

@dataclass
class SSPaper:
    paper_id: str
    title: str
    abstract: Optional[str]
    year: Optional[int]
    authors: List[str]
    citation_count: int
    doi: Optional[str]
    fields_of_study: List[str]
    embedding: Optional[List[float]] = field(default=None)  # SPECTER2, 768-dim

class SemanticScholarBrowser:
    """Wraps Semantic Scholar Graph API. Implements ManualSource protocol."""

    def __init__(self, rps: float = 1.0):
        self._session = requests.Session()
        if SS_API_KEY:
            self._session.headers["x-api-key"] = SS_API_KEY
        self._min_interval = 1.0 / rps
        self._last_call = 0.0

    def _get(self, path: str, params: dict) -> dict:
        now = time.monotonic()
        wait = self._min_interval - (now - self._last_call)
        if wait > 0:
            time.sleep(wait)
        r = self._session.get(f"{SS_BASE}{path}", params=params, timeout=15)
        self._last_call = time.monotonic()
        r.raise_for_status()
        return r.json()

    def get_by_id(self, paper_id: str) -> Optional[SSPaper]:
        """Fetch a paper by Semantic Scholar paperId or DOI (prefix with 'DOI:')."""
        data = self._get(f"/paper/{paper_id}", {"fields": PAPER_FIELDS})
        return self._parse(data)

    def get_by_url(self, url: str) -> Optional[SSPaper]:
        """Resolve a URL (eLife, ACS, etc.) to a Semantic Scholar paper."""
        data = self._get(f"/paper/URL:{url}", {"fields": PAPER_FIELDS})
        return self._parse(data)

    def get_citations(self, paper_id: str, limit: int = 50) -> List[SSPaper]:
        data = self._get(
            f"/paper/{paper_id}/citations",
            {"fields": PAPER_FIELDS, "limit": limit}
        )
        return [self._parse(item["citingPaper"]) for item in data.get("data", []) if item.get("citingPaper")]

    def get_references(self, paper_id: str, limit: int = 50) -> List[SSPaper]:
        data = self._get(
            f"/paper/{paper_id}/references",
            {"fields": PAPER_FIELDS, "limit": limit}
        )
        return [self._parse(item["citedPaper"]) for item in data.get("data", []) if item.get("citedPaper")]

    def search(self, query: str, max_results: int = 25, start: int = 0, **kwargs) -> List[SearchItem]:
        data = self._get("/paper/search", {
            "query": query,
            "fields": PAPER_FIELDS,
            "limit": max_results,
            "offset": start,
        })
        items = []
        for p in data.get("data", []):
            paper = self._parse(p)
            if paper:
                items.append(SearchItem(
                    title=paper.title,
                    url=f"https://www.semanticscholar.org/paper/{paper.paper_id}",
                    snippet=paper.abstract[:300] if paper.abstract else None,
                    item_id=paper.paper_id,
                    extra={"doi": paper.doi, "year": paper.year, "embedding": paper.embedding},
                ))
        return items

    def iter_all(self, query: str, chunk_size: int = 100, limit=None) -> Iterator[SearchItem]:
        offset = 0
        fetched = 0
        while True:
            batch = self.search(query, max_results=min(chunk_size, 100), start=offset)
            if not batch:
                break
            for item in batch:
                yield item
                fetched += 1
                if limit and fetched >= limit:
                    return
            offset += len(batch)

    def search_all(self, query: str, limit=None) -> List[SearchItem]:
        return list(self.iter_all(query, limit=limit))

    @staticmethod
    def _parse(data: dict) -> Optional["SSPaper"]:
        if not data or not data.get("paperId"):
            return None
        ext = data.get("externalIds") or {}
        emb = data.get("embedding")
        return SSPaper(
            paper_id=data["paperId"],
            title=data.get("title") or "",
            abstract=data.get("abstract"),
            year=data.get("year"),
            authors=[a["name"] for a in data.get("authors", [])],
            citation_count=data.get("citationCount", 0),
            doi=ext.get("DOI"),
            fields_of_study=data.get("fieldsOfStudy") or [],
            embedding=emb.get("vector") if emb else None,
        )
```

## Integration into `collect_candidates`

In `agent/pipeline/search.py`, add a branch for `src == "semantic_scholar"`:

```python
elif src == "semantic_scholar":
    from agent.browsing.manual.sources.semantic_scholar import SemanticScholarBrowser
    browser = SemanticScholarBrowser()
    ss_items = browser.search(q, max_results=per_query_limit)
    page = [_ss_item_to_candidate(item) for item in ss_items]
```

Add helper `_ss_item_to_candidate`:

```python
def _ss_item_to_candidate(item: SearchItem) -> PaperCandidate:
    extra = item.extra or {}
    return PaperCandidate(
        arxiv_id=item.item_id or item.url,
        title=item.title,
        summary=item.snippet or "",
        url=item.url,
        published=str(extra.get("year", "")),
        source="semantic_scholar",
    )
```

## Strategy Agent Update

Add `"semantic_scholar"` as a valid source in `strategy.py` system prompt and the
`GeneratedQuery.source` literal type in `models.py`:

```python
# models.py
source: Literal["arxiv", "pubmed", "scholar", "github", "semantic_scholar"] = "arxiv"
```

## Dependencies

No new packages needed — uses `requests` (already in `pyproject.toml`).
