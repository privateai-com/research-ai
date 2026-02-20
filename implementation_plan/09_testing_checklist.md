# Phase 9: Testing & Verification Checklist

## Prerequisites

```bash
# Set env vars before running tests
export SEMANTIC_SCHOLAR_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here
export PIPELINE_USE_AGENTS_GRAPH=1
```

---

## 1. Semantic Scholar Browser

```python
# test: resolve eLife paper by URL
from agent.browsing.manual.sources.semantic_scholar import SemanticScholarBrowser
browser = SemanticScholarBrowser()

paper = browser.get_by_url("https://elifesciences.org/articles/93796")
assert paper is not None
assert paper.title
assert paper.paper_id
print(f"✓ eLife paper: {paper.title} ({paper.paper_id})")

# test: resolve ACS Nano paper by URL
paper2 = browser.get_by_url("https://pubs.acs.org/doi/10.1021/acsnano.4c02012")
assert paper2 is not None
assert paper2.title
print(f"✓ ACS Nano paper: {paper2.title} ({paper2.paper_id})")

# test: search
results = browser.search("cryoprotectant vitrification organ preservation", max_results=5)
assert len(results) > 0
print(f"✓ Search returned {len(results)} results")

# test: get references
refs = browser.get_references(paper.paper_id, limit=10)
print(f"✓ Got {len(refs)} references for eLife paper")
```

---

## 2. Semantic Reranking

```python
import asyncio
from agent.pipeline.semantic_rerank import semantic_rerank
from agent.pipeline.models import PaperCandidate

# Create dummy candidates with different terminology
candidates = [
    PaperCandidate(arxiv_id="1", title="Vitrification of mammalian organs",
                   summary="We demonstrate that rapid cooling prevents ice crystal formation in kidney tissue."),
    PaperCandidate(arxiv_id="2", title="Machine learning for protein folding",
                   summary="Neural networks predict protein tertiary structure from sequence."),
    PaperCandidate(arxiv_id="3", title="Cryogenic preservation of biological samples",
                   summary="Low temperature storage maintains cell viability through controlled cooling rates."),
]

# Query about conclusions, not keywords
query = "preventing ice crystal damage during freezing of biological tissue"
reranked = semantic_rerank(query, candidates, top_k=3)

# The cryogenic papers should rank higher than the ML paper
assert reranked[0].arxiv_id != "2", "ML paper should not be top result for cryo query"
print(f"✓ Semantic rerank: top result = '{reranked[0].title}'")
print(f"  Order: {[c.arxiv_id for c in reranked]}")
```

---

## 3. Graph Extractor

```python
import asyncio
from agent.graph.extractor import extract_graph_from_paper

graph = asyncio.run(extract_graph_from_paper(
    paper_id="test_paper_1",
    title="Organ-on-a-chip models for cryopreservation research",
    abstract="We developed a microfluidic organ chip to study cryoprotectant perfusion. "
             "Results show that DMSO at 10% concentration prevents ice formation while "
             "maintaining cell viability above 85%. The method extends to kidney organoids.",
    doi="10.7554/eLife.93796",
    year=2024,
    authors=["Don Ingber", "Jane Smith"],
))

assert len(graph.nodes) >= 3, f"Expected ≥3 nodes, got {len(graph.nodes)}"
assert len(graph.edges) >= 2, f"Expected ≥2 edges, got {len(graph.edges)}"
node_types = {n.type for n in graph.nodes}
assert "paper" in node_types, "Should have a paper node"
print(f"✓ Extractor: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
print(f"  Node types: {node_types}")
```

---

## 4. Graph Builder (Single Seed)

```python
import asyncio
from agent.graph.builder import build_graph_from_seed

graph = asyncio.run(build_graph_from_seed(
    seed_identifier="https://elifesciences.org/articles/93796",
    depth=1,
    max_papers=5,  # small for testing
    is_url=True,
))

assert graph is not None
assert len(graph.nodes) > 0
assert len(graph.edges) > 0
assert graph.seed_paper_id is not None

export = graph.to_export_dict()
assert "nodes" in export
assert "edges" in export
assert isinstance(export["nodes"], list)
assert isinstance(export["edges"], list)

print(f"✓ Graph builder: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
print(f"  Seed paper ID: {graph.seed_paper_id}")
```

---

## 5. FastAPI Endpoints

```bash
# Start the API server
uvicorn api.app:app --reload --port 8000
```

