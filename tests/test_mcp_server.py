"""
Smriti MCP — Server Tests
===========================
Tests for MCP tools, resources, and prompts.
Uses mocked SmritiClient to avoid real API calls.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ── Adjust import path ───────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.client import SmritiClient, SmritiAPIError
from mcp.config import SmritiMCPConfig


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_context(client: SmritiClient) -> MagicMock:
    """Create a mock MCP Context with a SmritiClient in the lifespan context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"client": client}
    return ctx


def make_mock_client() -> SmritiClient:
    """Create a SmritiClient with all methods mocked."""
    config = SmritiMCPConfig(api_key="chrn_test_key")
    client = SmritiClient(config)
    client.ingest = AsyncMock()
    client.query = AsyncMock()
    client.health = AsyncMock()
    client.root_health = AsyncMock()
    client.usage = AsyncMock()
    client.list_connectors = AsyncMock()
    return client


# ── Tool Tests ────────────────────────────────────────────────────────────────

class TestSmritiRemember:
    @pytest.mark.asyncio
    async def test_remember_success(self):
        from mcp.server import smriti_remember

        client = make_mock_client()
        client.ingest.return_value = {
            "ingested_count": 1,
            "event_ids": ["evt_abc123"],
            "svo_tuples": [
                {"subject": "Alice", "verb": "quit", "object": "her job at Google", "confidence": 0.92}
            ],
            "turn_ids": ["turn_001"],
        }

        ctx = make_mock_context(client)
        result = await smriti_remember(
            text="Alice quit her job at Google",
            ctx=ctx,
        )

        assert "Remembered 1 event" in result
        assert "[Alice]" in result
        assert "[quit]" in result
        assert "confidence: 92%" in result
        client.ingest.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_remember_with_options(self):
        from mcp.server import smriti_remember

        client = make_mock_client()
        client.ingest.return_value = {
            "ingested_count": 1,
            "event_ids": ["evt_def456"],
            "svo_tuples": [],
            "turn_ids": ["turn_002"],
        }

        ctx = make_mock_context(client)
        result = await smriti_remember(
            text="Daily standup meeting",
            source_id="work-calendar",
            parse_svo=False,
            scope="work",
            timestamp="2026-07-15T09:00:00Z",
            ctx=ctx,
        )

        assert "Remembered 1 event" in result
        call_kwargs = client.ingest.call_args.kwargs
        assert call_kwargs["source_id"] == "work-calendar"
        assert call_kwargs["parse_svo"] is False
        assert call_kwargs["scope"] == "work"

    @pytest.mark.asyncio
    async def test_remember_api_error(self):
        from mcp.server import smriti_remember

        client = make_mock_client()
        client.ingest.side_effect = SmritiAPIError(429, "Event quota exceeded")

        ctx = make_mock_context(client)
        result = await smriti_remember(text="test", ctx=ctx)

        assert "❌" in result
        assert "quota" in result.lower()


class TestSmritiRecall:
    @pytest.mark.asyncio
    async def test_recall_with_results(self):
        from mcp.server import smriti_recall

        client = make_mock_client()
        client.query.return_value = {
            "results": [
                {
                    "event": {
                        "id": "evt_abc",
                        "source_id": "test",
                        "subject": "User",
                        "verb": "learned",
                        "object": "Rust",
                        "timestamp": "2026-07-15T10:00:00Z",
                        "confidence": 0.95,
                    },
                    "relevance_score": 0.87,
                    "provenance": "semantic_search",
                }
            ],
            "total_found": 1,
            "query_time_ms": 42.5,
        }

        ctx = make_mock_context(client)
        result = await smriti_recall(query="programming languages", ctx=ctx)

        assert "Found 1 memory" in result
        assert "[User]" in result
        assert "[learned]" in result
        assert "[Rust]" in result
        assert "42ms" in result

    @pytest.mark.asyncio
    async def test_recall_no_results(self):
        from mcp.server import smriti_recall

        client = make_mock_client()
        client.query.return_value = {
            "results": [],
            "total_found": 0,
            "query_time_ms": 5.0,
        }

        ctx = make_mock_context(client)
        result = await smriti_recall(query="quantum physics", ctx=ctx)

        assert "No memories found" in result

    @pytest.mark.asyncio
    async def test_recall_with_filters(self):
        from mcp.server import smriti_recall

        client = make_mock_client()
        client.query.return_value = {
            "results": [], "total_found": 0, "query_time_ms": 3.0
        }

        ctx = make_mock_context(client)
        await smriti_recall(
            query="meetings",
            max_results=5,
            source_id="work",
            time_range_start="2026-07-01T00:00:00Z",
            time_range_end="2026-07-15T23:59:59Z",
            scope="work",
            ctx=ctx,
        )

        call_kwargs = client.query.call_args.kwargs
        assert call_kwargs["max_results"] == 5
        assert call_kwargs["source_ids"] == ["work"]
        assert call_kwargs["time_range_start"] == "2026-07-01T00:00:00Z"
        assert call_kwargs["scope"] == "work"


