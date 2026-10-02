"""
Smriti MCP Server
=================
Model Context Protocol server for Smriti — the Temporal AI Memory Layer.

Exposes Smriti's S-V-O (Subject-Verb-Object) causal memory as MCP primitives:
  • 6 Tools  — remember, recall, timeline, forget, health, usage
  • 3 Resources — status, usage, config
  • 3 Prompts — memory-chat, daily-recap, knowledge-extraction

Runs over stdio (default) or SSE transport.
Connect to any MCP host: Claude Desktop, Cursor, VS Code, Windsurf, etc.

Usage:
    python -m smriti.mcp                    # stdio (default)
    python -m smriti.mcp --transport sse    # SSE on port 8080
"""

from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP, Context

from .config import SmritiMCPConfig, load_config
from .client import SmritiClient, SmritiAPIError

# ── Logging (stderr only — stdout is the JSON-RPC channel) ────────────────────
logger = logging.getLogger("smriti.mcp.server")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(
    logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ── Lifespan — initialize/teardown the HTTP client ────────────────────────────

@asynccontextmanager
async def smriti_lifespan(server):
    """Manage SmritiClient lifecycle across the MCP server's lifetime."""
    config = load_config()
    config.validate()

    client = SmritiClient(config)
    await client.connect()

    logger.info("Smriti MCP server initialized — temporal memory online")

    yield {"client": client, "config": config}

    await client.close()
    logger.info("Smriti MCP server shut down")


# ── FastMCP Server ────────────────────────────────────────────────────────────

mcp_server = FastMCP(
    "smriti",
    version="0.1.0",
    description=(
        "Temporal AI Memory — Smriti gives your AI causal, structured memory. "
        "Remember what happened, when, and why — powered by S-V-O event tuples "
        "with bi-temporal validity on PostgreSQL + pgvector."
    ),
    lifespan=smriti_lifespan,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Model-controlled functions the LLM can invoke
# ═══════════════════════════════════════════════════════════════════════════════


@mcp_server.tool()
async def smriti_remember(
    text: str,
    source_id: str | None = None,
    parse_svo: bool = True,
    timestamp: str | None = None,
    scope: str | None = None,
    ctx: Context = None,
) -> str:
    """Store a new memory in Smriti's temporal memory system.

    The text is automatically decomposed into S-V-O (Subject-Verb-Object)
    causal event tuples. For example:
      "Alice quit her job at Google because she got an offer from OpenAI"
    becomes:
      [Alice] [quit] [her job at Google]
      [Alice] [got] [an offer from OpenAI]

    Old facts are automatically superseded when contradicted by new ones.
    History is preserved (never deleted), just marked as superseded.

    Args:
        text: The memory to store. Can be a single fact, a paragraph,
              or a full conversation snippet. Be descriptive.
        source_id: Optional namespace label (e.g., "my-project", "work-notes").
                   Memories from different sources are kept separate.
        parse_svo: Whether to extract structured S-V-O tuples (default: true).
                   Set to false for raw storage without decomposition.
        timestamp: ISO 8601 timestamp of when this event occurred (e.g., "2026-07-15T10:30:00Z").
                   Defaults to current time if not provided.
        scope: Logical namespace for this memory (e.g., "work", "personal", "project-x").
               Useful for organizing memories by context.
    """
    client: SmritiClient = ctx.request_context.lifespan_context["client"]

    try:
        result = await client.ingest(
            text=text,
            source_id=source_id,
            parse_svo=parse_svo,
            timestamp=timestamp,
            scope=scope,
        )

        # Format a human-readable response
        count = result.get("ingested_count", 0)
        event_ids = result.get("event_ids", [])
        svo_tuples = result.get("svo_tuples", [])

        lines = [f"✅ Remembered {count} event(s)."]

        if svo_tuples:
            lines.append("\nExtracted S-V-O tuples:")
            for svo in svo_tuples:
                s = svo.get("subject", "?")
                v = svo.get("verb", "?")
                o = svo.get("object", "?")
                conf = svo.get("confidence", 0)
                lines.append(f"  [{s}] [{v}] [{o}]  (confidence: {conf:.0%})")

        if event_ids:
            lines.append(f"\nEvent IDs: {', '.join(event_ids[:5])}")
            if len(event_ids) > 5:
                lines.append(f"  ... and {len(event_ids) - 5} more")

        return "\n".join(lines)

    except SmritiAPIError as e:
        return f"❌ Failed to store memory: {e.detail}"
    except Exception as e:
        logger.error(f"smriti_remember error: {e}", exc_info=True)
        return f"❌ Unexpected error storing memory: {str(e)}"


@mcp_server.tool()
async def smriti_recall(
    query: str,
    max_results: int = 10,
    source_id: str | None = None,
    time_range_start: str | None = None,
    time_range_end: str | None = None,
    scope: str | None = None,
    ctx: Context = None,
) -> str:
    """Search and retrieve memories from Smriti's temporal memory.

    Uses a powerful 3-phase hybrid retrieval pipeline:
    1. Semantic search — finds memories by meaning (pgvector cosine similarity)
    2. Temporal filtering — finds memories within a time range
    3. Entity multi-hop — follows entity connections across memories

    Results are ranked by combined relevance score.

    Args:
        query: Natural language search query. Be descriptive for best results.
               Examples: "What programming languages has the user learned?",
                         "meetings about the product launch",
                         "any changes to the database schema"
        max_results: Maximum number of results to return (1-100, default: 10).
        source_id: Filter by a specific source namespace.
        time_range_start: ISO 8601 timestamp for the start of the time range
                          (e.g., "2026-07-01T00:00:00Z"). Only memories after this time.
        time_range_end: ISO 8601 timestamp for the end of the time range
                        (e.g., "2026-07-15T23:59:59Z"). Only memories before this time.
        scope: Restrict results to a specific scope (e.g., "work", "personal").
    """
    client: SmritiClient = ctx.request_context.lifespan_context["client"]

    try:
        source_ids = [source_id] if source_id else None
        result = await client.query(
            query=query,
            max_results=max_results,
            source_ids=source_ids,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            scope=scope,
        )

        results = result.get("results", [])
        total = result.get("total_found", 0)
        query_ms = result.get("query_time_ms", 0)

        if not results:
            return f"No memories found matching: \"{query}\"\n(query took {query_ms:.0f}ms)"

        lines = [f"Found {total} memory(ies) in {query_ms:.0f}ms:\n"]

        for i, r in enumerate(results, 1):
            event = r.get("event", {})
            score = r.get("relevance_score", 0)
            provenance = r.get("provenance", "unknown")

            s = event.get("subject", "?")
            v = event.get("verb", "?")
            o = event.get("object", "?")
            ts = event.get("timestamp", "")

            # Format timestamp nicely if present
            ts_display = ""
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts_display = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, AttributeError):
                    ts_display = str(ts)[:16]

            lines.append(
                f"  {i}. [{s}] [{v}] [{o}]\n"
                f"     📅 {ts_display}  |  relevance: {score:.2f}  |  via: {provenance}"
            )

        return "\n".join(lines)

    except SmritiAPIError as e:
        return f"❌ Failed to search memories: {e.detail}"
    except Exception as e:
        logger.error(f"smriti_recall error: {e}", exc_info=True)
        return f"❌ Unexpected error searching memories: {str(e)}"


@mcp_server.tool()
async def smriti_timeline(
    time_range_start: str,
    time_range_end: str | None = None,
    scope: str | None = None,
    max_results: int = 20,
    ctx: Context = None,
) -> str:
    """Retrieve a chronological timeline of events within a time range.

    This is optimized for temporal queries — "What happened last week?",
    "Show me everything from March 2026", "What did I do yesterday?"

    Results are ordered chronologically (oldest first).

    Args:
        time_range_start: ISO 8601 timestamp for the start of the time range
                          (e.g., "2026-07-01T00:00:00Z").
        time_range_end: ISO 8601 timestamp for the end of the time range
                        (e.g., "2026-07-15T23:59:59Z"). Defaults to current time.
        scope: Restrict to a specific scope (e.g., "work", "personal").
        max_results: Maximum number of events to return (default: 20).
    """
    client: SmritiClient = ctx.request_context.lifespan_context["client"]

    try:
        # Use a broad query to get temporal results — the API's temporal filter
        # does the heavy lifting
        end = time_range_end or datetime.now(timezone.utc).isoformat()

        result = await client.query(
            query="*",  # Broad query to let temporal filter dominate
            max_results=max_results,
            time_range_start=time_range_start,
            time_range_end=end,
            scope=scope,
            semantic_weight=0.1,  # Minimize semantic, maximize temporal
        )

        results = result.get("results", [])

        if not results:
            return (
                f"No events found between {time_range_start} and {end}.\n"
                "Try expanding the time range or checking if events were stored."
            )

        lines = [
            f"📅 Timeline: {time_range_start[:10]} → {end[:10]}",
            f"   ({len(results)} event(s))\n",
        ]

        for r in results:
            event = r.get("event", {})
            s = event.get("subject", "?")
            v = event.get("verb", "?")
            o = event.get("object", "?")
            ts = event.get("timestamp", "")

            ts_display = ""
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts_display = dt.strftime("%b %d, %H:%M")
                except (ValueError, AttributeError):
                    ts_display = str(ts)[:16]

            lines.append(f"  • {ts_display} — [{s}] [{v}] [{o}]")

        return "\n".join(lines)

    except SmritiAPIError as e:
        return f"❌ Failed to retrieve timeline: {e.detail}"
    except Exception as e:
        logger.error(f"smriti_timeline error: {e}", exc_info=True)
        return f"❌ Unexpected error retrieving timeline: {str(e)}"


@mcp_server.tool()
async def smriti_forget(
    query: str,
    scope: str | None = None,
    max_to_forget: int = 5,
    ctx: Context = None,
) -> str:
    """Find and mark memories as forgotten (superseded).

    This does NOT delete memories — it marks them as superseded
    (sets valid_to = now), preserving full history. The memories
    will no longer appear in normal recall queries.

    This is a two-step process:
    1. First, call this tool to FIND memories matching the query
    2. Review the results, then call smriti_remember with corrected facts

    To truly "forget" something, store a superseding fact:
      smriti_remember("User no longer uses React — switched to Vue")

    Args:
        query: Description of what to forget. Should match existing memories.
        scope: Restrict to a specific scope.
        max_to_forget: Maximum number of memories to find (safety limit, default: 5).
    """
    client: SmritiClient = ctx.request_context.lifespan_context["client"]

    try:
        result = await client.query(
            query=query,
            max_results=max_to_forget,
            scope=scope,
        )

        results = result.get("results", [])

        if not results:
            return f"No memories found matching: \"{query}\"\nNothing to forget."

        lines = [
            f"Found {len(results)} memory(ies) matching \"{query}\":\n",
            "To supersede these, store a corrected fact with smriti_remember.",
            "Example: smriti_remember(\"User no longer uses React — switched to Vue\")\n",
            "Matching memories:",
        ]

        for i, r in enumerate(results, 1):
            event = r.get("event", {})
            s = event.get("subject", "?")
            v = event.get("verb", "?")
            o = event.get("object", "?")
            eid = event.get("id", "?")

            lines.append(f"  {i}. [{s}] [{v}] [{o}]  (id: {eid[:8]}...)")

        return "\n".join(lines)

    except SmritiAPIError as e:
        return f"❌ Failed to search for memories to forget: {e.detail}"
    except Exception as e:
        logger.error(f"smriti_forget error: {e}", exc_info=True)
        return f"❌ Unexpected error: {str(e)}"


@mcp_server.tool()
async def smriti_health(ctx: Context = None) -> str:
    """Check the health and status of the Smriti memory service.

    Returns the service status, event counts, and vector embedding counts.
    Useful for diagnosing connection issues or checking if the service is alive.
    """
    client: SmritiClient = ctx.request_context.lifespan_context["client"]

    try:
        # Try detailed health first, fall back to basic
        try:
            result = await client.health()
        except SmritiAPIError:
            result = await client.root_health()

        status = result.get("status", "unknown")
        stores = result.get("stores", {})

        lines = [f"🏥 Smriti Health: {status.upper()}"]

        if stores:
            events = stores.get("postgres_events", "N/A")
            vectors = stores.get("pgvector_embeddings", "N/A")
            lines.append(f"   📊 Events stored: {events}")
            lines.append(f"   🧮 Vector embeddings: {vectors}")

        # Also include basic info if available
        version = result.get("version", "")
        if version:
            lines.append(f"   📦 Version: {version}")

        return "\n".join(lines)

    except SmritiAPIError as e:
        return f"❌ Health check failed: {e.detail}"
    except Exception as e:
        logger.error(f"smriti_health error: {e}", exc_info=True)
        return f"❌ Cannot reach Smriti service: {str(e)}"


@mcp_server.tool()
async def smriti_usage(ctx: Context = None) -> str:
    """Check your current Smriti API usage statistics and tier limits.

    Shows events used/remaining, orchestration calls, connected tools,
    and your current pricing tier (Explorer/Builder/Scale).
    """
    client: SmritiClient = ctx.request_context.lifespan_context["client"]

    try:
        result = await client.usage()

        tier = result.get("tier", "unknown")
        usage = result.get("usage", {})
        limits = result.get("limits", {})

        events = usage.get("events", {})
        orch = usage.get("orchestration", {})
        connectors = usage.get("connectors", {})

        lines = [
            f"📊 Smriti Usage — Tier: {tier.upper()}",
            "",
            f"  Events:        {events.get('used', 0):,} / {events.get('limit', 0):,}  "
            f"({events.get('remaining', 0):,} remaining)",
            f"  Orchestration: {orch.get('used', 0):,} / "
            f"{'∞' if orch.get('limit', -1) == -1 else f'{orch.get(\"limit\", 0):,}'}  "
            f"({'∞' if orch.get('remaining') == 'unlimited' else f'{orch.get(\"remaining\", 0):,}'} remaining)",
            f"  Connectors:    {connectors.get('used', 0)} / "
            f"{'∞' if connectors.get('limit', -1) == -1 else connectors.get('limit', 0)}",
        ]

        retention = limits.get("retention_days", 0)
        lines.append(
            f"\n  Retention: {'unlimited' if retention == -1 else f'{retention} days'}"
        )

        period = result.get("period_start", "")
        if period:
            lines.append(f"  Period start: {period[:10]}")

        return "\n".join(lines)

    except SmritiAPIError as e:
        return f"❌ Failed to get usage stats: {e.detail}"
    except Exception as e:
        logger.error(f"smriti_usage error: {e}", exc_info=True)
        return f"❌ Unexpected error fetching usage: {str(e)}"


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES — Read-only data the application can pull into context
# ═══════════════════════════════════════════════════════════════════════════════


@mcp_server.resource("smriti://status")
async def resource_status() -> str:
    """Live Smriti service health status and memory counts."""
    config = load_config()
    client = SmritiClient(config)
    await client.connect()
    try:
        result = await client.health()
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "detail": str(e)})
    finally:
        await client.close()


