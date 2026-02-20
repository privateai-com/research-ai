# Implementation Plan: Knowledge Graph & Semantic Search Extension

## Project Summary

Extend the existing `research-ai` agentic pipeline to support:
1. **Semantic search** — find papers by conclusion similarity, not just keywords
2. **Knowledge graph generation** — seed a paper, auto-build a graph of related concepts, methods, and findings
3. **Batch processing** — transform a cryo database into a giant knowledge graph
4. **Telegram bot & Web UI updates** — expose all new features to end users

## Guiding Principles

- **Additive only** — do not break the existing `/task` flow
- `build_graph` defaults to `False`, `use_semantic_rerank` defaults to `False`
- All new features are opt-in flags on existing models
- Prefer small, focused modules over large monolithic files

## External APIs & Services Required

| Service | Purpose | Env Var | Free Tier |
|---|---|---|---|
| Semantic Scholar API | DOI/URL resolution, citations, SPECTER2 embeddings | `SEMANTIC_SCHOLAR_API_KEY` | Yes (100 req/5min unauthenticated, 1 req/s authenticated) |
| OpenAI Embeddings | `text-embedding-3-small` for semantic reranking | `OPENAI_API_KEY` | No (pay-per-use) |
| OpenAI / OpenRouter | LLM for entity extraction in graph builder | `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | Existing |

## What the Client Needs From You

- `SEMANTIC_SCHOLAR_API_KEY` — register at https://www.semanticscholar.org/product/api
- Confirm budget for OpenAI embedding calls (~$0.02 per 1M tokens, very cheap)
- A sample cryo database export (CSV or JSON) for batch processing design
- Confirmation of preferred graph export format (JSON assumed)

## File Structure Overview

```
implementation_plan/
  00_overview.md              ← this file
  01_semantic_scholar.md      ← Phase 1: Semantic Scholar browser module
  02_semantic_rerank.md       ← Phase 2: Embedding-based semantic reranking
  03_graph_models.md          ← Phase 3: Graph data models & DB schema
  04_graph_extractor.md       ← Phase 4: LLM-based graph entity/relation extractor
  05_graph_builder.md         ← Phase 5: Graph builder orchestrator
  06_batch_processor.md       ← Phase 6: Batch processing for cryo database
  07_api_endpoints.md         ← Phase 7: FastAPI new endpoints
  08_telegram_bot.md          ← Phase 8: Telegram bot new commands
  09_testing_checklist.md     ← Phase 9: Testing & verification checklist
  10_migration.md             ← Phase 10: Alembic DB migration
```
