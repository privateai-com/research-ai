"""Embedding-based semantic reranking for pipeline candidates.

Replaces or augments BM25 ranking by computing cosine similarity between
the query embedding and each candidate's text embedding using OpenAI's
``text-embedding-3-small`` model.
"""

import math
import os
from typing import List, Optional, Tuple

from shared.logging import get_logger
from .models import PaperCandidate

logger = get_logger(__name__)


def _cosine(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two equal-length vectors.

    :param a: First vector.
    :param b: Second vector.
    :returns: Cosine similarity in [-1, 1].
    """
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _get_openai_embedding(
    text: str, model: str = "text-embedding-3-small"
) -> Optional[List[float]]:
    """Embed a text string using OpenAI's embedding API.

    :param text: Text to embed (truncated to 8000 chars).
    :param model: OpenAI embedding model name.
    :returns: Embedding vector or ``None`` if the API call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; skipping semantic embedding")
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.embeddings.create(input=text[:8000], model=model)
        return resp.data[0].embedding
    except Exception as e:
        logger.warning(f"OpenAI embedding failed: {e}")
        return None


def semantic_rerank(
    query: str,
    candidates: List[PaperCandidate],
    top_k: int = 20,
) -> List[PaperCandidate]:
    """Rerank candidates by cosine similarity between query and paper embeddings.

    Both the query and each candidate's ``title + abstract`` are embedded using
    ``text-embedding-3-small``. If embedding fails (no API key, rate limit, etc.)
    the original candidate list is returned unchanged.

    :param query: The user's research query or conclusion text.
    :param candidates: List of :class:`PaperCandidate` objects to rerank.
    :param top_k: Number of top candidates to return after reranking.
    :returns: Top-k candidates sorted by descending cosine similarity.
    """
    query_emb = _get_openai_embedding(query)
    if query_emb is None:
        logger.warning("Could not embed query; returning candidates unchanged")
        return candidates[:top_k]

    scored: List[Tuple[float, PaperCandidate]] = []
    for c in candidates:
        paper_text = f"{c.title}. {c.summary}"
        paper_emb = _get_openai_embedding(paper_text)
        if paper_emb is None:
            scored.append((0.0, c))
            continue
        sim = _cosine(query_emb, paper_emb)
        scored.append((sim, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    logger.info(
        f"Semantic rerank: top score={scored[0][0]:.3f} "
        f"bottom score={scored[-1][0]:.3f} (n={len(scored)})"
        if scored
        else "Semantic rerank: no candidates"
    )
    return [c for _, c in scored[:top_k]]
