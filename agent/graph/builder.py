"""Knowledge graph builder orchestrator.

Takes a seed paper, fetches its citation network via Semantic Scholar,
runs the LLM extractor on each paper, and merges everything into a single
:class:`KnowledgeGraph`.
"""

import asyncio
from typing import List, Optional

from shared.logging import get_logger

from .extractor import extract_graph_from_paper
from .models import KnowledgeGraph

logger = get_logger(__name__)


async def build_graph_from_seed(
    seed_identifier: str,
    depth: int = 1,
    max_papers: int = 30,
    is_url: bool = False,
) -> KnowledgeGraph:
    """Build a knowledge graph starting from a seed paper.

    Fetches the seed paper from Semantic Scholar, traverses its citation and
    reference network up to ``depth`` hops, runs the LLM extractor on each
    paper concurrently, and merges all mini-graphs into one.

    :param seed_identifier: A Semantic Scholar paper ID, ``DOI:<doi>``, or URL.
    :param depth: Citation traversal depth (1 = seed + direct neighbours).
    :param max_papers: Maximum total papers to process (controls cost/time).
    :param is_url: If ``True``, resolve ``seed_identifier`` as a URL.
    :returns: A merged :class:`KnowledgeGraph`.
    :raises ValueError: If the seed paper cannot be resolved.
    """
    from agent.browsing.manual.sources.semantic_scholar import (
        SemanticScholarBrowser,
        SSPaper,
    )

    browser = SemanticScholarBrowser()

    # ── Step 1: Resolve seed paper ───────────────────────────────────────────
    logger.info(f"Resolving seed paper: {seed_identifier}")
    if is_url:
        seed_paper = browser.get_by_url(seed_identifier)
    else:
        seed_paper = browser.get_by_id(seed_identifier)

    if seed_paper is None:
        raise ValueError(f"Could not resolve seed paper: {seed_identifier}")

    logger.info(f"Seed resolved: '{seed_paper.title}' ({seed_paper.paper_id})")

    # ── Step 2: Collect papers to process ────────────────────────────────────
    papers_to_process: List[SSPaper] = [seed_paper]
    seen_ids: set[str] = {seed_paper.paper_id}

    if depth >= 1:
        refs = browser.get_references(seed_paper.paper_id, limit=50)
        cites = browser.get_citations(seed_paper.paper_id, limit=50)
        for p in refs + cites:
            if p and p.paper_id not in seen_ids:
                seen_ids.add(p.paper_id)
                papers_to_process.append(p)
            if len(papers_to_process) >= max_papers:
                break

    if depth >= 2 and len(papers_to_process) < max_papers:
        second_level: List[SSPaper] = []
        for p in papers_to_process[1:]:
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

    # ── Step 3: Extract mini-graphs concurrently ──────────────────────────────
    semaphore = asyncio.Semaphore(5)

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

    mini_graphs = await asyncio.gather(
        *[_extract_one(p) for p in papers_to_process]
    )

    # ── Step 4: Merge all mini-graphs ─────────────────────────────────────────
    merged = mini_graphs[0]
    for g in mini_graphs[1:]:
        merged.merge(g)

    merged.seed_paper_id = seed_paper.paper_id
    merged.title = f"Knowledge Graph: {seed_paper.title[:60]}"
    merged.metadata["total_papers"] = len(papers_to_process)
    merged.metadata["depth"] = depth
    merged.metadata["seed_url"] = seed_identifier if is_url else None

    logger.info(
        f"Graph built: {len(merged.nodes)} nodes, {len(merged.edges)} edges"
    )
    return merged
