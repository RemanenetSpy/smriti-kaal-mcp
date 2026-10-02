# Smriti MCP Server

> **Model Context Protocol server for Smriti — Temporal AI Memory**
>
> Give any MCP-compatible AI host (Claude, Cursor, VS Code, Windsurf) structured temporal memory powered by S-V-O causal event tuples.

---

## Quick Start

### 1. Install & Run

```bash
# Option A: Zero-install via uvx (recommended)
uvx smriti-kaal-mcp

# Option B: Install via pip
pip install smriti-kaal-mcp
```

### 2. Set your API key

```bash
# Get a free API key at: https://smriti-kaal.vercel.app
export SMRITI_API_KEY="chrn_your_api_key_here"
```

### 3. Add to your MCP host

**Claude Desktop** — Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "smriti": {
      "command": "uvx",
      "args": ["smriti-kaal-mcp"],
      "env": {
        "SMRITI_API_KEY": "chrn_your_api_key_here"
      }
    }
  }
}
```

**Cursor** — Edit `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "smriti": {
      "command": "uvx",
      "args": ["smriti-kaal-mcp"],
      "env": {
        "SMRITI_API_KEY": "chrn_your_api_key_here",
        "SMRITI_SOURCE_ID": "my-project"
      }
    }
  }
}
```

### 4. Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uvx smriti-kaal-mcp
```

---

## Tools

| Tool | Purpose | Key Args |
|------|---------|----------|
| `smriti_remember` | Store new memories (text → S-V-O extraction) | `text`, `source_id`, `scope`, `timestamp` |
| `smriti_recall` | Search memories (semantic + temporal + entity) | `query`, `max_results`, `time_range_start/end` |
| `smriti_timeline` | Chronological event timeline | `time_range_start`, `time_range_end`, `scope` |
| `smriti_forget` | Find memories to supersede | `query`, `scope` |
| `smriti_health` | Service health check | — |
| `smriti_usage` | API usage stats & tier limits | — |

### `smriti_remember`

Stores a new memory. Text is automatically decomposed into **S-V-O (Subject-Verb-Object) causal event tuples**.

```
Input:  "Alice quit her job at Google because she got an offer from OpenAI"
Output: [Alice] [quit] [her job at Google]
        [Alice] [got] [an offer from OpenAI]
```

Old facts are **automatically superseded** when contradicted — history is preserved, never deleted.

### `smriti_recall`

Searches memories using a **3-phase hybrid retrieval pipeline**:

1. **Semantic search** — pgvector cosine similarity (meaning-based)
2. **Temporal filtering** — PostgreSQL time range queries
3. **Entity multi-hop** — follows entity connections across memories

### `smriti_timeline`

Optimized for temporal queries. Low semantic weight, high temporal weight.

### `smriti_forget`

Finds matching memories and guides you through supersession. Smriti **never deletes** — it marks old facts as superseded and stores corrected facts.

---

## Resources

| URI | Description |
|-----|-------------|
| `smriti://status` | Live service health and memory counts |
| `smriti://usage` | Current API usage stats and tier limits |
| `smriti://config` | MCP server configuration (non-sensitive) |

---

## Prompts

| Name | Purpose |
|------|---------|
| `memory-chat` | System prompt for memory-augmented conversations |
| `daily-recap` | Template for timeline-based daily/weekly recap |
| `knowledge-extraction` | Bulk knowledge ingestion from documents |

---

## Configuration

All settings via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SMRITI_API_KEY` | *(required)* | Your Smriti API key (`chrn_...`) |
| `SMRITI_BASE_URL` | `https://smriti-kaal.vercel.app` | API base URL |
| `SMRITI_SOURCE_ID` | `mcp-client` | Default source namespace |
| `SMRITI_SCOPE` | `default` | Default memory scope |
| `SMRITI_MAX_RESULTS` | `20` | Default max results for queries |
| `SMRITI_PARSE_SVO` | `true` | Enable S-V-O extraction by default |
| `SMRITI_TIMEOUT` | `30.0` | HTTP timeout (seconds) |
| `SMRITI_MAX_RETRIES` | `3` | Max HTTP retries for transient errors |
| `SMRITI_SUPABASE_URL` | *(unset)* | Session Pooler URL to route memory to your own Supabase DB (BYODB). Leave unset to use Smriti's cloud storage. |

---

## Transport

```bash
# stdio (default) — for Claude Desktop, Cursor, local use
uvx smriti-kaal-mcp
# or when installed with pip:
smriti-kaal-mcp

# SSE — for remote/multi-client access
smriti-kaal-mcp --transport sse --port 8080
```

---

## Architecture

```
┌────────────────────────────────────────┐
│  MCP Host (Claude / Cursor / VS Code)  │
│  ┌──────────────────────────────────┐  │
│  │          MCP Client              │  │
│  └──────────────┬───────────────────┘  │
└─────────────────┼──────────────────────┘
                  │ JSON-RPC 2.0 (stdio)
                  │
┌─────────────────┼──────────────────────┐
│  Smriti MCP Server (this package)      │
│  ┌──────────────┴───────────────────┐  │
│  │  FastMCP (server.py)             │  │
│  │  6 Tools │ 3 Resources │ 3 Prompts │
│  └──────────────┬───────────────────┘  │
│  ┌──────────────┴───────────────────┐  │
│  │  SmritiClient (client.py)        │  │
│  │  HTTP client → Smriti REST API   │  │
│  └──────────────┬───────────────────┘  │
└─────────────────┼──────────────────────┘
                  │ HTTPS
                  │
┌─────────────────┼──────────────────────┐
│  Smriti API (HuggingFace Spaces)       │
│  FastAPI + PostgreSQL + pgvector       │
│  SVO Parser + Supersession Engine      │
└────────────────────────────────────────┘
```

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all MCP tests
python -m pytest tests/test_mcp_client.py tests/test_mcp_server.py -v
```

---

## Example Conversation

Once connected, the AI naturally uses Smriti memory:

> **You:** I just switched our backend from Express to FastAPI
>
> **AI:** *(calls `smriti_remember` with "User switched backend from Express to FastAPI")*
> Got it! I've noted the backend migration from Express to FastAPI.
>
> **You:** What tech stack are we using?
>
> **AI:** *(calls `smriti_recall` with "tech stack")*
> Based on your memory: You recently switched the backend to **FastAPI** (previously Express). [Other recalled context...]
>
> **You:** What happened this week?
>
> **AI:** *(calls `smriti_timeline` for last 7 days)*
> Here's your weekly recap:
> - Jul 15: Switched backend from Express to FastAPI
> - Jul 16: ...

---

## File Structure

```
smriti/mcp/
├── __init__.py              # Package metadata
├── __main__.py              # CLI entry point (python -m smriti.mcp)
├── server.py                # FastMCP server — tools, resources, prompts
├── client.py                # HTTP client for Smriti REST API
├── config.py                # Environment variable configuration
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── claude_desktop_config.json  # Example Claude Desktop config
└── cursor_config.json          # Example Cursor config
```
