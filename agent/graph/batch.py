"""Batch graph processor for building merged knowledge graphs from multiple seeds.

Processes a list of seed paper identifiers sequentially, building a graph for
each and merging them into a single unified :class:`KnowledgeGraph`.
"""

import json
from pathlib import Path
from typing import Callable, List, Optional, Union

from shared.logging import get_logger

from .builder import build_graph_from_seed
from .models import KnowledgeGraph

logger = get_logger(__name__)


async def build_batch_graph(
    seed_identifiers: List[str],
    is_url: bool = False,
    depth: int = 1,
    max_papers_per_seed: int = 20,
    output_path: Optional[Union[str, Path]] = None,
    progress_callback: Optional[Callable] = None,
) -> KnowledgeGraph:
    """Build a merged knowledge graph from multiple seed papers.

    Processes seeds sequentially (to respect Semantic Scholar rate limits),
    merging each mini-graph into a single unified graph. Saves a checkpoint
    JSON after each seed if ``output_path`` is provided.

    :param seed_identifiers: List of DOIs, URLs, or Semantic Scholar paper IDs.
    :param is_url: If ``True``, treat all identifiers as URLs.
    :param depth: Citation traversal depth per seed.
    :param max_papers_per_seed: Max papers to process per seed.
    :param output_path: If provided, save checkpoint JSON here after each seed.
    :param progress_callback: Optional async callable ``(current, total, graph)``
                              called after each seed is processed.
    :returns: A single merged :class:`KnowledgeGraph`.
    """
    merged: Optional[KnowledgeGraph] = None
    total = len(seed_identifiers)

    for i, seed_id in enumerate(seed_identifiers):
        logger.info(f"Batch: processing seed {i + 1}/{total}: {seed_id}")
        try:
            graph = await build_graph_from_seed(
                seed_identifier=seed_id,
                depth=depth,
                max_papers=max_papers_per_seed,
                is_url=is_url,
            )
            if merged is None:
                merged = graph
            else:
                merged.merge(graph)

            logger.info(
                f"Batch {i + 1}/{total}: "
                f"{len(merged.nodes)} nodes, {len(merged.edges)} edges"
            )

            if output_path:
                _save_checkpoint(merged, output_path)

            if progress_callback:
                await progress_callback(i + 1, total, merged)

        except Exception as e:
            logger.error(f"Batch: failed on seed {seed_id}: {e}")
            continue

    if merged is None:
        merged = KnowledgeGraph(title="Empty batch graph")

    merged.metadata["batch_seeds"] = seed_identifiers
    merged.metadata["batch_size"] = total
    return merged


def _save_checkpoint(graph: KnowledgeGraph, path: Union[str, Path]) -> None:
    """Save graph to disk as a JSON checkpoint (overwrites previous).

    :param graph: The graph to save.
    :param path: Destination file path.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(graph.to_export_dict(), f, indent=2)
    logger.debug(f"Checkpoint saved to {p}")


async def build_batch_graph_from_csv(
    csv_path: Union[str, Path],
    doi_column: str = "doi",
    url_column: Optional[str] = None,
    **kwargs,
) -> KnowledgeGraph:
    """Build a batch graph from seed identifiers loaded from a CSV file.

    The CSV must have at least one of: a DOI column or a URL column.

    :param csv_path: Path to the CSV file.
    :param doi_column: Column name containing DOIs (default ``"doi"``).
    :param url_column: Column name containing URLs (optional).
    :param kwargs: Additional keyword arguments forwarded to
                   :func:`build_batch_graph`.
    :returns: A merged :class:`KnowledgeGraph`.
    """
    import csv

    seeds: List[str] = []
    is_url = False

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if url_column and row.get(url_column):
                seeds.append(row[url_column])
                is_url = True
            elif row.get(doi_column):
                seeds.append(f"DOI:{row[doi_column]}")

    logger.info(f"Loaded {len(seeds)} seeds from {csv_path}")
    return await build_batch_graph(seeds, is_url=is_url, **kwargs)