class TestSmritiTimeline:
    @pytest.mark.asyncio
    async def test_timeline_with_events(self):
        from mcp.server import smriti_timeline

        client = make_mock_client()
        client.query.return_value = {
            "results": [
                {
                    "event": {
                        "id": "evt_1",
                        "source_id": "test",
                        "subject": "Team",
                        "verb": "deployed",
                        "object": "v2.0",
                        "timestamp": "2026-07-10T14:00:00Z",
                        "confidence": 0.9,
                    },
                    "relevance_score": 0.8,
                    "provenance": "temporal_filter",
                }
            ],
            "total_found": 1,
            "query_time_ms": 20.0,
        }

        ctx = make_mock_context(client)
        result = await smriti_timeline(
            time_range_start="2026-07-01T00:00:00Z",
            time_range_end="2026-07-15T23:59:59Z",
            ctx=ctx,
        )

        assert "Timeline" in result
        assert "[Team]" in result
        assert "[deployed]" in result

    @pytest.mark.asyncio
    async def test_timeline_empty(self):
        from mcp.server import smriti_timeline

        client = make_mock_client()
        client.query.return_value = {
            "results": [], "total_found": 0, "query_time_ms": 3.0,
        }

        ctx = make_mock_context(client)
        result = await smriti_timeline(
            time_range_start="2020-01-01T00:00:00Z",
            ctx=ctx,
        )

        assert "No events found" in result


class TestSmritiForget:
    @pytest.mark.asyncio
    async def test_forget_finds_matches(self):
        from mcp.server import smriti_forget

        client = make_mock_client()
        client.query.return_value = {
            "results": [
                {
                    "event": {
                        "id": "evt_old_fact",
                        "source_id": "test",
                        "subject": "User",
                        "verb": "uses",
                        "object": "React",
                        "timestamp": "2026-06-01T00:00:00Z",
                        "confidence": 0.9,
                    },
                    "relevance_score": 0.8,
                    "provenance": "semantic_search",
                }
            ],
            "total_found": 1,
            "query_time_ms": 10.0,
        }

        ctx = make_mock_context(client)
        result = await smriti_forget(query="User uses React", ctx=ctx)

        assert "Found 1 memory" in result
        assert "smriti_remember" in result
        assert "[User]" in result

    @pytest.mark.asyncio
    async def test_forget_no_matches(self):
        from mcp.server import smriti_forget

        client = make_mock_client()
        client.query.return_value = {
            "results": [], "total_found": 0, "query_time_ms": 5.0,
        }

        ctx = make_mock_context(client)
        result = await smriti_forget(query="nonexistent fact", ctx=ctx)

        assert "No memories found" in result
        assert "Nothing to forget" in result


class TestSmritiHealth:
    @pytest.mark.asyncio
    async def test_health_success(self):
        from mcp.server import smriti_health

        client = make_mock_client()
        client.health.return_value = {
            "status": "healthy",
            "stores": {
                "postgres_events": 5000,
                "pgvector_embeddings": 4800,
            },
        }

        ctx = make_mock_context(client)
        result = await smriti_health(ctx=ctx)

        assert "HEALTHY" in result
        assert "5000" in result
        assert "4800" in result

    @pytest.mark.asyncio
    async def test_health_fallback(self):
        from mcp.server import smriti_health

        client = make_mock_client()
        client.health.side_effect = SmritiAPIError(500, "Internal error")
        client.root_health.return_value = {
            "service": "Smriti",
            "version": "0.2.0",
            "status": "operational",
        }

        ctx = make_mock_context(client)
        result = await smriti_health(ctx=ctx)

        assert "OPERATIONAL" in result
        assert "0.2.0" in result


class TestSmritiUsage:
    @pytest.mark.asyncio
    async def test_usage_success(self):
        from mcp.server import smriti_usage

        client = make_mock_client()
        client.usage.return_value = {
            "source_id": "test",
            "tier": "explorer",
            "usage": {
                "events": {"used": 500, "limit": 10000, "remaining": 9500},
                "orchestration": {"used": 10, "limit": 1000, "remaining": 990},
                "connectors": {"used": 1, "limit": 3},
            },
            "limits": {"retention_days": 30},
            "period_start": "2026-07-01T00:00:00Z",
        }

        ctx = make_mock_context(client)
        result = await smriti_usage(ctx=ctx)

        assert "EXPLORER" in result
        assert "500" in result
        assert "10,000" in result
        assert "30 days" in result


# ── Resource Tests ────────────────────────────────────────────────────────────

class TestResources:
    @pytest.mark.asyncio
    async def test_config_resource(self):
        from mcp.server import resource_config

        with patch.dict(os.environ, {
            "SMRITI_API_KEY": "chrn_test",
            "SMRITI_SOURCE_ID": "test-src",
        }):
            result = await resource_config()
            data = json.loads(result)
            assert data["source_id"] == "test-src"
            assert data["api_key_set"] is True
            assert "api_key" not in data  # Should NOT expose the actual key


# ── Prompt Tests ──────────────────────────────────────────────────────────────

class TestPrompts:
    @pytest.mark.asyncio
    async def test_memory_chat_prompt(self):
        from mcp.server import memory_chat

        result = await memory_chat()
        assert "smriti_remember" in result
        assert "smriti_recall" in result
        assert "REMEMBER" in result

    @pytest.mark.asyncio
    async def test_daily_recap_prompt(self):
        from mcp.server import daily_recap

        result = await daily_recap()
        assert "smriti_timeline" in result
        assert "recap" in result.lower()

    @pytest.mark.asyncio
    async def test_knowledge_extraction_prompt(self):
        from mcp.server import knowledge_extraction

        result = await knowledge_extraction()
        assert "smriti_remember" in result
        assert "extraction" in result.lower()
