<p align="center">
  <img src="https://img.shields.io/badge/Status-Live-4ADE80?style=for-the-badge" alt="Live" />
  <img src="https://img.shields.io/badge/PyPI-smriti--kaal--mcp-blue?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/MCP-Claude%20%7C%20Cursor%20%7C%20VS%20Code-6B7194?style=for-the-badge" alt="MCP" />
  <img src="https://img.shields.io/badge/Free%20Tier-10K%20events%2Fmo-C7AB6B?style=for-the-badge" alt="Free" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT" />
</p>

<h1 align="center">🕰️ Smriti — Temporal Event Memory</h1>

<p align="center">
  <b>Give your AI agents and business workflows an auditable ledger of what happened, when, and with whom.</b><br>
  Smriti decomposes events into Subject-Verb-Object tuples, stores them in a Bi-Temporal PostgreSQL architecture,<br>and lets AI reason precisely across time — without hallucination.
</p>

---

## 📖 What is Smriti?

**The Problem:** Traditional "agent memory" relies on fuzzy vector databases that suffer from temporal drift. When tracking deals, deployments, contracts, or multi-step workflows, you need a deterministic event ledger — not a chatbot guessing from old embeddings.

**The Solution:** Smriti is a **temporal event memory layer** — a bi-temporal hippocampus for AI agents that tracks state changes perfectly across systems and sessions.

| Feature | Smriti (Event Memory) | Traditional RAG (Chat Memory) |
|---|---|---|
| **Structure** | **SVO Tuples:** Tracks concrete actions (`Agent → Deployed → Build42`) | **Vector Sludge:** Dumps unstructured text into a vector DB |
| **Time** | **Bi-Temporal:** Tracks both *when it happened* and *when it was recorded* | **Timeless:** Cannot distinguish old facts from current state |
| **Updates** | **Supersession:** Safely overrides state without deleting history | **Overwrite:** Hard deletes or creates confusing duplicates |

---

## 🚀 Quick Start (5 Minutes)

**Step 1 — Get a free API key**
```bash
curl -X POST "https://smriti-kaal.vercel.app/billing/keys?tier=explorer"
```

**Step 2 — Store a memory**
```bash
curl -X POST https://smriti-kaal.vercel.app/ingest \
  -H "X-API-Key: chrn_your_key" \
  -H "Content-Type: application/json" \
  -d '{"source_id": "demo", "events": [{"text": "Alice joined as Lead Engineer on July 15"}]}'
```

**Step 3 — Recall it**
```bash
curl -X POST https://smriti-kaal.vercel.app/query \
  -H "X-API-Key: chrn_your_key" \
  -H "Content-Type: application/json" \
  -d '{"query": "Who joined the team recently?"}'
```

**Response:**
```json
{
  "results": [
    {
      "subject": "Alice",
      "verb": "joined",
      "object": "the team as Lead Engineer",
      "timestamp": "2026-07-15T00:00:00Z",
      "confidence_score": 0.94
    }
  ]
}
```

---

## 🔌 MCP Server — Claude, Cursor, VS Code

Smriti ships with a built-in **Model Context Protocol (MCP)** server. It runs as a lightweight local process — no backend to host, no infrastructure to manage.

### Install

```bash
pip install smriti-kaal-mcp
# or zero-install via uvx (no pip needed):
uvx smriti-kaal-mcp
```

