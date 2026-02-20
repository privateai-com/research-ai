# Phase 5: Graph Builder Orchestrator

## Goal

Create `agent/graph/builder.py` — the main orchestrator that takes a seed paper,
fetches its citation network via Semantic Scholar, runs the extractor on each paper,
and merges everything into a single `KnowledgeGraph`.

## New File: `agent/graph/builder.py`

```python
import asyncio
from typing import List, Optional
from loguru import logger
from .models import KnowledgeGraph
from .extractor import extract_graph_from_paper
from agent.browsing.manual.sources.semantic_scholar import SemanticScholarBrowser, SSPaper

async def build_graph_from_seed(
    seed_identifier: str,
    depth: int = 1,
    max_papers: int = 30,
    is_url: bool = False,
) -> KnowledgeGraph:
    """
    Build a knowledge graph starting from a seed paper.

    Args:
        seed_identifier: A Semantic Scholar paperId, DOI (prefix "DOI:"), or URL.
        depth: Citation traversal depth. depth=1 means seed + direct citations/references.
        max_papers: Maximum total papers to process (to control cost/time).
        is_url: If True, resolve seed_identifier as a URL first.

    Returns:
        A merged KnowledgeGraph.
    """
    browser = SemanticScholarBrowser()

    # ── Step 1: Resolve seed paper ───────────────────────────────────────────
    logger.info(f"Resolving seed paper: {seed_identifier}")
    if is_url:
        seed_paper = browser.get_by_url(seed_identifier)
    else:
        seed_paper = browser.get_by_id(seed_identifier)

    if seed_paper is None:
        raise ValueError(f"Could not resolve seed paper: {seed_identifier}")

    logger.info(f"Seed paper resolved: '{seed_paper.title}' ({seed_paper.paper_id})")

    # ── Step 2: Collect papers to process ───────────────────────────────────
    papers_to_process: List[SSPaper] = [seed_paper]
    seen_ids = {seed_paper.paper_id}

    if depth >= 1:
        refs = browser.get_references(seed_paper.paper_id, limit=50)
        cites = browser.get_citations(seed_paper.paper_id, limit=50)
        for p in refs + cites:
            if p and p.paper_id not in seen_ids:
                seen_ids.add(p.paper_id)
                papers_to_process.append(p)
            if len(papers_to_process) >= max_papers:
                break

    if depth >= 2:
        second_level: List[SSPaper] = []
        for p in papers_to_process[1:]:  # skip seed
            if len(papers_to_process) + len(second_level) >= max_papers:
                break
            refs2 = browser.get_references(p.paper_id, limit=20)
            for p2 in refs2:
                if p2 and p2.paper_id not in seen_ids:
                    seen_ids.add(p2.paper_id)
                    second_level.append(p2)
        papers_to_process.extend(second_level)

    papers_to_process = papers_to_process[:max_papers]
    logger.info(f"Processing {len(papers_to_process)} papers for graph construction")

    # ── Step 3: Extract mini-graphs concurrently ─────────────────────────────
    semaphore = asyncio.Semaphore(5)  # max 5 concurrent LLM calls

    async def _extract_one(paper: SSPaper) -> KnowledgeGraph:
        async with semaphore:
            return await extract_graph_from_paper(
                paper_id=paper.paper_id,
                title=paper.title,
                abstract=paper.abstract or "",
                doi=paper.doi,
                year=paper.year,
                authors=paper.authors,
            )

    mini_graphs = await asyncio.gather(*[_extract_one(p) for p in papers_to_process])

    # ── Step 4: Merge all mini-graphs ────────────────────────────────────────
    merged = mini_graphs[0]
    for g in mini_graphs[1:]:
        merged.merge(g)

    # ── Step 5: Add citation edges between papers ────────────────────────────
    _add_citation_edges(merged, papers_to_process, browser)

    merged.seed_paper_id = seed_paper.paper_id
    merged.title = f"Knowledge Graph: {seed_paper.title[:60]}"
    merged.metadata["total_papers"] = len(papers_to_process)
    merged.metadata["depth"] = depth

    logger.info(
        f"Graph built: {len(merged.nodes)} nodes, {len(merged.edges)} edges"
    )
    return merged


def _add_citation_edges(
    graph: KnowledgeGraph,
    papers: List[SSPaper],
    browser: SemanticScholarBrowser,
) -> None:
    """Add 'cites' edges between paper nodes that are already in the graph."""
    paper_id_to_node_id = {
        n.properties.get("ss_paper_id", ""): n.id
        for n in graph.nodes
        if n.type == "paper"
    }
    existing_edges = {(e.source, e.target, e.type) for e in graph.edges}

    for paper in papers:
        src_node_id = paper_id_to_node_id.get(paper.paper_id)
        if not src_node_id:
            continue
        # We already fetched references; re-use from paper metadata if stored
        # This avoids extra API calls — citation edges are best-effort
```

## Integration into `pipeline.py`

Add `build_graph: bool = False` to `PipelineTask`. At the end of `run_pipeline`:

```python
# pipeline.py — after make_decision_and_report(...)
graph: Optional[KnowledgeGraph] = None
if task.build_graph and task.seed_paper_url:
    from agent.graph.builder import build_graph_from_seed
    logger.info("Stage: graph builder -> knowledge graph")
    graph = await build_graph_from_seed(
        seed_identifier=task.seed_paper_url,
        depth=task.graph_depth,
        max_papers=task.graph_max_papers,
        is_url=True,
    )

return PipelineOutput(
    ...existing fields...,
    graph=graph,
)
```

## `PipelineTask` additions (`models.py`)

```python
build_graph: bool = False
seed_paper_url: Optional[str] = None   # URL or DOI to seed the graph
graph_depth: int = 1                   # citation traversal depth
graph_max_papers: int = 30             # cap to control cost
```

## `PipelineOutput` additions (`models.py`)

```python
from agent.graph.models import KnowledgeGraph
graph: Optional[KnowledgeGraph] = None
```

## Performance Notes

- `depth=1`, `max_papers=30`: ~30 Semantic Scholar API calls + 30 LLM calls ≈ 30-60 seconds
- `depth=2`, `max_papers=100`: ~150 API calls + 100 LLM calls ≈ 3-5 minutes
- Semaphore limits concurrent LLM calls to 5 to avoid rate limits
- Semantic Scholar rate limit: 1 req/s authenticated → 30 papers takes ~30s minimum

## New `agent/graph/__init__.py`

```python
from .models import KnowledgeGraph, GraphNode, GraphEdge
from .builder import build_graph_from_seed
from .extractor import extract_graph_from_paper

__all__ = [
    "KnowledgeGraph", "GraphNode", "GraphEdge",
    "build_graph_from_seed", "extract_graph_from_paper",
]
```