@mcp_server.resource("smriti://usage")
async def resource_usage() -> str:
    """Current API usage statistics and tier limits."""
    config = load_config()
    client = SmritiClient(config)
    await client.connect()
    try:
        result = await client.usage()
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await client.close()


@mcp_server.resource("smriti://config")
async def resource_config() -> str:
    """Current MCP server configuration (non-sensitive fields only)."""
    config = load_config()
    return json.dumps(
        {
            "base_url": config.base_url,
            "source_id": config.source_id,
            "scope": config.scope,
            "max_results": config.max_results,
            "parse_svo": config.parse_svo,
            "timeout_seconds": config.timeout_seconds,
            "api_key_set": bool(config.api_key),
        },
        indent=2,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS — User-selectable instruction templates
# ═══════════════════════════════════════════════════════════════════════════════


@mcp_server.prompt()
async def memory_chat() -> str:
    """System prompt for memory-augmented conversations.

    Instructs the AI to naturally remember and recall information
    during conversation, using smriti_remember and smriti_recall.
    """
    return (
        "You are an AI assistant with persistent temporal memory powered by Smriti.\n\n"
        "MEMORY GUIDELINES:\n"
        "1. REMEMBER important facts: When the user shares preferences, decisions, "
        "events, or key information, use smriti_remember to store it.\n"
        "2. RECALL before answering: When the user asks about something that might "
        "have been discussed before, use smriti_recall to check your memory first.\n"
        "3. BE NATURAL: Don't announce every memory operation. Seamlessly weave "
        "recalled context into your responses.\n"
        "4. TEMPORAL AWARENESS: Note when things happened. Use timestamps and "
        "time ranges to provide temporally accurate answers.\n"
        "5. SUPERSESSION: When facts change (e.g., 'I switched from React to Vue'), "
        "store the new fact — Smriti automatically supersedes the old one.\n\n"
        "WHAT TO REMEMBER:\n"
        "- User preferences and settings\n"
        "- Important decisions and their reasoning\n"
        "- Project milestones and status changes\n"
        "- Technical choices and architecture decisions\n"
        "- People, relationships, and roles mentioned\n"
        "- Problems encountered and solutions found\n\n"
        "WHAT NOT TO REMEMBER:\n"
        "- Transient/throwaway questions\n"
        "- Generic greetings or chitchat\n"
        "- Information the user explicitly asks you to ignore\n"
    )


@mcp_server.prompt()
async def daily_recap() -> str:
    """Prompt template for generating a daily/weekly recap.

    Uses smriti_timeline to pull events from a time range
    and summarize what happened.
    """
    return (
        "Generate a concise recap of recent events using Smriti's temporal memory.\n\n"
        "INSTRUCTIONS:\n"
        "1. Use smriti_timeline to retrieve events from the relevant time range.\n"
        "2. Group events by theme or category (work, personal, learning, etc.).\n"
        "3. Highlight key decisions, milestones, and changes.\n"
        "4. Note any superseded facts (things that changed).\n"
        "5. Format as a clean, scannable summary.\n\n"
        "SUGGESTED TIME RANGES:\n"
        "- Daily recap: last 24 hours\n"
        "- Weekly recap: last 7 days\n"
        "- Monthly recap: last 30 days\n\n"
        "Start by asking the user what time range they'd like to review, "
        "or default to the last 24 hours.\n"
    )


@mcp_server.prompt()
async def knowledge_extraction() -> str:
    """Prompt for bulk knowledge ingestion from documents or conversations.

    Instructs the AI to read content and extract key facts into memory
    using smriti_remember.
    """
    return (
        "You are a knowledge extraction assistant powered by Smriti temporal memory.\n\n"
        "INSTRUCTIONS:\n"
        "1. Read the provided content carefully.\n"
        "2. Identify key facts, events, decisions, and relationships.\n"
        "3. For each significant piece of information, use smriti_remember to store it.\n"
        "4. Use descriptive text that captures the WHO, WHAT, WHEN, and WHY.\n"
        "5. Set appropriate timestamps if dates are mentioned in the content.\n"
        "6. Use scopes to organize by topic (e.g., 'project-x', 'meeting-notes').\n\n"
        "EXTRACTION PRIORITIES:\n"
        "- Decisions and their rationale\n"
        "- Action items and deadlines\n"
        "- Key metrics and numbers\n"
        "- People and their roles/responsibilities\n"
        "- Status changes and milestones\n"
        "- Technical specifications and constraints\n\n"
        "After extraction, provide a summary of what was stored.\n"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Server runner (used by __main__.py)
# ═══════════════════════════════════════════════════════════════════════════════


def run_server(transport: str = "stdio", port: int = 8080) -> None:
    """Run the MCP server with the specified transport."""
    logger.info(f"Starting Smriti MCP server (transport={transport})")

    if transport == "stdio":
        mcp_server.run(transport="stdio")
    elif transport == "sse":
        mcp_server.run(transport="sse", port=port)
    else:
        logger.error(f"Unknown transport: {transport}")
        raise ValueError(f"Unsupported transport: {transport}. Use 'stdio' or 'sse'.")
