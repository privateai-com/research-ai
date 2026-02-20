# Phase 6: Batch Processing for Cryo Database

## Goal

Create `agent/graph/batch.py` — a batch processor that takes a list of seed paper
identifiers (DOIs, URLs, or Semantic Scholar IDs) and builds a single merged
knowledge graph representing the entire cryo database.

## New File: `agent/graph/batch.py`

```python
import asyncio
import json
from pathlib import Path
from typing import List, Optional, Union
from loguru import logger
from .models import KnowledgeGraph
from .builder import build_graph_from_seed

async def build_batch_graph(
    seed_identifiers: List[str],
    is_url: bool = False,
    depth: int = 1,
    max_papers_per_seed: int = 20,
    output_path: Optional[Union[str, Path]] = None,
    progress_callback=None,
) -> KnowledgeGraph:
    """
    Build a merged knowledge graph from multiple seed papers.

    Args:
        seed_identifiers: List of DOIs, URLs, or Semantic Scholar paper IDs.
        is_url: If True, treat all identifiers as URLs.
        depth: Citation traversal depth per seed.
        max_papers_per_seed: Max papers to process per seed (controls cost).
        output_path: If provided, save the merged graph JSON here after each seed.
        progress_callback: Optional async callable(current, total, graph) for progress.

    Returns:
        A single merged KnowledgeGraph containing all seeds and their networks.
    """
    merged: Optional[KnowledgeGraph] = None
    total = len(seed_identifiers)

    for i, seed_id in enumerate(seed_identifiers):
        logger.info(f"Batch: processing seed {i+1}/{total}: {seed_id}")
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
                f"Batch progress {i+1}/{total}: "
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
    """Save graph to disk as a checkpoint (overwrites previous)."""
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
    """
    Convenience wrapper: load seed identifiers from a CSV file.

    The CSV must have at least one of: a DOI column or a URL column.
    Example CSV:
        doi,title
        10.7554/eLife.93796,Organ chip paper
        10.1021/acsnano.4c02012,Nanoparticle paper
    """
    import csv
    seeds = []
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
```

## CLI Entry Point

Add to `pyproject.toml` scripts or create `scripts/build_cryo_graph.py`:

```python
#!/usr/bin/env python3
"""
CLI: Build a knowledge graph from a CSV of cryo papers.

Usage:
    python scripts/build_cryo_graph.py \
        --input cryo_database.csv \
        --output cryo_graph.json \
        --depth 1 \
        --max-papers 20
"""
import asyncio
import argparse
from agent.graph.batch import build_batch_graph_from_csv

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CSV file with DOIs")
    parser.add_argument("--output", default="cryo_graph.json")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--max-papers", type=int, default=20)
    parser.add_argument("--doi-column", default="doi")
    args = parser.parse_args()

    graph = asyncio.run(build_batch_graph_from_csv(
        csv_path=args.input,
        doi_column=args.doi_column,
        depth=args.depth,
        max_papers_per_seed=args.max_papers,
        output_path=args.output,
    ))
    print(f"Done: {len(graph.nodes)} nodes, {len(graph.edges)} edges → {args.output}")

if __name__ == "__main__":
    main()
```

## Cryo Database Format Requirements

The client needs to provide the cryo database in one of these formats:

| Format | Required Columns | Notes |
|---|---|---|
| CSV | `doi` | Most common, easiest |
| CSV | `url` | For papers without DOIs |
| JSON | `[{"doi": "...", "title": "..."}]` | Array of objects |

## Cost & Time Estimate for 1,000 Papers

| Parameter | Value |
|---|---|
| Seeds | 1,000 |
| Papers per seed (depth=1) | 20 |
| Total papers processed | ~5,000 (after dedup) |
| LLM calls | ~5,000 × $0.001 = **$5** |
| Embedding calls | ~5,000 × $0.0002 = **$1** |
| SS API calls | ~20,000 (rate limited to 1/s = ~6 hours) |
| **Total cost** | **~$6** |
| **Total time** | **~6-8 hours** (SS rate limit bound) |

For faster processing, request a higher Semantic Scholar API rate limit tier.
