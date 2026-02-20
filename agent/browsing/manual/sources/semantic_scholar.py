"""Semantic Scholar Graph API browser.

Implements the :class:`ManualSource` protocol and provides additional methods
for fetching paper metadata, citations, references, and SPECTER2 embeddings.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

import requests

from .base import ManualSource, SearchItem

SS_BASE = "https://api.semanticscholar.org/graph/v1"

PAPER_FIELDS = (
    "paperId,externalIds,title,abstract,year,authors,"
    "citationCount,referenceCount,fieldsOfStudy,embedding"
)


@dataclass
class SSPaper:
    """Lightweight representation of a Semantic Scholar paper.

    :ivar paper_id: Semantic Scholar internal paper ID.
    :ivar title: Paper title.
    :ivar abstract: Abstract text, if available.
    :ivar year: Publication year.
    :ivar authors: List of author name strings.
    :ivar citation_count: Number of citing papers.
    :ivar doi: DOI string, if available.
    :ivar fields_of_study: List of field-of-study labels.
    :ivar embedding: SPECTER2 embedding vector (768-dim), if available.
    """

    paper_id: str
    title: str
    abstract: Optional[str]
    year: Optional[int]
    authors: List[str]
    citation_count: int
    doi: Optional[str]
    fields_of_study: List[str]
    embedding: Optional[List[float]] = field(default=None)


class SemanticScholarBrowser:
    """Wraps the Semantic Scholar Graph API.

    Implements the :class:`ManualSource` protocol so it can be used as a
    drop-in search source in the pipeline, and also exposes richer methods
    for citation/reference traversal used by the graph builder.

    :param rps: Maximum requests per second (default 1.0 for authenticated).
    """

    def __init__(self, rps: float = 1.0) -> None:
        self._session = requests.Session()
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
        if api_key:
            self._session.headers["x-api-key"] = api_key
        self._min_interval = 1.0 / rps
        self._last_call: float = 0.0

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
        """Fetch a paper by Semantic Scholar paperId or prefixed DOI (``DOI:10.xxx``).

        :param paper_id: Semantic Scholar paper ID or ``DOI:<doi>`` string.
        :returns: :class:`SSPaper` or ``None`` if not found.
        """
        try:
            data = self._get(f"/paper/{paper_id}", {"fields": PAPER_FIELDS})
            return self._parse(data)
        except requests.HTTPError:
            return None

    def get_by_url(self, url: str) -> Optional[SSPaper]:
        """Resolve a paper URL (eLife, ACS, PubMed, etc.) via Semantic Scholar.

        :param url: Full paper URL, e.g. ``https://elifesciences.org/articles/93796``.
        :returns: :class:`SSPaper` or ``None`` if not resolvable.
        """
        try:
            data = self._get(f"/paper/URL:{url}", {"fields": PAPER_FIELDS})
            return self._parse(data)
        except requests.HTTPError:
            return None

    def get_citations(self, paper_id: str, limit: int = 50) -> List[SSPaper]:
        """Return papers that cite the given paper.

        :param paper_id: Semantic Scholar paper ID.
        :param limit: Maximum number of citing papers to return.
        :returns: List of :class:`SSPaper` objects.
        """
        try:
            data = self._get(
                f"/paper/{paper_id}/citations",
                {"fields": PAPER_FIELDS, "limit": limit},
            )
            return [
                p
                for item in data.get("data", [])
                if (p := self._parse(item.get("citingPaper") or {})) is not None
            ]
        except requests.HTTPError:
            return []

    def get_references(self, paper_id: str, limit: int = 50) -> List[SSPaper]:
        """Return papers referenced by the given paper.

        :param paper_id: Semantic Scholar paper ID.
        :param limit: Maximum number of references to return.
        :returns: List of :class:`SSPaper` objects.
        """
        try:
            data = self._get(
                f"/paper/{paper_id}/references",
                {"fields": PAPER_FIELDS, "limit": limit},
            )
            return [
                p
                for item in data.get("data", [])
                if (p := self._parse(item.get("citedPaper") or {})) is not None
            ]
        except requests.HTTPError:
            return []

    def search(
        self, query: str, max_results: int = 25, start: int = 0, **kwargs: object
    ) -> List[SearchItem]:
        """Search Semantic Scholar and return :class:`SearchItem` results.

        :param query: Free-text search query.
        :param max_results: Maximum results to return (capped at 100 by API).
        :param start: Zero-based offset for pagination.
        :returns: List of :class:`SearchItem` objects.
        """
        try:
            data = self._get(
                "/paper/search",
                {
                    "query": query,
                    "fields": PAPER_FIELDS,
                    "limit": min(max_results, 100),
                    "offset": start,
                },
            )
        except requests.HTTPError:
            return []

        items: List[SearchItem] = []
        for p in data.get("data", []):
            paper = self._parse(p)
            if paper is None:
                continue
            items.append(
                SearchItem(
                    title=paper.title,
                    url=f"https://www.semanticscholar.org/paper/{paper.paper_id}",
                    snippet=paper.abstract[:300] if paper.abstract else None,
                    item_id=paper.paper_id,
                    extra={
                        "doi": paper.doi,
                        "year": paper.year,
                        "embedding": paper.embedding,
                        "ss_paper_id": paper.paper_id,
                    },
                )
            )
        return items

    def iter_all(
        self,
        query: str,
        chunk_size: int = 100,
        limit: Optional[int] = None,
    ) -> Iterator[SearchItem]:
        """Iterate over all search results with automatic pagination.

        :param query: Free-text search query.
        :param chunk_size: Page size per request (max 100).
        :param limit: Optional total result cap.
        :returns: Iterator of :class:`SearchItem` objects.
        """
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

    def search_all(
        self, query: str, limit: Optional[int] = None
    ) -> List[SearchItem]:
        """Return all search results as a list (convenience wrapper).

        :param query: Free-text search query.
        :param limit: Optional total result cap.
        :returns: List of :class:`SearchItem` objects.
        """
        return list(self.iter_all(query, limit=limit))

    @staticmethod
    def _parse(data: dict) -> Optional[SSPaper]:
        """Parse a raw API response dict into an :class:`SSPaper`.

        :param data: Raw dict from the Semantic Scholar API.
        :returns: :class:`SSPaper` or ``None`` if the data is invalid.
        """
        if not data or not data.get("paperId"):
            return None
        ext = data.get("externalIds") or {}
        emb = data.get("embedding")
        return SSPaper(
            paper_id=data["paperId"],
            title=data.get("title") or "",
            abstract=data.get("abstract"),
            year=data.get("year"),
            authors=[a["name"] for a in data.get("authors", []) if a.get("name")],
            citation_count=data.get("citationCount", 0),
            doi=ext.get("DOI"),
            fields_of_study=data.get("fieldsOfStudy") or [],
            embedding=emb.get("vector") if emb else None,
        )
