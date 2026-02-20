# Phase 12: Backend Bridge (research-agent-front/src/backend)

## Architecture Context

`src/backend/` is a FastAPI app that:
- Authenticates users via Telegram OAuth
- Stores `Research` and `Article` records in PostgreSQL
- Calls `research-ai` pipeline (currently via `ResearchService` using OpenAI directly)

For knowledge graphs, the backend bridge needs to:
1. Accept graph requests from the frontend/bot
2. Forward them to the `research-ai` API (`POST /v1/graph`, `POST /v1/batch`)
3. Store graph metadata in its own DB for listing/retrieval per user
4. Stream status back to the frontend via polling

The `research-ai` API URL is a new env var: `RESEARCH_AI_API_URL`.

---

## 1. New DB Model (`src/backend/app/models.py`)

Add alongside existing `Research` model:

```python
class KnowledgeGraph(Base):
    __tablename__ = "knowledge_graphs"

    id = Column(String, primary_key=True, index=True)          # UUID from research-ai
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String, nullable=False, default="")
    seed_paper_url = Column(String, nullable=True)
    seed_paper_id = Column(String, nullable=True)
    depth = Column(Integer, default=1)
    status = Column(String, default="pending")                  # pending|processing|completed|failed
    node_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)
    graph_json = Column(Text, nullable=True)                    # full JSON, populated on completion
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="graphs")
```

Add to `User` model:
```python
graphs = relationship("KnowledgeGraph", back_populates="user", cascade="all, delete-orphan")
```

---

## 2. New Pydantic Schemas (`src/backend/app/schemas.py`)

```python
class GraphRequest(BaseModel):
    seed_paper_url: Optional[str] = None
    seed_paper_id: Optional[str] = None
    depth: int = Field(default=1, ge=1, le=2)
    max_papers: int = Field(default=30, ge=1, le=100)

class GraphListItem(BaseModel):
    id: str
    title: str
    seed_paper_url: Optional[str]
    seed_paper_id: Optional[str]
    node_count: int
    edge_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class GraphDetail(GraphListItem):
    graph_json: Optional[str]   # raw JSON string; frontend parses it
    depth: int
    error_message: Optional[str]
```

---

## 3. Graph Service (`src/backend/app/graph_service.py`)

New file — handles async calls to `research-ai` API and DB persistence.

```python
import httpx
import asyncio
import json
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import KnowledgeGraph, User
from app.config import settings

RESEARCH_AI_URL = os.getenv("RESEARCH_AI_API_URL", "http://localhost:8001")


class GraphService:

    async def create_graph(
        self,
        db: AsyncSession,
        user: User,
        seed_paper_url: str | None,
        seed_paper_id: str | None,
        depth: int = 1,
        max_papers: int = 30,
    ) -> KnowledgeGraph:
        """
        Create a graph record immediately (status=processing), then kick off
        background task to call research-ai and update the record.
        """
        graph_id = str(uuid.uuid4())
        record = KnowledgeGraph(
            id=graph_id,
            user_id=user.id,
            title=f"Graph: {seed_paper_url or seed_paper_id or 'Unknown'}",
            seed_paper_url=seed_paper_url,
            seed_paper_id=seed_paper_id,
            depth=depth,
            status="processing",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        # Fire and forget — background task updates the record
        asyncio.create_task(
            self._build_graph_background(graph_id, seed_paper_url, seed_paper_id, depth, max_papers)
        )
        return record

    async def _build_graph_background(
        self,
        graph_id: str,
        seed_paper_url: str | None,
        seed_paper_id: str | None,
        depth: int,
        max_papers: int,
    ) -> None:
        """Call research-ai /v1/graph and update the DB record with the result."""
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            try:
                payload = {
                    "seed_paper_url": seed_paper_url,
                    "seed_paper_id": seed_paper_id,
                    "depth": depth,
                    "max_papers": max_papers,
                }
                async with httpx.AsyncClient(timeout=300) as client:
                    resp = await client.post(
                        f"{RESEARCH_AI_URL}/v1/graph",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                record = await db.get(KnowledgeGraph, graph_id)
                if record:
                    record.status = "completed"
                    record.title = data.get("title", record.title)
                    record.node_count = data.get("node_count", 0)
                    record.edge_count = data.get("edge_count", 0)
                    record.graph_json = json.dumps(data.get("graph", {}))
                    # Use the research-ai graph ID as our canonical ID
                    # (keep our own ID for user-scoped lookups)
                    await db.commit()

            except Exception as e:
                record = await db.get(KnowledgeGraph, graph_id)
                if record:
                    record.status = "failed"
                    record.error_message = str(e)
                    await db.commit()

    async def get_graphs(self, db: AsyncSession, user_id: int) -> list[KnowledgeGraph]:
        result = await db.execute(
            select(KnowledgeGraph)
            .where(KnowledgeGraph.user_id == user_id)
            .order_by(KnowledgeGraph.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_graph(self, db: AsyncSession, graph_id: str, user_id: int) -> KnowledgeGraph | None:
        result = await db.execute(
            select(KnowledgeGraph).where(
                KnowledgeGraph.id == graph_id,
                KnowledgeGraph.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_graph(self, db: AsyncSession, graph_id: str, user_id: int) -> bool:
        record = await self.get_graph(db, graph_id, user_id)
        if not record:
            return False
        await db.delete(record)
        await db.commit()
        return True


graph_service = GraphService()
```

