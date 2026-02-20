# Phase 3: Graph Data Models & DB Schema

## Goal

Define Pydantic models for the knowledge graph (for serialization/API) and SQLAlchemy ORM
models for persisting graphs to the database.

## New File: `agent/graph/models.py`

```python
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

class GraphNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    type: str  # "paper" | "concept" | "method" | "finding" | "author" | "institution"
    properties: Dict[str, Any] = Field(default_factory=dict)
    # e.g. for paper: {"doi": "...", "year": 2023, "abstract": "..."}
    # e.g. for concept: {"definition": "...", "aliases": [...]}

class GraphEdge(BaseModel):
    source: str   # node id
    target: str   # node id
    type: str     # "cites" | "uses_method" | "reaches_conclusion" | "contradicts" | "extends"
    weight: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)

class KnowledgeGraph(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    seed_paper_id: Optional[str] = None
    title: str = ""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def merge(self, other: "KnowledgeGraph") -> "KnowledgeGraph":
        """Merge another graph into this one, deduplicating nodes by label+type."""
        existing_keys = {(n.label.lower(), n.type) for n in self.nodes}
        id_map: Dict[str, str] = {}  # other.node.id -> self.node.id

        for node in other.nodes:
            key = (node.label.lower(), node.type)
            if key in existing_keys:
                # Find the existing node's id
                match = next(n for n in self.nodes if (n.label.lower(), n.type) == key)
                id_map[node.id] = match.id
            else:
                existing_keys.add(key)
                id_map[node.id] = node.id
                self.nodes.append(node)

        existing_edges = {(e.source, e.target, e.type) for e in self.edges}
        for edge in other.edges:
            mapped = GraphEdge(
                source=id_map.get(edge.source, edge.source),
                target=id_map.get(edge.target, edge.target),
                type=edge.type,
                weight=edge.weight,
                properties=edge.properties,
            )
            key = (mapped.source, mapped.target, mapped.type)
            if key not in existing_edges:
                existing_edges.add(key)
                self.edges.append(mapped)

        return self

    def to_export_dict(self) -> dict:
        """Standard JSON export format compatible with graph visualization tools."""
        return {
            "id": self.id,
            "seed_paper_id": self.seed_paper_id,
            "title": self.title,
            "nodes": [n.model_dump() for n in self.nodes],
            "edges": [e.model_dump() for e in self.edges],
            "metadata": self.metadata,
        }
```

## DB Schema Additions (`shared/database/models.py`)

Add two new ORM models:

```python
class KnowledgeGraphRecord(Base):
    __tablename__ = "knowledge_graph"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), nullable=True, index=True)
    user_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user_task.id"), nullable=True)
    seed_paper_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    graph_json: Mapped[str] = mapped_column(Text)  # serialized KnowledgeGraph JSON
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class GraphSeedPaper(Base):
    __tablename__ = "graph_seed_paper"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graph_id: Mapped[str] = mapped_column(ForeignKey("knowledge_graph.id"), index=True)
    paper_id: Mapped[str] = mapped_column(String(255))   # SS paperId or DOI
    paper_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

## Node Types Reference

| Type | Description | Key Properties |
|---|---|---|
| `paper` | A research paper | doi, year, abstract, authors, source |
| `concept` | Scientific concept (e.g. "cryoprotectant") | definition, aliases |
| `method` | Experimental method (e.g. "vitrification") | description |
| `finding` | A specific result/conclusion | text, confidence |
| `author` | A researcher | affiliation, orcid |
| `institution` | Lab or university | location |

## Edge Types Reference

| Type | Description |
|---|---|
| `cites` | Paper A cites Paper B |
| `uses_method` | Paper uses a method |
| `reaches_conclusion` | Paper reaches a finding |
| `contradicts` | Finding contradicts another finding |
| `extends` | Paper extends prior work |
| `shares_concept` | Two papers share a concept |
