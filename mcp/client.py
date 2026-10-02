"""
Smriti MCP — HTTP Client
=========================
Async HTTP client that wraps the Smriti REST API.
Handles authentication, retries, timeouts, and error mapping.

All methods return plain Python dicts — the MCP server layer
converts them to tool responses.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Any, Optional

import httpx

from .config import SmritiMCPConfig

# All logging goes to stderr (MCP requirement — stdout is the JSON-RPC channel)
logger = logging.getLogger("smriti.mcp.client")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class SmritiAPIError(Exception):
    """Raised when the Smriti API returns an error response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Smriti API error {status_code}: {detail}")


class SmritiClient:
    """
    Async HTTP client for the Smriti temporal memory API.

    Usage:
        client = SmritiClient(config)
        await client.connect()
        result = await client.ingest("User started learning Rust")
        await client.close()
    """

    def __init__(self, config: SmritiMCPConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Initialize the HTTP client with auth headers."""
        headers: dict[str, str] = {
            "X-API-Key": self.config.api_key,
            "Content-Type": "application/json",
            "User-Agent": "smriti-mcp/0.1.0",
        }
        # Forward Supabase BYODB URL when configured — applies to all tool calls
        if self.config.supabase_url:
            headers["X-Supabase-Url"] = self.config.supabase_url
            logger.info("Supabase BYODB active — memory routed to user's Supabase DB")

        self._client = httpx.AsyncClient(
            base_url=self.config.base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(self.config.timeout_seconds),
        )
        logger.info(f"SmritiClient connected to {self.config.base_url}")


    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("SmritiClient disconnected")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _ensure_connected(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("SmritiClient not connected. Call connect() first.")
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic."""
        client = self._ensure_connected()
        last_error: Exception | None = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                )

                if response.status_code == 200:
                    return response.json()

                # Non-retryable errors
                if response.status_code in (400, 401, 403, 404, 409, 422):
                    detail = self._extract_error_detail(response)
                    raise SmritiAPIError(response.status_code, detail)

                # Retryable errors (429, 500, 502, 503, 504)
                detail = self._extract_error_detail(response)
                last_error = SmritiAPIError(response.status_code, detail)
                logger.warning(
                    f"Retryable error (attempt {attempt}/{self.config.max_retries}): "
                    f"{response.status_code} {detail}"
                )

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Timeout (attempt {attempt}/{self.config.max_retries}): {e}"
                )
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    f"Connection error (attempt {attempt}/{self.config.max_retries}): {e}"
                )
            except SmritiAPIError:
                raise  # Non-retryable, already raised

        # All retries exhausted
        raise SmritiAPIError(
            503,
            f"All {self.config.max_retries} retries exhausted. Last error: {last_error}",
        )

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        """Extract a human-readable error message from an API response."""
        try:
            data = response.json()
            return data.get("detail", str(data))
        except Exception:
            return response.text[:500]

    # ── Public API methods ────────────────────────────────────────────────────

    async def ingest(
        self,
        text: str,
        source_id: str | None = None,
        parse_svo: bool = True,
        timestamp: str | None = None,
        scope: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Ingest text into Smriti temporal memory.

        The text is automatically decomposed into S-V-O (Subject-Verb-Object)
        causal event tuples and stored with bi-temporal validity.

        Args:
            text: The memory to store (e.g., "User switched from React to Vue")
            source_id: Namespace label for this memory source
            parse_svo: Whether to extract S-V-O tuples (uses LLM)
            timestamp: ISO timestamp override (default: now)
            scope: Logical namespace (e.g., "work", "personal")
            metadata: Additional metadata to attach to events

        Returns:
            Dict with ingested_count, event_ids, svo_tuples, turn_ids
        """
        event: dict[str, Any] = {"text": text}
        if timestamp:
            event["timestamp"] = timestamp
        if metadata:
            event["metadata"] = metadata
        if scope:
            event["scope"] = scope

        payload = {
            "source_id": source_id or self.config.source_id,
            "events": [event],
            "parse_svo": parse_svo,
        }
        if scope:
            payload["scope"] = scope

        return await self._request("POST", "/ingest", json=payload)

    async def query(
        self,
        query: str,
        max_results: int | None = None,
        source_ids: list[str] | None = None,
        time_range_start: str | None = None,
        time_range_end: str | None = None,
        scope: str | None = None,
        semantic_weight: float = 0.5,
    ) -> dict[str, Any]:
        """
        Search Smriti temporal memory with hybrid retrieval.

        Uses a 3-phase pipeline:
        1. Semantic search via pgvector (fuzzy recall)
        2. Temporal filtering via PostgreSQL (deterministic time ranges)
        3. Entity multi-hop (capitalized entity matching)

        Args:
            query: Natural language search query
            max_results: Maximum results to return
            source_ids: Filter by specific source namespaces
            time_range_start: ISO timestamp for range start
            time_range_end: ISO timestamp for range end
            scope: Restrict to a specific scope
            semantic_weight: Balance between semantic (1.0) and temporal (0.0)

        Returns:
            Dict with results (list of events), total_found, query_time_ms
        """
        payload: dict[str, Any] = {
            "query": query,
            "max_results": max_results or self.config.max_results,
            "semantic_weight": semantic_weight,
        }
        if source_ids:
            payload["source_ids"] = source_ids
        if scope:
            payload["scope"] = scope

        if time_range_start or time_range_end:
            time_range: dict[str, str] = {}
            if time_range_start:
                time_range["start"] = time_range_start
            if time_range_end:
                time_range["end"] = time_range_end
            payload["time_range"] = time_range

        return await self._request("POST", "/query", json=payload)

    async def health(self) -> dict[str, Any]:
        """
        Check Smriti API health status.

        Returns:
            Dict with status, postgres_events count, pgvector_embeddings count
        """
        return await self._request("GET", "/health")

    async def usage(self) -> dict[str, Any]:
        """
        Get current API usage statistics and tier limits.

        Returns:
            Dict with tier, usage (events/orchestration/connectors), limits
        """
        return await self._request("GET", "/billing/usage")

    async def list_connectors(self) -> list[dict[str, Any]]:
        """
        List all registered SaaS tool connectors.

        Returns:
            List of connector dicts with id, name, description, endpoints_count
        """
        result = await self._request("GET", "/connectors")
        # The API returns a list directly, not wrapped in an object
        return result if isinstance(result, list) else []

    async def root_health(self) -> dict[str, Any]:
        """
        Basic health check (GET /).

        Returns:
            Dict with service name, version, status
        """
        return await self._request("GET", "/")