---

## 4. New API Routes (`src/backend/app/api/routes.py`)

Add to the existing router (after the `/research` routes):

```python
from app.graph_service import graph_service
from app.schemas import GraphRequest, GraphListItem, GraphDetail

@router.post("/graphs", response_model=GraphDetail)
@limiter.limit("10/minute")
async def create_graph(
    request: Request,
    graph_request: GraphRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a knowledge graph from a seed paper URL or ID."""
    if not graph_request.seed_paper_url and not graph_request.seed_paper_id:
        raise HTTPException(status_code=422, detail="Provide seed_paper_url or seed_paper_id")

    record = await graph_service.create_graph(
        db=db,
        user=current_user,
        seed_paper_url=graph_request.seed_paper_url,
        seed_paper_id=graph_request.seed_paper_id,
        depth=graph_request.depth,
        max_papers=graph_request.max_papers,
    )
    return record


@router.get("/graphs", response_model=List[GraphListItem])
async def list_graphs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge graphs for the current user."""
    return await graph_service.get_graphs(db, current_user.id)


@router.get("/graphs/{graph_id}", response_model=GraphDetail)
async def get_graph(
    graph_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific graph by ID (includes full graph_json when completed)."""
    record = await graph_service.get_graph(db, graph_id, current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Graph not found")
    return record


@router.delete("/graphs/{graph_id}", status_code=204)
async def delete_graph(
    graph_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a graph."""
    deleted = await graph_service.delete_graph(db, graph_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Graph not found")


@router.get("/graphs/{graph_id}/export")
async def export_graph(
    graph_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download graph as JSON file."""
    from fastapi.responses import Response
    record = await graph_service.get_graph(db, graph_id, current_user.id)
    if not record or not record.graph_json:
        raise HTTPException(status_code=404, detail="Graph not found or not yet completed")
    return Response(
        content=record.graph_json,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="graph_{graph_id[:8]}.json"'},
    )
```

---

## 5. Alembic Migration

```bash
cd src/backend
alembic revision --autogenerate -m "add_knowledge_graphs_table"
alembic upgrade head
```

Expected: one new `knowledge_graphs` table, no changes to existing tables.

---

## 6. Environment Variable

Add to `src/backend/example.env`:

```bash
# URL of the research-ai FastAPI service
RESEARCH_AI_API_URL=http://research-ai:8001
```

And to `src/backend/app/config.py`:

```python
research_ai_api_url: str = Field(default="http://localhost:8001", env="RESEARCH_AI_API_URL")
```

---

## 7. `docker-compose.yml` Update

The `research-ai` service needs to be reachable from the backend container.
Add to `docker-compose.yml` (or `docker-compose.prod.yml`):

```yaml
services:
  backend:
    environment:
      - RESEARCH_AI_API_URL=http://research-ai:8001
    depends_on:
      - research-ai

  research-ai:
    build:
      context: ../../research-ai   # path to the research-ai repo
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SEMANTIC_SCHOLAR_API_KEY=${SEMANTIC_SCHOLAR_API_KEY}
    command: uvicorn api.app:app --host 0.0.0.0 --port 8001
```

---

## 8. Bot API Client Extension (`src/telegram/api_client.py`)

Add graph methods to the existing `APIClient` class:

```python
async def create_graph(
    self,
    telegram_id: int,
    seed_paper_url: str | None = None,
    seed_paper_id: str | None = None,
    depth: int = 1,
    max_papers: int = 30,
) -> dict:
    token = self.get_user_token(telegram_id)
    return await self._make_request(
        "POST", "/graphs",
        data={
            "seed_paper_url": seed_paper_url,
            "seed_paper_id": seed_paper_id,
            "depth": depth,
            "max_papers": max_papers,
        },
        token=token,
    )

async def get_graphs(self, telegram_id: int) -> list:
    token = self.get_user_token(telegram_id)
    return await self._make_request("GET", "/graphs", token=token)

async def get_graph(self, telegram_id: int, graph_id: str) -> dict:
    token = self.get_user_token(telegram_id)
    return await self._make_request("GET", f"/graphs/{graph_id}", token=token)

async def export_graph(self, telegram_id: int, graph_id: str) -> bytes:
    """Download graph JSON as bytes for sending as Telegram document."""
    token = self.get_user_token(telegram_id)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            f"{self.base_url}/api/v1/graphs/{graph_id}/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.content
```
