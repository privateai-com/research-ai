# Phase 13: Telegram Bot UI (research-agent-front/src/telegram)

## Architecture Context

The Telegram bot lives in `src/telegram/`. It uses `aiogram` with FSM states, a shared
`api_client` (wraps the `src/backend` REST API), and per-user token caching.

Existing pattern (from `handlers/user/research.py`):
1. Validate input
2. Authenticate user via `api_client`
3. Call backend API
4. Poll for status every 5 seconds (max 24 attempts = 2 min)
5. Edit the processing message with results

All new handlers follow this exact pattern. New file:
**`src/telegram/handlers/user/graph.py`**

---

## New File: `src/telegram/handlers/user/graph.py`

```python
"""
Handlers for knowledge graph commands: /seed, /graphs, /batch_graph
"""

import asyncio
import io
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from api_client import api_client

router = Router(name="graph")


class GraphStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_batch_urls = State()


# ── /seed ─────────────────────────────────────────────────────────────────────

@router.message(Command("seed"))
async def seed_command(message: Message, state: FSMContext):
    """
    /seed <paper_url_or_doi>
    Build a knowledge graph from a single seed paper.

    Examples:
        /seed https://elifesciences.org/articles/93796
        /seed DOI:10.7554/eLife.93796
    """
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "🕸️ <b>Build a Knowledge Graph</b>\n\n"
            "Please provide a paper URL or DOI:\n\n"
            "<b>Examples:</b>\n"
            "• <code>/seed https://elifesciences.org/articles/93796</code>\n"
            "• <code>/seed https://pubs.acs.org/doi/10.1021/acsnano.4c02012</code>\n"
            "• <code>/seed DOI:10.7554/eLife.93796</code>\n\n"
            "Or just send the URL/DOI now:",
            parse_mode="HTML",
        )
        await state.set_state(GraphStates.waiting_for_url)
        return

    identifier = parts[1].strip()
    await _build_graph(message, identifier)


@router.message(GraphStates.waiting_for_url)
async def handle_graph_url_input(message: Message, state: FSMContext):
    """Handle URL/DOI input after /seed with no argument."""
    await state.clear()
    identifier = message.text.strip()
    if not identifier:
        await message.answer("❌ Please provide a valid URL or DOI.")
        return
    await _build_graph(message, identifier)


async def _build_graph(message: Message, identifier: str, depth: int = 1, max_papers: int = 30):
    """Core graph build flow: authenticate → create → poll → deliver."""
    try:
        # Ensure authenticated
        if not api_client.get_user_token(message.from_user.id):
            await api_client.authenticate_telegram_user(
                telegram_id=message.from_user.id,
                auth_data={
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                    "username": message.from_user.username,
                },
            )

        is_url = identifier.startswith("http")
        processing_msg = await message.answer(
            f"🕸️ <b>Building knowledge graph for:</b>\n"
            f"<code>{identifier}</code>\n\n"
            f"⏳ <i>Resolving paper and fetching citation network...</i>\n"
            f"This takes 1–2 minutes.",
            parse_mode="HTML",
        )

        response = await api_client.create_graph(
            telegram_id=message.from_user.id,
            seed_paper_url=identifier if is_url else None,
            seed_paper_id=identifier if not is_url else None,
            depth=depth,
            max_papers=max_papers,
        )

        graph_id = response["id"]
        max_attempts = 36  # 3 minutes max (36 × 5s)
        attempt = 0

        while attempt < max_attempts:
            await asyncio.sleep(5)
            attempt += 1

            try:
                updated = await api_client.get_graph(message.from_user.id, graph_id)

                if updated["status"] == "completed":
                    node_count = updated.get("node_count", 0)
                    edge_count = updated.get("edge_count", 0)
                    title = updated.get("title", "Knowledge Graph")

                    # Send summary message
                    await processing_msg.edit_text(
                        f"✅ <b>Graph Ready!</b>\n\n"
                        f"<b>{title}</b>\n\n"
                        f"📊 <b>Nodes:</b> {node_count}\n"
                        f"🔗 <b>Edges:</b> {edge_count}\n"
                        f"🆔 <b>ID:</b> <code>{graph_id[:8]}...</code>\n\n"
                        f"Use <code>/graphs {graph_id}</code> to download the JSON file.\n"
                        f"Or view it at: research.privateai.com/graphs",
                        parse_mode="HTML",
                    )

                    # Auto-send the JSON file
                    try:
                        json_bytes = await api_client.export_graph(
                            message.from_user.id, graph_id
                        )
                        file = BufferedInputFile(
                            json_bytes,
                            filename=f"graph_{graph_id[:8]}.json",
                        )
                        await message.answer_document(
                            document=file,
                            caption=(
                                f"📎 <b>{title}</b>\n"
                                f"Nodes: {node_count} | Edges: {edge_count}"
                            ),
                            parse_mode="HTML",
                        )
                    except Exception as export_err:
                        # Non-fatal: summary was already sent
                        print(f"Graph export failed: {export_err}")

                    return

                elif updated["status"] == "failed":
                    error = updated.get("error_message", "Unknown error")
                    await processing_msg.edit_text(
                        f"❌ <b>Graph Build Failed</b>\n\n"
                        f"<b>Seed:</b> <code>{identifier}</code>\n\n"
                        f"<b>Error:</b> {error}\n\n"
                        "Please check the URL/DOI and try again with <code>/seed</code>.",
                        parse_mode="HTML",
                    )
                    return

                # Progress update
                dots = "." * (attempt % 4)
                await processing_msg.edit_text(
                    f"🕸️ <b>Building graph{dots}</b>\n\n"
                    f"<code>{identifier}</code>\n\n"
                    f"⏳ <i>Extracting entities and relationships...</i>\n"
                    f"⏱️ <i>Time elapsed: {attempt * 5}s</i>",
                    parse_mode="HTML",
                )

            except Exception as poll_err:
                print(f"Graph poll error: {poll_err}")
                continue

        await processing_msg.edit_text(
            f"⏰ <b>Graph Build Timeout</b>\n\n"
            f"The graph is still processing in the background.\n"
            f"Use <code>/graphs {graph_id}</code> to check later.",
            parse_mode="HTML",
        )

    except Exception as e:
        await message.answer(
            f"❌ <b>Error building graph:</b>\n{str(e)}\n\nPlease try again later.",
            parse_mode="HTML",
        )


# ── /graphs ───────────────────────────────────────────────────────────────────

@router.message(Command("graphs"))
async def graphs_command(message: Message):
    """
    /graphs           — list your recent knowledge graphs
    /graphs <id>      — download a specific graph as JSON
    """
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        # List graphs
        try:
            if not api_client.get_user_token(message.from_user.id):
                await api_client.authenticate_telegram_user(
                    telegram_id=message.from_user.id,
                    auth_data={
                        "first_name": message.from_user.first_name,
                        "username": message.from_user.username,
                    },
                )

            graphs = await api_client.get_graphs(message.from_user.id)

            if not graphs:
                await message.answer(
                    "🕸️ <b>No graphs yet.</b>\n\n"
                    "Use <code>/seed &lt;paper_url&gt;</code> to build your first knowledge graph.",
                    parse_mode="HTML",
                )
                return

            lines = ["🕸️ <b>Your Knowledge Graphs:</b>\n"]
            for g in graphs[:10]:
                status_emoji = {
                    "completed": "✅",
                    "processing": "⏳",
                    "failed": "❌",
                    "pending": "⏸",
                }.get(g["status"], "❓")

                lines.append(
                    f"{status_emoji} <b>{g['title'][:50]}</b>\n"
                    f"   📊 {g['node_count']} nodes · 🔗 {g['edge_count']} edges\n"
                    f"   <code>/graphs {g['id']}</code>\n"
                )

            lines.append("\nUse <code>/seed &lt;url&gt;</code> to build a new graph.")
            await message.answer("\n".join(lines), parse_mode="HTML")

        except Exception as e:
            await message.answer(
                f"❌ <b>Error fetching graphs:</b>\n{str(e)}",
                parse_mode="HTML",
            )
        return

    # Download specific graph
    graph_id = parts[1].strip()
    try:
        if not api_client.get_user_token(message.from_user.id):
            await api_client.authenticate_telegram_user(
                telegram_id=message.from_user.id,
                auth_data={"first_name": message.from_user.first_name},
            )

        graph = await api_client.get_graph(message.from_user.id, graph_id)

        if graph["status"] != "completed":
            await message.answer(
                f"⏳ Graph <code>{graph_id[:8]}...</code> is still <b>{graph['status']}</b>.\n"
                "Please wait and try again.",
                parse_mode="HTML",
            )
            return

        json_bytes = await api_client.export_graph(message.from_user.id, graph_id)
        file = BufferedInputFile(json_bytes, filename=f"graph_{graph_id[:8]}.json")
        await message.answer_document(
            document=file,
            caption=(
                f"📎 <b>{graph['title']}</b>\n"
                f"Nodes: {graph['node_count']} | Edges: {graph['edge_count']}"
            ),
            parse_mode="HTML",
        )

    except Exception as e:
        await message.answer(
            f"❌ <b>Error downloading graph:</b>\n{str(e)}",
            parse_mode="HTML",
        )


# ── /batch_graph ──────────────────────────────────────────────────────────────

@router.message(Command("batch_graph"))
async def batch_graph_command(message: Message, state: FSMContext):
    """
    /batch_graph <url1> <url2> ...
    Build a merged graph from multiple seed papers (space or newline separated, max 10).
    """
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "🕸️ <b>Batch Knowledge Graph</b>\n\n"
            "Provide multiple paper URLs or DOIs (space or newline separated):\n\n"
            "<b>Example:</b>\n"
            "<code>/batch_graph https://elifesciences.org/articles/93796\n"
            "DOI:10.1021/acsnano.4c02012</code>\n\n"
            "Maximum 10 papers per batch via bot.\n"
            "Or send the URLs now:",
            parse_mode="HTML",
        )
        await state.set_state(GraphStates.waiting_for_batch_urls)
        return

    raw = parts[1].strip()
    await _process_batch(message, raw)


@router.message(GraphStates.waiting_for_batch_urls)
async def handle_batch_url_input(message: Message, state: FSMContext):
    """Handle URL list input after /batch_graph with no arguments."""
    await state.clear()
    await _process_batch(message, message.text.strip())


async def _process_batch(message: Message, raw: str):
    """Parse identifiers and build batch graph sequentially."""
    identifiers = [s.strip() for s in raw.replace("\n", " ").split() if s.strip()]

    if len(identifiers) < 2:
        await message.answer(
            "❌ Please provide at least 2 paper URLs or DOIs.",
            parse_mode="HTML",
        )
        return

    if len(identifiers) > 10:
        await message.answer(
            f"❌ Too many papers ({len(identifiers)}). Maximum 10 via bot.\n"
            "For larger batches, use the web interface or API.",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"🕸️ <b>Building batch graph for {len(identifiers)} papers...</b>\n\n"
        + "\n".join(f"• <code>{s[:60]}</code>" for s in identifiers)
        + "\n\n⏳ <i>This may take several minutes.</i>",
        parse_mode="HTML",
    )

    # Build graphs sequentially and report progress
    results = []
    for i, identifier in enumerate(identifiers):
        try:
            progress_msg = await message.answer(
                f"⏳ Processing {i+1}/{len(identifiers)}: <code>{identifier[:60]}</code>",
                parse_mode="HTML",
            )
            # Each seed uses a small max_papers to keep batch fast
            await _build_graph(message, identifier, depth=1, max_papers=15)
            results.append({"id": identifier, "ok": True})
        except Exception as e:
            results.append({"id": identifier, "ok": False, "error": str(e)})

    success_count = sum(1 for r in results if r["ok"])
    await message.answer(
        f"✅ <b>Batch complete!</b>\n\n"
        f"Successfully built: {success_count}/{len(identifiers)} graphs\n\n"
        f"Use <code>/graphs</code> to see all your graphs.",
        parse_mode="HTML",
    )
```

