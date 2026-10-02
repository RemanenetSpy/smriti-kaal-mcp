"""
Smriti MCP — CLI Entry Point
=============================
Run with: python -m smriti.mcp

Supports:
    python -m smriti.mcp                    → stdio transport (default)
    python -m smriti.mcp --transport sse    → SSE transport
    python -m smriti.mcp --port 3000        → Custom SSE port
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="smriti-mcp",
        description="Smriti MCP Server — Temporal AI Memory for any MCP host",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for SSE transport (default: 8080)",
    )

    args = parser.parse_args()

    # Import here to avoid loading everything just for --help
    from .server import run_server

    try:
        run_server(transport=args.transport, port=args.port)
    except KeyboardInterrupt:
        print("\nSmriti MCP server stopped.", file=sys.stderr)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
