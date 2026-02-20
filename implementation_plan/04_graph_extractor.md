# Phase 4: LLM-Based Graph Entity & Relation Extractor

## Goal

Create `agent/graph/extractor.py` — an LLM agent that reads a paper's title + abstract
and extracts structured nodes and edges for the knowledge graph.

## New File: `agent/graph/extractor.py`

```python
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from loguru import logger
from .models import GraphNode, GraphEdge, KnowledgeGraph

# ── Pydantic schemas for LLM structured output ──────────────────────────────

class ExtractedNode(BaseModel):
    label: str
    type: str  # paper | concept | method | finding | author | institution
    properties: dict = Field(default_factory=dict)

class ExtractedEdge(BaseModel):
    source_label: str
    target_label: str
    type: str
    weight: float = 1.0
    properties: dict = Field(default_factory=dict)

class ExtractionOutput(BaseModel):
    nodes: List[ExtractedNode] = Field(default_factory=list)
    edges: List[ExtractedEdge] = Field(default_factory=list)

# ── Agent setup ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are a scientific knowledge graph extractor.
Given a paper's title and abstract, extract:
1. Key NODES: the paper itself, scientific concepts, methods, findings, authors, institutions.
2. EDGES connecting them.

Node types: paper, concept, method, finding, author, institution
Edge types: cites, uses_method, reaches_conclusion, contradicts, extends, shares_concept

Rules:
- Keep labels concise (3-6 words max for concepts/methods)
- Extract 5-15 nodes and 5-20 edges per paper
- Always include the paper itself as a node of type "paper"
- findings should be specific, falsifiable statements from the abstract
- Return valid JSON matching the ExtractionOutput schema
"""

def _get_extractor_agent():
    from agents import Agent
    from shared.llm import get_agent_model
    return Agent(
        name="Graph Extractor",
        instructions=_SYSTEM_PROMPT,
        model=get_agent_model(),
        output_type=ExtractionOutput,
    )

# ── Main extraction function ─────────────────────────────────────────────────

async def extract_graph_from_paper(
    paper_id: str,
    title: str,
    abstract: str,
    doi: Optional[str] = None,
    year: Optional[int] = None,
    authors: Optional[List[str]] = None,
) -> KnowledgeGraph:
    """
    Extract a mini knowledge graph from a single paper using an LLM agent.
    Falls back to a minimal heuristic graph if the agent fails.
    """
    prompt = f"""
Title: {title}

Abstract: {abstract or 'Not available.'}

Extract the knowledge graph nodes and edges for this paper.
The paper node should have label="{title[:80]}", type="paper",
properties={{"doi": "{doi or ''}", "year": {year or 'null'}}}.
"""
    use_agents = os.getenv("PIPELINE_USE_AGENTS_GRAPH", "1").lower() in {"1", "true", "yes"}
    extraction: Optional[ExtractionOutput] = None

    if use_agents:
        try:
            from agents import Runner
            result = await Runner.run(_get_extractor_agent(), prompt)
            extraction = result.final_output
        except Exception as e:
            logger.warning(f"Graph extractor agent failed for {paper_id}: {e}")

    if extraction is None:
        extraction = _heuristic_extraction(title, abstract, doi, year, authors)

    return _build_graph(paper_id, extraction, title, doi, year, authors)


def _heuristic_extraction(
    title: str,
    abstract: str,
    doi: Optional[str],
    year: Optional[int],
    authors: Optional[List[str]],
) -> ExtractionOutput:
    """Minimal fallback: just the paper node + author nodes."""
    nodes = [ExtractedNode(
        label=title[:80],
        type="paper",
        properties={"doi": doi or "", "year": year},
    )]
    edges = []
    for author in (authors or [])[:3]:
        nodes.append(ExtractedNode(label=author, type="author", properties={}))
        edges.append(ExtractedEdge(
            source_label=author,
            target_label=title[:80],
            type="authored",
        ))
    return ExtractionOutput(nodes=nodes, edges=edges)


def _build_graph(
    paper_id: str,
    extraction: ExtractionOutput,
    title: str,
    doi: Optional[str],
    year: Optional[int],
    authors: Optional[List[str]],
) -> KnowledgeGraph:
    """Convert ExtractionOutput into a KnowledgeGraph with stable node IDs."""
    label_to_id: dict[str, str] = {}
    nodes: List[GraphNode] = []

    for en in extraction.nodes:
        node = GraphNode(label=en.label, type=en.type, properties=en.properties)
        label_to_id[en.label] = node.id
        nodes.append(node)

    edges: List[GraphEdge] = []
    for ee in extraction.edges:
        src_id = label_to_id.get(ee.source_label)
        tgt_id = label_to_id.get(ee.target_label)
        if src_id and tgt_id:
            edges.append(GraphEdge(
                source=src_id,
                target=tgt_id,
                type=ee.type,
                weight=ee.weight,
                properties=ee.properties,
            ))

    return KnowledgeGraph(
        seed_paper_id=paper_id,
        title=f"Graph: {title[:60]}",
        nodes=nodes,
        edges=edges,
        metadata={"doi": doi, "year": year, "authors": authors or []},
    )
```

## Environment Variable

```
PIPELINE_USE_AGENTS_GRAPH=1   # set to 0 to use heuristic fallback only
```

## LLM Cost Estimate

- ~500 tokens per paper (prompt + response)
- At $0.002/1K tokens (GPT-4o-mini via OpenRouter): **$0.001 per paper**
- 1,000 papers in cryo DB ≈ **$1.00 total**
