# Phase 7: FastAPI New Endpoints

## Goal

Extend `api/app.py` with new endpoints for graph generation, graph retrieval, and batch
processing. All new endpoints are additive — existing `/v1/run` is unchanged.

## Updated `api/app.py` additions

### New Pydantic request/response models

```python
# ── Graph generation ─────────────────────────────────────────────────────────

class GraphRequest(BaseModel):
    seed_paper_url: Optional[str] = None    # URL like https://elifesciences.org/articles/93796
    seed_paper_id: Optional[str] = None     # Semantic Scholar ID or DOI:10.xxx
    depth: int = Field(default=1, ge=1, le=2)
    max_papers: int = Field(default=30, ge=1, le=100)

class GraphResponse(BaseModel):
    graph_id: str
    seed_paper_id: Optional[str]
    title: str
    node_count: int
    edge_count: int
    graph: dict  # full KnowledgeGraph export dict

# ── Batch processing ─────────────────────────────────────────────────────────

class BatchRequest(BaseModel):
    seed_identifiers: List[str]             # list of DOIs, URLs, or SS paper IDs
    is_url: bool = False
    depth: int = Field(default=1, ge=1, le=2)
    max_papers_per_seed: int = Field(default=20, ge=1, le=50)

class BatchResponse(BaseModel):
    graph_id: str
    seed_count: int
    node_count: int
    edge_count: int
    graph: dict

# ── Updated RunRequest (additive fields) ─────────────────────────────────────

class PipelineTaskRequest(BaseModel):
    # ... existing fields unchanged ...
    use_semantic_rerank: bool = False       # NEW
    build_graph: bool = False               # NEW
    seed_paper_url: Optional[str] = None    # NEW
    graph_depth: int = 1                    # NEW
    graph_max_papers: int = 30              # NEW
```

### New endpoints

```python
@app.post("/v1/graph", response_model=GraphResponse)
async def generate_graph(req: GraphRequest) -> GraphResponse:
    """
    Generate a knowledge graph from a seed paper URL or Semantic Scholar ID.

    Example:
        POST /v1/graph
        {"seed_paper_url": "https://elifesciences.org/articles/93796", "depth": 1}
    """
    from agent.graph.builder import build_graph_from_seed

    if not req.seed_paper_url and not req.seed_paper_id:
        raise HTTPException(status_code=422, detail="Provide seed_paper_url or seed_paper_id")

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
    """
    Build a merged knowledge graph from multiple seed papers.

    Example:
        POST /v1/batch
        {"seed_identifiers": ["DOI:10.7554/eLife.93796", "DOI:10.1021/acsnano.4c02012"]}
    """
    from agent.graph.batch import build_batch_graph

    if not req.seed_identifiers:
        raise HTTPException(status_code=422, detail="seed_identifiers must not be empty")

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


@app.get("/v1/graph/{graph_id}", response_model=GraphResponse)
async def get_graph(graph_id: str) -> GraphResponse:
    """Retrieve a previously generated graph from the database."""
    from shared.database.operations import get_graph_record  # to be implemented
    record = await get_graph_record(graph_id)
    if not record:
        raise HTTPException(status_code=404, detail="Graph not found")
    import json
    export = json.loads(record.graph_json)
    return GraphResponse(
        graph_id=record.id,
        seed_paper_id=record.seed_paper_id,
        title=record.title,
        node_count=record.node_count,
        edge_count=record.edge_count,
        graph=export,
    )


@app.get("/v1/graphs", response_model=List[GraphResponse])
async def list_graphs(user_id: Optional[int] = None, limit: int = 20) -> List[GraphResponse]:
    """List all graphs, optionally filtered by user_id."""
    from shared.database.operations import list_graph_records  # to be implemented
    import json
    records = await list_graph_records(user_id=user_id, limit=limit)
    return [
        GraphResponse(
            graph_id=r.id,
            seed_paper_id=r.seed_paper_id,
            title=r.title,
            node_count=r.node_count,
            edge_count=r.edge_count,
            graph=json.loads(r.graph_json),
        )
        for r in records
    ]
```

## DB Operations to Add (`shared/database/operations.py` or new file)

```python
async def save_graph_record(graph: KnowledgeGraph, user_id: Optional[int] = None, user_task_id: Optional[int] = None) -> KnowledgeGraphRecord:
    import json
    from shared.database.models import KnowledgeGraphRecord
    record = KnowledgeGraphRecord(
        id=graph.id,
        user_id=user_id,
        user_task_id=user_task_id,
        seed_paper_id=graph.seed_paper_id,
        title=graph.title,
        graph_json=json.dumps(graph.to_export_dict()),
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
    )
    async with get_session() as session:
        session.add(record)
        await session.commit()
    return record

async def get_graph_record(graph_id: str) -> Optional[KnowledgeGraphRecord]:
    async with get_session() as session:
        return await session.get(KnowledgeGraphRecord, graph_id)

async def list_graph_records(user_id: Optional[int] = None, limit: int = 20) -> List[KnowledgeGraphRecord]:
    from sqlalchemy import select
    async with get_session() as session:
        q = select(KnowledgeGraphRecord).order_by(KnowledgeGraphRecord.created_at.desc()).limit(limit)
        if user_id:
            q = q.where(KnowledgeGraphRecord.user_id == user_id)
        result = await session.execute(q)
        return list(result.scalars().all())
```

## Updated `/v1/run` response

Add `graph` field to `RunResponse`:

```python
class RunResponse(BaseModel):
    # ... existing fields ...
    graph: Optional[dict] = None  # populated when build_graph=True
```

And in the `run` endpoint handler:

```python
response = RunResponse(
    ...existing...,
    graph=output.graph.to_export_dict() if output.graph else None,
)
```
