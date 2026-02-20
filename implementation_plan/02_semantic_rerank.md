# Phase 2: Embedding-Based Semantic Reranking

## Goal

Replace (or augment) BM25 ranking with embedding-based cosine similarity so the pipeline
can find papers that reach **similar conclusions** even when they use different terminology.
This is the core capability the client needs for cross-domain discovery.

## New File

**`agent/pipeline/semantic_rerank.py`**

```python
import os
import math
from typing import List, Optional, Tuple
from loguru import logger
from .models import PaperCandidate

def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

def _get_openai_embedding(text: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; skipping embedding")
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
    use_specter: bool = True,
) -> List[PaperCandidate]:
    """
    Rerank candidates by cosine similarity between query embedding and paper embeddings.

    If a candidate already has a SPECTER2 embedding stored in candidate.extra['embedding'],
    it is used directly (free, no API call). Otherwise, OpenAI text-embedding-3-small is
    used to embed the title+abstract.

    Args:
        query: The user's research query or conclusion text.
        candidates: List of PaperCandidate objects.
        top_k: Number of top candidates to return.
        use_specter: Prefer SPECTER2 embeddings from Semantic Scholar when available.

    Returns:
        Top-k candidates sorted by descending cosine similarity.
    """
    query_emb = _get_openai_embedding(query)
    if query_emb is None:
        logger.warning("Could not embed query; returning candidates unchanged")
        return candidates[:top_k]

    scored: List[Tuple[float, PaperCandidate]] = []
    for c in candidates:
        # Try SPECTER2 first (stored in extra by SemanticScholarBrowser)
        specter_emb = None
        if use_specter and c.extra and isinstance(c.extra.get("embedding"), list):
            specter_emb = c.extra["embedding"]

        if specter_emb:
            # SPECTER2 is 768-dim; query_emb is 1536-dim — need same space.
            # Use OpenAI embedding for the paper text instead.
            paper_text = f"{c.title}. {c.summary}"
            paper_emb = _get_openai_embedding(paper_text)
        else:
            paper_text = f"{c.title}. {c.summary}"
            paper_emb = _get_openai_embedding(paper_text)

        if paper_emb is None:
            scored.append((0.0, c))
            continue

        sim = _cosine(query_emb, paper_emb)
        scored.append((sim, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]
```

## Integration into `pipeline.py`

Add an optional `use_semantic_rerank: bool = False` field to `PipelineTask` (in `models.py`),
then in `pipeline.py` after the BM25 ranking stage:

```python
# pipeline.py — after rank_candidates(...)
if task.use_semantic_rerank:
    from agent.pipeline.semantic_rerank import semantic_rerank
    logger.info("Stage: semantic rerank -> embedding cosine similarity")
    ranked = semantic_rerank(
        query=task.query,
        candidates=ranked,
        top_k=task.bm25_top_k,
    )
    logger.info(f"Semantic rerank kept top {len(ranked)} candidates")
```

## `PipelineTask` model additions (`models.py`)

```python
use_semantic_rerank: bool = False
# Passed through from API/bot; defaults False so existing tasks are unaffected
```

## Cost Estimate

- `text-embedding-3-small`: $0.02 / 1M tokens
- A typical abstract is ~200 tokens
- 50 candidates + 1 query = 51 embeddings × 200 tokens ≈ 10,200 tokens ≈ **$0.0002 per run**
- Effectively free at research scale

## Why Not Use SPECTER2 Directly for Both?

SPECTER2 (768-dim) and OpenAI embeddings (1536-dim) live in different vector spaces —
you cannot compute cosine similarity across them. Two options:
1. **Embed everything with OpenAI** (chosen — simpler, consistent)
2. **Embed query with a local SPECTER2 model** (future enhancement, requires `transformers`)
