"""
Smriti MCP — Configuration
==========================
All settings loaded from environment variables.
Remote API mode only (HTTP client to deployed Smriti API).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SmritiMCPConfig:
    """Immutable configuration for the Smriti MCP server."""

    # ── Required ──────────────────────────────────────────────────────────────
    api_key: str = field(default="")

    # ── API Connection ────────────────────────────────────────────────────────
    base_url: str = field(default="https://smriti-kaal.vercel.app")

    # ── Defaults ──────────────────────────────────────────────────────────────
    source_id: str = field(default="mcp-client")
    scope: str = field(default="default")
    max_results: int = field(default=20)
    parse_svo: bool = field(default=True)

    # ── HTTP Client ───────────────────────────────────────────────────────────
    timeout_seconds: float = field(default=30.0)
    max_retries: int = field(default=3)

    # ── Supabase BYODB (optional) ─────────────────────────────────────────────
    # Set SMRITI_SUPABASE_URL to route memory storage to your own Supabase DB.
    # Leave unset to use the default Smriti cloud storage.
    supabase_url: str = field(default="")

    def validate(self) -> None:
        """Validate that all required config is present."""
        if not self.api_key:
            print(
                "ERROR: SMRITI_API_KEY environment variable is required.\n"
                "Get your free API key at: https://smriti-kaal.vercel.app\n"
                "Then set it: export SMRITI_API_KEY=chrn_your_key_here",
                file=sys.stderr,
            )
            raise ValueError("SMRITI_API_KEY is required but not set.")


def load_config() -> SmritiMCPConfig:
    """Load configuration from environment variables."""
    config = SmritiMCPConfig(
        api_key=os.getenv("SMRITI_API_KEY", ""),
        base_url=os.getenv(
            "SMRITI_BASE_URL",
            "https://smriti-kaal.vercel.app",
        ),
        source_id=os.getenv("SMRITI_SOURCE_ID", "mcp-client"),
        scope=os.getenv("SMRITI_SCOPE", "default"),
        max_results=int(os.getenv("SMRITI_MAX_RESULTS", "20")),
        parse_svo=os.getenv("SMRITI_PARSE_SVO", "true").lower() in ("true", "1", "yes"),
        timeout_seconds=float(os.getenv("SMRITI_TIMEOUT", "30.0")),
        max_retries=int(os.getenv("SMRITI_MAX_RETRIES", "3")),
        supabase_url=os.getenv("SMRITI_SUPABASE_URL", ""),
    )
    return config