### Configure Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "smriti": {
      "command": "uvx",
      "args": ["smriti-kaal-mcp"],
      "env": {
        "SMRITI_API_KEY": "chrn_your_key_here",
        "SMRITI_SOURCE_ID": "claude-desktop"
      }
    }
  }
}
```

### Configure Cursor

Add to `.cursor/mcp.json` in your project root:
```json
{
  "mcpServers": {
    "smriti": {
      "command": "uvx",
      "args": ["smriti-kaal-mcp"],
      "env": {
        "SMRITI_API_KEY": "chrn_your_key_here",
        "SMRITI_SOURCE_ID": "cursor-project"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | What It Does |
|------|-------------|
| `smriti_remember` | Store text — auto-extracts causal SVO events |
| `smriti_recall` | Hybrid search (semantic + temporal) across all memories |
| `smriti_timeline` | Generate a chronological timeline of events |
| `smriti_forget` | Supersede outdated memories cleanly |
| `smriti_health` | View service health and DB status |

---

## 🐘 Bring Your Own Database (BYODB)

Keep your memory data in your own infrastructure using **Supabase** (PostgreSQL + pgvector). Just pass your Session Pooler URL as a header — no code changes required:

```bash
curl -X POST https://smriti-kaal.vercel.app/ingest \
  -H "X-API-Key: chrn_your_key" \
  -H "X-Supabase-Url: postgresql://postgres.xxxx:YOUR_PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres" \
  -H "Content-Type: application/json" \
  -d '{"source_id": "my-app", "events": [{"text": "Alice joined the team"}]}'
```

👉 **[Full 3-step BYODB setup guide →](./supabase/README.md)**

---

## 🏗️ Architecture

When you send text to Smriti, it passes through four discrete layers:

1. **Ingest Gate** — Accepts raw text from chat logs, emails, or code
2. **Decomposition** — LLM extracts structured `Subject → Verb → Object` tuples
3. **Temporal Binding** — Assigns exact temporal boundaries to track state changes over time
4. **Dual-Store Indexing** — Saves to PostgreSQL (exact chronological queries) + pgvector (semantic search)

---

## 📖 REST API Reference

**Base URL:** `https://smriti-kaal.vercel.app`  
**Auth:** `X-API-Key: chrn_your_key`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/billing/keys` | POST | Generate a new API key |
| `/ingest` | POST | Convert raw text into structured memories |
| `/query` | POST | Natural language memory retrieval |
| `/agent/run` | POST | Chat with the memory-aware LangGraph agent |
| `/health` | GET | System uptime and DB status |

---

## 💻 Integration Examples

### Node.js
```javascript
const headers = { "X-API-Key": "chrn_...", "Content-Type": "application/json" };

await fetch("https://smriti-kaal.vercel.app/ingest", {
  method: "POST", headers,
  body: JSON.stringify({ source_id: "app", events: [{ text: "Upgraded to Pro" }] })
});

const res = await fetch("https://smriti-kaal.vercel.app/query", {
  method: "POST", headers,
  body: JSON.stringify({ query: "Who upgraded?" })
});
console.log(await res.json());
```

### Python
```python
import httpx

API = "https://smriti-kaal.vercel.app"
HEADERS = {"X-API-Key": "chrn_..."}

httpx.post(f"{API}/ingest", headers=HEADERS, json={
    "source_id": "my-app",
    "events": [{"text": "User completed onboarding on July 15"}]
})

result = httpx.post(f"{API}/query", headers=HEADERS, json={"query": "What did the user do?"})
print(result.json()["results"])
```

---

## ⚙️ Environment Variables (MCP)

| Variable | Required | Description |
|---|---|---|
| `SMRITI_API_KEY` | ✅ | Your API key (`chrn_...`) from [smriti-kaal.vercel.app](https://smriti-kaal.vercel.app) |
| `SMRITI_SOURCE_ID` | No | Namespace for your memories (e.g. `claude-desktop`, `my-project`) |
| `SMRITI_SUPABASE_URL` | No | Session Pooler URL to route memory to your own Supabase DB |
| `SMRITI_SCOPE` | No | Memory scope (`default` unless you need multi-tenant isolation) |
| `SMRITI_BASE_URL` | No | Override the API base URL (advanced) |

---

## 📊 Pricing

| Tier | Price | Limits |
|---|---|---|
| **Explorer** | Free | 10,000 events/mo · 3 connected tools |
| **Builder** | \$49/mo | 500,000 events/mo · 25 tools |
| **Scale** | \$249/mo | 5,000,000 events/mo · unlimited tools |

Manage keys and view memory timelines at **[smriti-kaal.vercel.app](https://smriti-kaal.vercel.app)**

---

## 🔒 Security

- All API requests require a bearer token (`X-API-Key`)
- API keys are scoped per `source_id` — one application cannot read another's memories
- BYODB mode: your data never touches Smriti's cloud storage
- MCP server runs locally on your machine; only outbound HTTPS calls are made

---

## 📄 License

MIT © 2026 Smriti / Chronos Labs

---

<p align="center">
  <em>🕰️ Memory that persists. Context that continues.</em>
</p>
