# Phase 8: Telegram Bot New Commands

## Goal

Add new Telegram bot commands for graph generation and retrieval. All changes are in
`bot/handlers/` — no existing handlers are modified.

## New File: `bot/handlers/graph.py`

```python
import json
import io
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

router = Router()

class GraphStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_depth = State()

# ── /seed command ─────────────────────────────────────────────────────────────

@router.message(Command("seed"))
async def cmd_seed(message: Message, state: FSMContext) -> None:
    """
    /seed <url_or_doi>
    Builds a knowledge graph from a seed paper URL or DOI.

    Examples:
        /seed https://elifesciences.org/articles/93796
        /seed DOI:10.7554/eLife.93796
    """
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "Usage: /seed <paper_url_or_doi>\n\n"
            "Examples:\n"
            "  /seed https://elifesciences.org/articles/93796\n"
            "  /seed DOI:10.7554/eLife.93796"
        )
        return

    identifier = args[1].strip()
    is_url = identifier.startswith("http")

    await message.answer(
        f"Building knowledge graph for:\n<code>{identifier}</code>\n\n"
        "This may take 1-2 minutes. I'll send you the graph file when ready.",
        parse_mode="HTML",
    )

    try:
        from agent.graph.builder import build_graph_from_seed
        graph = await build_graph_from_seed(
            seed_identifier=identifier,
            depth=1,
            max_papers=30,
            is_url=is_url,
        )

        # Save to DB
        from shared.database.operations import save_graph_record, get_or_create_user
        user = await get_or_create_user(message.from_user)
        await save_graph_record(graph, user_id=user.id)

        # Send summary
        await message.answer(
            f"Graph ready!\n\n"
            f"Title: {graph.title}\n"
            f"Nodes: {len(graph.nodes)}\n"
            f"Edges: {len(graph.edges)}\n"
            f"Graph ID: <code>{graph.id}</code>\n\n"
            f"Use /graph {graph.id} to download the JSON file.",
            parse_mode="HTML",
        )

    except ValueError as e:
        await message.answer(f"Could not resolve paper: {e}")
    except Exception as e:
        logger.error(f"Graph build failed for user {message.from_user.id}: {e}")
        await message.answer(f"Graph build failed: {e}")


# ── /graph command ────────────────────────────────────────────────────────────

@router.message(Command("graph"))
async def cmd_graph(message: Message) -> None:
    """
    /graph           — list your recent graphs
    /graph <id>      — download a graph as JSON file
    """
    args = (message.text or "").split(maxsplit=1)

    if len(args) < 2 or not args[1].strip():
        # List recent graphs
        from shared.database.operations import list_graph_records, get_or_create_user
        user = await get_or_create_user(message.from_user)
        records = await list_graph_records(user_id=user.id, limit=10)

        if not records:
            await message.answer(
                "No graphs yet. Use /seed <url> to generate one."
            )
            return

        lines = ["Your recent graphs:\n"]
        for r in records:
            lines.append(
                f"• <code>{r.id[:8]}...</code> — {r.title}\n"
                f"  {r.node_count} nodes, {r.edge_count} edges\n"
                f"  /graph {r.id}"
            )
        await message.answer("\n".join(lines), parse_mode="HTML")
        return

    # Download specific graph
    graph_id = args[1].strip()
    from shared.database.operations import get_graph_record
    record = await get_graph_record(graph_id)

    if not record:
        await message.answer(f"Graph <code>{graph_id}</code> not found.", parse_mode="HTML")
        return

    graph_dict = json.loads(record.graph_json)
    json_bytes = json.dumps(graph_dict, indent=2).encode("utf-8")
    file = BufferedInputFile(json_bytes, filename=f"graph_{graph_id[:8]}.json")

    await message.answer_document(
        document=file,
        caption=(
            f"Graph: {record.title}\n"
            f"Nodes: {record.node_count} | Edges: {record.edge_count}"
        ),
    )


# ── /batch command ────────────────────────────────────────────────────────────

@router.message(Command("batch"))
async def cmd_batch(message: Message) -> None:
    """
    /batch <url1> <url2> ...
    Build a merged graph from multiple seed papers (space or newline separated).
    """
    text = (message.text or "").split(maxsplit=1)
    if len(text) < 2 or not text[1].strip():
        await message.answer(
            "Usage: /batch <url1> <url2> ...\n\n"
            "Provide multiple paper URLs or DOIs separated by spaces or newlines.\n"
            "Example:\n"
            "/batch https://elifesciences.org/articles/93796 DOI:10.1021/acsnano.4c02012"
        )
        return

    raw = text[1].strip()
    identifiers = [s.strip() for s in raw.replace("\n", " ").split() if s.strip()]

    if len(identifiers) > 10:
        await message.answer(
            f"Too many seeds ({len(identifiers)}). Max 10 via bot. "
            "Use the API for larger batches."
        )
        return

    await message.answer(
        f"Building merged graph for {len(identifiers)} papers...\n"
        "This may take several minutes."
    )

    try:
        from agent.graph.batch import build_batch_graph
        from shared.database.operations import save_graph_record, get_or_create_user

        is_url = all(s.startswith("http") for s in identifiers)

        async def progress(current, total, graph):
            if current % 3 == 0 or current == total:
                await message.answer(
                    f"Progress: {current}/{total} seeds processed\n"
                    f"Graph so far: {len(graph.nodes)} nodes, {len(graph.edges)} edges"
                )

        graph = await build_batch_graph(
            seed_identifiers=identifiers,
            is_url=is_url,
            depth=1,
            max_papers_per_seed=20,
            progress_callback=progress,
        )

        user = await get_or_create_user(message.from_user)
        await save_graph_record(graph, user_id=user.id)

        json_bytes = json.dumps(graph.to_export_dict(), indent=2).encode("utf-8")
        file = BufferedInputFile(json_bytes, filename=f"batch_graph_{graph.id[:8]}.json")

        await message.answer_document(
            document=file,
            caption=(
                f"Batch graph complete!\n"
                f"Seeds: {len(identifiers)}\n"
                f"Nodes: {len(graph.nodes)} | Edges: {len(graph.edges)}\n"
                f"Graph ID: {graph.id}"
            ),
        )

    except Exception as e:
        logger.error(f"Batch graph failed for user {message.from_user.id}: {e}")
        await message.answer(f"Batch graph failed: {e}")
```