---

## Register the Router

In `src/telegram/handlers/user/__init__.py`, add:

```python
from .graph import router as graph_router
```

In `src/telegram/handlers/__init__.py` or `main.py`, include the router:

```python
from handlers.user.graph import router as graph_router
dp.include_router(graph_router)
```

---

## Update `/start` or `/help` Command

In the existing `me.py` or `common/` handler, add graph commands to the help text:

```python
GRAPH_HELP = """
🕸️ <b>Knowledge Graph Commands:</b>
• <code>/seed &lt;url&gt;</code> — Build a graph from a paper URL or DOI
• <code>/graphs</code> — List your recent graphs
• <code>/graphs &lt;id&gt;</code> — Download a graph as JSON
• <code>/batch_graph &lt;url1&gt; &lt;url2&gt; ...</code> — Merge graphs from multiple papers
"""
```

---

## Bot Command Registration

Register new commands with BotFather (update `set_my_commands` call):

```python
from aiogram.types import BotCommand

commands = [
    # ... existing commands ...
    BotCommand(command="seed", description="Build a knowledge graph from a paper URL"),
    BotCommand(command="graphs", description="List or download your knowledge graphs"),
    BotCommand(command="batch_graph", description="Build a merged graph from multiple papers"),
]
await bot.set_my_commands(commands)
```

