# Phase 10: Alembic DB Migration

## Goal

Add the two new tables (`knowledge_graph`, `graph_seed_paper`) to the existing database
without touching any existing tables or data.

## Steps

### 1. Ensure Alembic is configured

Check `alembic.ini` and `alembic/env.py` — they should already exist since the project
uses Alembic. Verify `target_metadata` points to `shared.database.models.Base`.

```python
# alembic/env.py — verify this line exists:
from shared.database.models import Base
target_metadata = Base.metadata
```

### 2. Import new models in `shared/database/models.py`

The two new ORM classes (`KnowledgeGraphRecord`, `GraphSeedPaper`) defined in Phase 3
must be in the same file as `Base` so Alembic's autogenerate detects them.

### 3. Generate the migration

```bash
alembic revision --autogenerate -m "add_knowledge_graph_tables"
```

### 4. Review the generated file

The generated file in `alembic/versions/` should contain two `op.create_table` calls.
Verify it does NOT contain any `op.drop_table` or `op.alter_column` for existing tables.

Expected generated migration (reference):

```python
def upgrade() -> None:
    op.create_table(
        "knowledge_graph",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("user_task_id", sa.Integer(), sa.ForeignKey("user_task.id"), nullable=True),
        sa.Column("seed_paper_id", sa.String(255), nullable=True),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("graph_json", sa.Text(), nullable=False),
        sa.Column("node_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("edge_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_graph_seed_paper_id", "knowledge_graph", ["seed_paper_id"])
    op.create_index("ix_knowledge_graph_user_id", "knowledge_graph", ["user_id"])

    op.create_table(
        "graph_seed_paper",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("graph_id", sa.String(36), sa.ForeignKey("knowledge_graph.id"), nullable=False),
        sa.Column("paper_id", sa.String(255), nullable=False),
        sa.Column("paper_url", sa.String(1000), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_graph_seed_paper_graph_id", "graph_seed_paper", ["graph_id"])


def downgrade() -> None:
    op.drop_table("graph_seed_paper")
    op.drop_table("knowledge_graph")
```

### 5. Apply the migration

```bash
alembic upgrade head
```

### 6. Verify

```bash
# SQLite: inspect tables
python -c "
import sqlite3, os
db_path = os.getenv('DATABASE_URL', 'research.db').replace('sqlite:///', '')
conn = sqlite3.connect(db_path)
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('Tables:', [t[0] for t in tables])
assert ('knowledge_graph',) in tables
assert ('graph_seed_paper',) in tables
print('✓ Migration verified')
"
```

## `pyproject.toml` Dependency Additions

Add to `[project.dependencies]`:

```toml
"numpy>=1.24",          # for future SPECTER2 local embeddings (optional now)
```

No new required packages — `requests` and `openai` are already present.

## Environment Variables Summary

Add to `.env` (or deployment secrets):

```bash
# Required for Semantic Scholar integration
SEMANTIC_SCHOLAR_API_KEY=your_key_here

# Required for semantic reranking (already present for LLM)
OPENAI_API_KEY=your_key_here

# Feature flags (optional, defaults shown)
PIPELINE_USE_AGENTS_GRAPH=1      # 1=LLM extraction, 0=heuristic only
```

## Rollback Plan

If migration causes issues:

```bash
alembic downgrade -1
```

This drops only the two new tables and leaves all existing data intact.
