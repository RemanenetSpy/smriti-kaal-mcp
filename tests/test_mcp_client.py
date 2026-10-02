"""
Smriti MCP — HTTP Client Tests
================================
Tests for the SmritiClient HTTP wrapper.
Uses httpx mock transport to avoid real API calls.
"""

from __future__ import annotations

import json
import pytest
import httpx

# ── Adjust import path ───────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.config import SmritiMCPConfig, load_config
from mcp.client import SmritiClient, SmritiAPIError


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_config(**overrides) -> SmritiMCPConfig:
    defaults = dict(
        api_key="chrn_test_key_123",
        base_url="https://test-api.smriti.dev",
        source_id="test-source",
        scope="default",
        max_results=10,
        parse_svo=True,
        timeout_seconds=5.0,
        max_retries=1,
    )
    defaults.update(overrides)
    return SmritiMCPConfig(**defaults)


def mock_transport(responses: dict[str, httpx.Response]) -> httpx.MockTransport:
    """Create a mock transport that returns canned responses by path."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in responses:
            return responses[path]
        return httpx.Response(404, json={"detail": f"Not found: {path}"})
    return httpx.MockTransport(handler)


# ── Config Tests ──────────────────────────────────────────────────────────────

class TestConfig:
    def test_load_defaults(self, monkeypatch):
        monkeypatch.delenv("SMRITI_API_KEY", raising=False)
        monkeypatch.delenv("SMRITI_BASE_URL", raising=False)
        config = load_config()
        assert config.api_key == ""
        assert "smriti-kaal.vercel.app" in config.base_url
        assert config.source_id == "mcp-client"

    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("SMRITI_API_KEY", "chrn_env_key")
        monkeypatch.setenv("SMRITI_BASE_URL", "https://custom.api.dev")
        monkeypatch.setenv("SMRITI_SOURCE_ID", "my-source")
        monkeypatch.setenv("SMRITI_MAX_RESULTS", "50")
        monkeypatch.setenv("SMRITI_PARSE_SVO", "false")
        config = load_config()
        assert config.api_key == "chrn_env_key"
        assert config.base_url == "https://custom.api.dev"
        assert config.source_id == "my-source"
        assert config.max_results == 50
        assert config.parse_svo is False

    def test_validate_missing_key(self):
        config = SmritiMCPConfig(api_key="")
        with pytest.raises(ValueError, match="SMRITI_API_KEY"):
            config.validate()

    def test_validate_with_key(self):
        config = SmritiMCPConfig(api_key="chrn_valid_key")
        config.validate()  # Should not raise


# ── Client Tests ──────────────────────────────────────────────────────────────

class TestSmritiClient:

    @pytest.mark.asyncio
    async def test_ingest_success(self):
        config = make_config()
        client = SmritiClient(config)

        response_data = {
            "ingested_count": 2,
            "event_ids": ["evt_abc", "evt_def"],
            "svo_tuples": [
                {"subject": "User", "verb": "learned", "object": "Rust", "confidence": 0.95}
            ],
            "turn_ids": ["turn_001"],
        }

        transport = mock_transport({
            "/ingest": httpx.Response(200, json=response_data),
        })
        client._client = httpx.AsyncClient(
            base_url=config.base_url, transport=transport
        )

        result = await client.ingest("User started learning Rust last week")
        assert result["ingested_count"] == 2
        assert len(result["event_ids"]) == 2
        assert result["svo_tuples"][0]["subject"] == "User"

        await client.close()

    @pytest.mark.asyncio
    async def test_query_success(self):
        config = make_config()
        client = SmritiClient(config)

        response_data = {
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

        transport = mock_transport({
            "/query": httpx.Response(200, json=response_data),
        })
        client._client = httpx.AsyncClient(
            base_url=config.base_url, transport=transport
        )

        result = await client.query("What has the user learned?")
        assert result["total_found"] == 1
        assert result["results"][0]["event"]["subject"] == "User"

        await client.close()

    @pytest.mark.asyncio
    async def test_health_success(self):
        config = make_config()
        client = SmritiClient(config)

        response_data = {
            "status": "healthy",
            "stores": {
                "postgres_events": 1234,
                "pgvector_embeddings": 1200,
            },
        }

        transport = mock_transport({
            "/health": httpx.Response(200, json=response_data),
        })
        client._client = httpx.AsyncClient(
            base_url=config.base_url, transport=transport
        )

        result = await client.health()
        assert result["status"] == "healthy"
        assert result["stores"]["postgres_events"] == 1234

        await client.close()

    @pytest.mark.asyncio
    async def test_usage_success(self):
        config = make_config()
        client = SmritiClient(config)

        response_data = {
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

        transport = mock_transport({
            "/billing/usage": httpx.Response(200, json=response_data),
        })
        client._client = httpx.AsyncClient(
            base_url=config.base_url, transport=transport
        )

        result = await client.usage()
        assert result["tier"] == "explorer"
        assert result["usage"]["events"]["used"] == 500

        await client.close()

    @pytest.mark.asyncio
    async def test_auth_error_not_retried(self):
        config = make_config(max_retries=3)
        client = SmritiClient(config)

        transport = mock_transport({
            "/health": httpx.Response(401, json={"detail": "Invalid API key"}),
        })
        client._client = httpx.AsyncClient(
            base_url=config.base_url, transport=transport
        )

        with pytest.raises(SmritiAPIError) as exc_info:
            await client.health()
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

        await client.close()

    @pytest.mark.asyncio
    async def test_quota_error(self):
        config = make_config()
        client = SmritiClient(config)

        transport = mock_transport({
            "/ingest": httpx.Response(
                429, json={"detail": "Event quota exceeded (10000/10000)"}
            ),
        })
        client._client = httpx.AsyncClient(
            base_url=config.base_url, transport=transport
        )

        with pytest.raises(SmritiAPIError) as exc_info:
            await client.ingest("test")
        assert exc_info.value.status_code == 429

        await client.close()

    @pytest.mark.asyncio
    async def test_connectors_success(self):
        config = make_config()
        client = SmritiClient(config)

        response_data = [
            {
                "id": "conn_001",
                "name": "Stripe",
                "description": "Payment API",
                "base_url": "https://api.stripe.com",
                "endpoints_count": 3,
                "created_at": "2026-07-01T00:00:00Z",
            }
        ]

        transport = mock_transport({
            "/connectors": httpx.Response(200, json=response_data),
        })
        client._client = httpx.AsyncClient(
            base_url=config.base_url, transport=transport
        )

        result = await client.list_connectors()
        assert len(result) == 1
        assert result[0]["name"] == "Stripe"

        await client.close()

    @pytest.mark.asyncio
    async def test_query_with_time_range(self):
        config = make_config()
        client = SmritiClient(config)

        transport = mock_transport({
            "/query": httpx.Response(200, json={
                "results": [], "total_found": 0, "query_time_ms": 5.0
            }),
        })
        client._client = httpx.AsyncClient(
            base_url=config.base_url, transport=transport
        )

        result = await client.query(
            "meetings",
            time_range_start="2026-07-01T00:00:00Z",
            time_range_end="2026-07-15T23:59:59Z",
        )
        assert result["total_found"] == 0

        await client.close()

    @pytest.mark.asyncio
    async def test_not_connected_error(self):
        config = make_config()
        client = SmritiClient(config)
        # Don't call connect()

        with pytest.raises(RuntimeError, match="not connected"):
            await client.health()

    @pytest.mark.asyncio
    async def test_connect_and_close(self):
        config = make_config()
        client = SmritiClient(config)

        await client.connect()
        assert client._client is not None

        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_auth_header_set(self):
        config = make_config(api_key="chrn_my_secret_key")
        client = SmritiClient(config)
        await client.connect()

        assert client._client.headers["X-API-Key"] == "chrn_my_secret_key"
        assert "smriti-mcp" in client._client.headers["User-Agent"]

        await client.close()