---

## File Summary

| File | Action |
|---|---|
| `src/telegram/handlers/user/graph.py` | **New** — `/seed`, `/graphs`, `/batch_graph` handlers |
| `src/telegram/handlers/user/__init__.py` | Import and export `graph_router` |
| `src/telegram/api_client.py` | Add `create_graph`, `get_graphs`, `get_graph`, `export_graph` methods |
| `src/telegram/main.py` or `start_bot.py` | Register `graph_router` with dispatcher |
| `src/telegram/handlers/common/` or `me.py` | Add graph commands to `/help` text |

---

## UX Flow Summary

```
User: /seed https://elifesciences.org/articles/93796
Bot:  🕸️ Building knowledge graph for: <url>
      ⏳ Resolving paper and fetching citation network...
      [5s polling loop with progress dots]
Bot:  ✅ Graph Ready!
      Title: Knowledge Graph: Organ-on-a-chip...
      📊 Nodes: 47 | 🔗 Edges: 89
      ID: a3f2b1c0...
      [Sends .json file attachment automatically]

User: /graphs
Bot:  🕸️ Your Knowledge Graphs:
      ✅ Knowledge Graph: Organ-on-a-chip...
         📊 47 nodes · 🔗 89 edges
         /graphs a3f2b1c0-...

User: /graphs a3f2b1c0-...
Bot:  [Sends .json file attachment]

User: /batch_graph https://elifesciences.org/articles/93796 DOI:10.1021/acsnano.4c02012
Bot:  🕸️ Building batch graph for 2 papers...
      [Processes each sequentially with progress]
Bot:  ✅ Batch complete! Successfully built: 2/2 graphs
```
