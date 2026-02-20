"""FastAPI application exposing the research pipeline as a REST API.

This module provides a thin HTTP layer over the internal agent pipeline in
:mod:`agent.pipeline`. It defines request/response models and endpoints that
delegate execution to :func:`agent.pipeline.pipeline.run_pipeline`.

- ``GET /healthz``: liveness probe
- ``POST /v1/run``: run the end-to-end research pipeline for a free-text task
- ``POST /v1/graph``: build a knowledge graph from a seed paper URL or ID
- ``POST /v1/batch``: build a merged graph from multiple seed papers
- ``GET /v1/graph/{graph_id}``: retrieve a stored graph by ID
- ``GET /v1/graphs``: list stored graphs

See also: :mod:`agent.pipeline.models`, :mod:`agent.pipeline.pipeline`.
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.pipeline.models import (
    AnalysisResult,
    PipelineOutput,
    PipelineTask,
    ScoredAnalysis,
)
import agent.pipeline.pipeline as pipeline_mod


class PipelineTaskRequest(BaseModel):
    """Request schema for running the research pipeline.

    This mirrors :class:`agent.pipeline.models.PipelineTask` and is validated
    before being converted to the internal model.

    :ivar query: Free-text task description (e.g. "AI for medical imaging").
    :ivar categories: Optional arXiv categories (e.g. ["cs.AI", "cs.CV"]).
    :ivar max_queries: Upper bound on generated search queries (default 5).
    :ivar bm25_top_k: Number of top-ranked candidates to keep (default 20).
    :ivar max_analyze: Maximum number of candidates to analyze (default 10).
    :ivar min_relevance: Minimum relevance threshold in [0, 100] (default 50.0).
    :ivar use_semantic_rerank: If True, rerank with embedding cosine similarity.
    :ivar build_graph: If True, build a knowledge graph from seed_paper_url.
    :ivar seed_paper_url: URL or DOI of the seed paper for graph construction.
    :ivar graph_depth: Citation traversal depth (1 or 2).
    :ivar graph_max_papers: Max papers to process for graph (1-100).
    """

    query: str = Field(min_length=1, description="Free-text task description")
    categories: Optional[List[str]] = Field(
        default=None, description="Optional arXiv categories"
    )
    max_queries: int = Field(default=5, ge=1, le=20)
    bm25_top_k: int = Field(default=20, ge=5, le=100)
    max_analyze: int = Field(default=10, ge=1, le=50)
    min_relevance: float = Field(default=50.0, ge=0.0, le=100.0)
    queries: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional user-suggested queries. The agent will decide sources per query."
        ),
    )
    use_semantic_rerank: bool = Field(default=False)
    build_graph: bool = Field(default=False)
    seed_paper_url: Optional[str] = Field(default=None)
    graph_depth: int = Field(default=1, ge=1, le=2)
    graph_max_papers: int = Field(default=30, ge=1, le=100)


class PaperSummary(BaseModel):
    """Compact representation of an analyzed paper for API responses.

    This is a projection of :class:`agent.pipeline.models.AnalysisResult` used
    by the public API to keep responses concise.

    :ivar arxiv_id: Stable arXiv identifier (e.g. "2301.01234").
    :ivar title: Paper title.
    :ivar relevance: Relevance score in [0, 100].
    :ivar summary: Short summary tailored to the user task.
    :ivar link: Preferred URL (abstract or PDF).
    """

    arxiv_id: str
    title: str
    relevance: float
    summary: str
    link: Optional[str]


class RunResponse(BaseModel):
    """Response schema returned by the main pipeline endpoint.

    Aggregates a compact view of :class:`agent.pipeline.models.PipelineOutput`.

    :ivar task: Echo of the validated request payload.
    :ivar generated_queries: Queries produced by the strategy stage.
    :ivar analyzed: List of compact paper summaries.
    :ivar selected: Short list of selected items recommended for reporting.
    :ivar should_notify: Whether notifying the user is recommended.
    :ivar report_text: Plain-text report with findings, when available.
    :ivar graph: Knowledge graph export dict when build_graph=True, else None.
    """

    task: PipelineTaskRequest
    generated_queries: List[str]
    analyzed: List[PaperSummary]
    selected: List[PaperSummary]
    should_notify: bool
    report_text: Optional[str]
    graph: Optional[Dict[str, Any]] = None


class GraphRequest(BaseModel):
    """Request schema for building a knowledge graph from a seed paper.

    :ivar seed_paper_url: Full URL of the seed paper (eLife, ACS, PubMed, etc.).
    :ivar seed_paper_id: Semantic Scholar paper ID or ``DOI:<doi>`` string.
    :ivar depth: Citation traversal depth (1 or 2, default 1).
    :ivar max_papers: Maximum papers to process (default 30).
    """

    seed_paper_url: Optional[str] = None
    seed_paper_id: Optional[str] = None
    depth: int = Field(default=1, ge=1, le=2)
    max_papers: int = Field(default=30, ge=1, le=100)


class GraphResponse(BaseModel):
    """Response schema for a knowledge graph.

    :ivar graph_id: Stable UUID for this graph.
    :ivar seed_paper_id: Semantic Scholar paper ID of the seed.
    :ivar title: Human-readable graph title.
    :ivar node_count: Number of nodes.
    :ivar edge_count: Number of edges.
    :ivar graph: Full graph export dict with ``nodes`` and ``edges`` arrays.
    """

    graph_id: str
    seed_paper_id: Optional[str]
    title: str
    node_count: int
    edge_count: int
    graph: Dict[str, Any]


class BatchRequest(BaseModel):
    """Request schema for building a merged graph from multiple seed papers.

    :ivar seed_identifiers: List of DOIs, URLs, or Semantic Scholar paper IDs.
    :ivar is_url: If True, treat all identifiers as URLs.
    :ivar depth: Citation traversal depth per seed (default 1).
    :ivar max_papers_per_seed: Max papers per seed (default 20).
    """

    seed_identifiers: List[str]
    is_url: bool = False
    depth: int = Field(default=1, ge=1, le=2)
    max_papers_per_seed: int = Field(default=20, ge=1, le=50)


class BatchResponse(BaseModel):
    """Response schema for a batch knowledge graph build.

    :ivar graph_id: Stable UUID for the merged graph.
    :ivar seed_count: Number of seed papers processed.
    :ivar node_count: Number of nodes in the merged graph.
    :ivar edge_count: Number of edges in the merged graph.
    :ivar graph: Full graph export dict.
    """

    graph_id: str
    seed_count: int
    node_count: int
    edge_count: int
    graph: Dict[str, Any]


def _to_paper_summary(item: AnalysisResult) -> PaperSummary:
    """Convert an analysis result into a public paper summary.

    :param item: A single :class:`agent.pipeline.models.AnalysisResult` produced
                 by the analysis stage.
    :returns: A :class:`PaperSummary` with essential, serializable fields.
    """

    link = item.candidate.abs_url or item.candidate.pdf_url
    return PaperSummary(
        arxiv_id=item.candidate.arxiv_id,
        title=item.candidate.title,
        relevance=float(item.relevance),
        summary=item.summary,
        link=link,
    )


def _selected_to_summary(items: List[ScoredAnalysis]) -> List[PaperSummary]:
    """Convert selected scored analyses into compact summaries.

    :param items: Items returned by
                  :func:`agent.pipeline.decision.select_top`.
    :returns: List of :class:`PaperSummary` items.
    """

    summaries: List[PaperSummary] = []
    for s in items:
        summaries.append(_to_paper_summary(s.result))
    return summaries


app = FastAPI(title="Research AI API", version="0.1.0")


@app.get("/healthz")
async def health() -> dict[str, str]:
    """Liveness probe endpoint.

    :returns: A constant payload ``{"status": "ok"}`` when the service is
              alive.
    """

    return {"status": "ok"}


@app.post("/v1/run", response_model=RunResponse)
async def run(task: PipelineTaskRequest) -> RunResponse:
    """Run the research pipeline and return a compact response.

    The request is validated and transformed to
    :class:`agent.pipeline.models.PipelineTask`, then executed by
    :func:`agent.pipeline.pipeline.run_pipeline`.

    :param task: Validated request body describing the user's research task.
    :returns: A :class:`RunResponse` with generated queries, analyzed items,
              selection, decision flag, and optional report text.
    :raises fastapi.HTTPException: ``422 Unprocessable Entity`` if validation
            fails.
    """

    try:
        pipeline_task = PipelineTask.model_validate(task.model_dump())
    except Exception as error:  # pragma: no cover - pydantic will give details
        raise HTTPException(status_code=422, detail=str(error))

    output: PipelineOutput = await pipeline_mod.run_pipeline(pipeline_task)

    analyzed_summaries = [_to_paper_summary(a) for a in output.analyzed]
    selected_summaries = _selected_to_summary(output.selected)

    graph_export = output.graph.to_export_dict() if output.graph else None

    response = RunResponse(
        task=task,
        generated_queries=output.generated_queries,
        analyzed=analyzed_summaries,
        selected=selected_summaries,
        should_notify=output.should_notify,
        report_text=output.report_text,
        graph=graph_export,
    )
    return response


@app.post("/v1/graph", response_model=GraphResponse)
async def generate_graph(req: GraphRequest) -> GraphResponse:
    """Build a knowledge graph from a seed paper URL or Semantic Scholar ID.

    :param req: Graph request with seed paper identifier and traversal options.
    :returns: A :class:`GraphResponse` with the full graph export.
    :raises fastapi.HTTPException: 422 if neither URL nor ID is provided,
            404 if the seed paper cannot be resolved, 500 on build failure.
    """
    from agent.graph.builder import build_graph_from_seed

    if not req.seed_paper_url and not req.seed_paper_id:
        raise HTTPException(
            status_code=422, detail="Provide seed_paper_url or seed_paper_id"
        )

    is_url = bool(req.seed_paper_url)
    identifier = req.seed_paper_url or req.seed_paper_id

    try:
        graph = await build_graph_from_seed(
            seed_identifier=identifier,
            depth=req.depth,
            max_papers=req.max_papers,
            is_url=is_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph build failed: {e}")

    export = graph.to_export_dict()
    return GraphResponse(
        graph_id=graph.id,
        seed_paper_id=graph.seed_paper_id,
        title=graph.title,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        graph=export,
    )


@app.post("/v1/batch", response_model=BatchResponse)
async def batch_graph(req: BatchRequest) -> BatchResponse:
    """Build a merged knowledge graph from multiple seed papers.

    :param req: Batch request with list of seed identifiers.
    :returns: A :class:`BatchResponse` with the merged graph export.
    :raises fastapi.HTTPException: 422 if seed list is empty, 500 on failure.
    """
    from agent.graph.batch import build_batch_graph

    if not req.seed_identifiers:
        raise HTTPException(
            status_code=422, detail="seed_identifiers must not be empty"
        )

    try:
        graph = await build_batch_graph(
            seed_identifiers=req.seed_identifiers,
            is_url=req.is_url,
            depth=req.depth,
            max_papers_per_seed=req.max_papers_per_seed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch build failed: {e}")

    export = graph.to_export_dict()
    return BatchResponse(
        graph_id=graph.id,
        seed_count=len(req.seed_identifiers),
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        graph=export,
    )