```python
import httpx
import asyncio

BASE = "http://localhost:8000"

async def test_api():
    async with httpx.AsyncClient(timeout=120) as client:

        # Health check
        r = await client.get(f"{BASE}/healthz")
        assert r.status_code == 200
        print("✓ /healthz OK")

        # Generate graph from seed URL
        r = await client.post(f"{BASE}/v1/graph", json={
            "seed_paper_url": "https://elifesciences.org/articles/93796",
            "depth": 1,
            "max_papers": 5,
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "graph_id" in data
        assert "nodes" in data["graph"]
        assert "edges" in data["graph"]
        graph_id = data["graph_id"]
        print(f"✓ POST /v1/graph: {data['node_count']} nodes, {data['edge_count']} edges")

        # Retrieve graph by ID
        r = await client.get(f"{BASE}/v1/graph/{graph_id}")
        assert r.status_code == 200
        print(f"✓ GET /v1/graph/{graph_id[:8]}... OK")

        # Batch graph
        r = await client.post(f"{BASE}/v1/batch", json={
            "seed_identifiers": [
                "DOI:10.7554/eLife.93796",
                "DOI:10.1021/acsnano.4c02012",
            ],
            "depth": 1,
            "max_papers_per_seed": 5,
        })
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["seed_count"] == 2
        print(f"✓ POST /v1/batch: {data['node_count']} nodes, {data['edge_count']} edges")

        # Existing /v1/run still works (regression check)
        r = await client.post(f"{BASE}/v1/run", json={
            "query": "cryoprotectant organ preservation",
            "max_queries": 2,
            "bm25_top_k": 5,
            "max_analyze": 3,
        })
        assert r.status_code == 200
        print("✓ POST /v1/run (regression) OK")

asyncio.run(test_api())
```

---

## 6. Telegram Bot Commands

Manual test sequence in Telegram:

```
1. /seed https://elifesciences.org/articles/93796
   Expected: "Building knowledge graph..." → graph summary message with ID

2. /graph
   Expected: List of recent graphs with IDs

3. /graph <id_from_step_1>
   Expected: Bot sends a .json file attachment

4. /batch https://elifesciences.org/articles/93796 DOI:10.1021/acsnano.4c02012
   Expected: Progress messages → final .json file with merged graph

5. /task find papers about cryoprotectant toxicity --graph
   Expected: Normal task flow + graph file delivered at end
```

---

## 7. Semantic Rerank in Pipeline (Integration)

```python
import asyncio
from agent.pipeline.pipeline import run_pipeline
from agent.pipeline.models import PipelineTask

task = PipelineTask(
    query="similar conclusions to: preventing ice crystal formation preserves organ viability",
    max_queries=2,
    bm25_top_k=10,
    max_analyze=5,
    use_semantic_rerank=True,  # NEW FLAG
)

output = asyncio.run(run_pipeline(task))
assert output.selected is not None
print(f"✓ Pipeline with semantic rerank: {len(output.selected)} selected papers")
```

---

## 8. Batch CLI Script

```bash
# Create a test CSV
echo "doi,title" > test_cryo.csv
echo "10.7554/eLife.93796,eLife organ chip" >> test_cryo.csv
echo "10.1021/acsnano.4c02012,ACS Nano nanoparticle" >> test_cryo.csv

# Run batch
python scripts/build_cryo_graph.py \
    --input test_cryo.csv \
    --output test_cryo_graph.json \
    --depth 1 \
    --max-papers 5

# Verify output
python -c "
import json
with open('test_cryo_graph.json') as f:
    g = json.load(f)
assert 'nodes' in g and 'edges' in g
print(f'✓ Batch CLI: {len(g[\"nodes\"])} nodes, {len(g[\"edges\"])} edges')
"
```

---

## 9. Alembic Migration

```bash
# Generate migration
alembic revision --autogenerate -m "add_knowledge_graph_tables"

# Review the generated migration file in alembic/versions/
# Then apply:
alembic upgrade head

# Verify tables exist
python -c "
from shared.database.models import KnowledgeGraphRecord, GraphSeedPaper
print('✓ ORM models importable')
"
```

---

## Regression Checklist

- [ ] Existing `/task` flow unaffected (no `build_graph` flag = old behavior)
- [ ] `use_semantic_rerank=False` (default) produces same results as before
- [ ] `build_graph=False` (default) produces same results as before
- [ ] Alembic migration runs cleanly on fresh DB
- [ ] All existing bot commands still work
- [ ] API `/v1/run` without new fields returns same schema as before
