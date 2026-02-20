"""Pydantic models for the knowledge graph.

Defines the core graph data structures used for serialization, API responses,
and in-memory graph manipulation.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """A node in the knowledge graph.

    :ivar id: Stable UUID for this node.
    :ivar label: Human-readable label (e.g. paper title, concept name).
    :ivar type: Node type: ``paper``, ``concept``, ``method``, ``finding``,
                ``author``, or ``institution``.
    :ivar properties: Arbitrary key-value metadata (DOI, year, definition, etc.).
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """A directed edge in the knowledge graph.

    :ivar source: ID of the source node.
    :ivar target: ID of the target node.
    :ivar type: Relationship type: ``cites``, ``uses_method``,
                ``reaches_conclusion``, ``contradicts``, ``extends``,
                ``shares_concept``, or ``authored``.
    :ivar weight: Edge weight (default 1.0).
    :ivar properties: Arbitrary key-value metadata.
    """

    source: str
    target: str
    type: str
    weight: float = 1.0
    properties: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    """A complete knowledge graph with nodes and edges.

    :ivar id: Stable UUID for this graph.
    :ivar seed_paper_id: Semantic Scholar paper ID of the seed paper.
    :ivar title: Human-readable graph title.
    :ivar nodes: List of graph nodes.
    :ivar edges: List of directed edges.
    :ivar metadata: Arbitrary graph-level metadata.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    seed_paper_id: Optional[str] = None
    title: str = ""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def merge(self, other: KnowledgeGraph) -> KnowledgeGraph:
        """Merge another graph into this one, deduplicating nodes by label+type.

        Nodes are considered duplicates when their ``(label.lower(), type)``
        pair matches an existing node. Edges referencing merged-away node IDs
        are remapped to the surviving node IDs.

        :param other: The graph to merge into this one (mutates ``self``).
        :returns: ``self`` for chaining.
        """
        existing_keys: set[tuple[str, str]] = {
            (n.label.lower(), n.type) for n in self.nodes
        }
        id_map: Dict[str, str] = {}

        for node in other.nodes:
            key = (node.label.lower(), node.type)
            if key in existing_keys:
                match = next(
                    n for n in self.nodes if (n.label.lower(), n.type) == key
                )
                id_map[node.id] = match.id
            else:
                existing_keys.add(key)
                id_map[node.id] = node.id
                self.nodes.append(node)

        existing_edges: set[tuple[str, str, str]] = {
            (e.source, e.target, e.type) for e in self.edges
        }
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
        """Serialize to a standard JSON-compatible dict.

        The format is compatible with common graph visualization tools
        (e.g. the frontend ``react-force-graph-2d`` component).

        :returns: Dict with ``id``, ``seed_paper_id``, ``title``, ``nodes``,
                  ``edges``, and ``metadata`` keys.
        """
        return {
            "id": self.id,
            "seed_paper_id": self.seed_paper_id,
            "title": self.title,
            "nodes": [n.model_dump() for n in self.nodes],
            "edges": [e.model_dump() for e in self.edges],
            "metadata": self.metadata,
        }