## Register Router in `bot/main.py` (or wherever routers are registered)

```python
from bot.handlers.graph import router as graph_router
dp.include_router(graph_router)
```

## Updated `/help` or `/start` command

Add to the existing help text:

```
Knowledge Graph Commands:
  /seed <url>     — Build a knowledge graph from a paper URL or DOI
  /graph          — List your recent graphs
  /graph <id>     — Download a graph as JSON
  /batch <urls>   — Build a merged graph from multiple papers
```

## Updated `/task` command (additive flag)

In `bot/handlers/task.py`, when creating a task, add optional graph flag parsing:

```python
# If user appends --graph to their task description, set build_graph=True
build_graph = "--graph" in description
seed_url = None
if build_graph:
    # Extract URL from description if present
    import re
    urls = re.findall(r'https?://\S+', description)
    seed_url = urls[0] if urls else None
    description = description.replace("--graph", "").strip()
```

Then pass `build_graph` and `seed_url` when building the `PipelineTask` in `manager.py`.

## Telegram Bot Commands Summary

| Command | Description |
|---|---|
| `/seed <url>` | Build graph from single seed paper |
| `/graph` | List recent graphs |
| `/graph <id>` | Download graph as JSON file |
| `/batch <urls>` | Build merged graph from multiple papers |
| `/task <query> --graph` | Run research pipeline + build graph |
