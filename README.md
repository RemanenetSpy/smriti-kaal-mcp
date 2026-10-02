---
title: Smriti — Temporal Event Memory for Business Workflows
emoji: 🕰️
colorFrom: red
colorTo: gray
sdk: docker
pinned: false
---

<p align="center">
  <img src="https://img.shields.io/badge/Status-Live-4ADE80?style=for-the-badge" alt="Live" />
  <img src="https://img.shields.io/badge/MCP-Claude%20%7C%20Cursor%20%7C%20VS%20Code-6B7194?style=for-the-badge" alt="MCP" />
  <img src="https://img.shields.io/badge/Free%20Tier-10K%20events%2Fmo-C7AB6B?style=for-the-badge" alt="Free" />
  <img src="https://img.shields.io/badge/Memory-Bi--Temporal%20SVO%20%2B%20pgvector-4ADE80?style=for-the-badge" alt="Memory" />
</p>

<h1 align="center">🕰️ Smriti — Temporal Event Memory</h1>

> **Give your business workflows, ops teams, and AI agents an auditable ledger of what happened, when, and with whom.**
> Smriti decomposes operational events into concrete Subject-Verb-Object (SVO) tuples, stores them in a Bi-Temporal PostgreSQL architecture, and lets workflows reason precisely across time without hallucination.

---

## 📖 What is Smriti?

**The Problem:** Traditional "agent memory" relies on fuzzy vector databases that struggle with temporal drift and ambiguous chat facts. When tracking deals, deployments, contracts, or multi-step operational workflows, you don't need a chatbot to remember a favorite color—you need an auditable, deterministic event ledger.

**The Solution:** Smriti is a **temporal event memory layer**. It gives AI agents and business infrastructure a bi-temporal hippocampus that tracks state changes perfectly across systems and sessions.

| Feature | Smriti (Event Memory) | Traditional RAG (Chat Memory) |
|---|---|---|
| **Structure** | **SVO Tuples:** Tracks concrete actions (`Agent → Deployed → Build42`) | **Vector Sludge:** Dumps unstructured text into a vector DB |
| **Time** | **Bi-Temporal:** Tracks both *when it happened* and *when it was recorded* | **Timeless:** Cannot distinguish old facts from current state |
| **Updates** | **Supersession:** Safely overrides state without deleting history | **Overwrite:** Hard deletes or creates confusing duplicates |

---

## 🚀 Quick Start (5 Minutes)

**1. Get a Free API Key**
```bash
curl -X POST "https://smriti-kaal.vercel.app/billing/keys?tier=explorer"
```

**2. Store a Memory**
```bash
curl -X POST https://smriti-kaal.vercel.app/ingest \
  -H "X-API-Key: chrn_your_key" \
  -d '{"source_id": "demo", "events": [{"text": "Alice joined as Lead Engineer on July 15"}]}'
```

**3. Recall It**
```bash
curl -X POST https://smriti-kaal.vercel.app/query \
  -H "X-API-Key: chrn_your_key" \
  -d '{"query": "Who joined the team recently?"}'
```

### What You Get Back
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

## 🐘 Bring Your Own Database (BYODB) — Supabase

Want to keep your memory data in your own infrastructure? Smriti supports **Bring Your Own Database (BYODB)** using Supabase (PostgreSQL + pgvector).

With zero code changes, you can route all extracted memories, vectors, and conversation turns directly to your own Supabase project. The data never touches Smriti's cloud storage.

### How it works
Just add the `X-Supabase-Url` header to your API requests (using the Session Pooler URL):
```bash
curl -X POST https://smriti-kaal.vercel.app/ingest \
  -H "X-API-Key: chrn_your_key" \
  -H "X-Supabase-Url: postgresql://postgres.xxxx:pw@aws-0-REGION.pooler.supabase.com:5432/postgres" \
  -d '{"source_id": "my-app", "events": [{"text": "Alice joined the team"}]}'
```

The Smriti pipeline runs exactly the same, but the final data lands in your database!

👉 **[Read the full 3-step setup guide here](./supabase/README.md)**

---

## 🔌 MCP Server (Claude, Cursor, VS Code)

Smriti ships with a built-in **Model Context Protocol (MCP)** server. It runs as a lightweight local process that connects Claude Desktop, Cursor, and VS Code directly to Smriti's cloud memory API — no backend to host, no infrastructure to manage on your end. All memory processing and storage happens on Smriti's servers.

### 1. Install & Configure

Install via PyPI:
```bash
pip install smriti-kaal-mcp
```
*(Or use zero-install `uvx smriti-kaal-mcp` directly in your client config below).*

<details>
<summary><b>Setup for Claude Desktop</b></summary>

Add this to your `claude_desktop_config.json`:
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
</details>

<details>
<summary><b>Setup for Cursor</b></summary>

Add this to `.cursor/mcp.json` in your project root:
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
</details>


### 2. Available MCP Tools

| Tool | What It Does |
|------|-------------|
| `smriti_remember` | Store text; auto-extracts causal SVO events |
| `smriti_recall` | Hybrid search (semantic + temporal) across all memories |
| `smriti_timeline` | Generate a chronological timeline of events |
| `smriti_forget` | Supersede outdated memories cleanly |
| `smriti_health` | View service health status |

---

## 🏗️ The 4-Layer Architecture Pipeline

When you send text to Smriti, it passes through four discrete layers:

1. **Ingest Gate** — Accepts raw, chaotic text from chat logs, emails, or code.
2. **Decomposition** — The Groq LLM strips fluff and extracts structured `Subject → Verb → Object` tuples.
3. **Temporal Binding** — Assigns exact temporal boundaries to track state changes over time.
4. **Dual-Store Indexing** — Saves to PostgreSQL (for exact chronological queries) and pgvector (for fuzzy semantic search).

---

## 📖 REST API Reference

**Base URL:** `https://smriti-kaal.vercel.app`  
**Auth:** Include header `X-API-Key: chrn_your_key`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/billing/keys` | POST | Generate a new API key |
| `/ingest` | POST | Send raw text to be converted into structured memories |
| `/query` | POST | Natural language memory retrieval |
| `/agent/run` | POST | Chat directly with our memory-aware LangGraph agent |
| `/health` | GET | System uptime and DB status |

---

## 💻 Integration Examples

### Node.js / JavaScript
```javascript
const headers = { "X-API-Key": "chrn_...", "Content-Type": "application/json" };

// Remember
await fetch("https://smriti-kaal.vercel.app/ingest", {
  method: "POST", headers,
  body: JSON.stringify({ source_id: "app", events: [{ text: "Upgraded to Pro" }] })
});

// Recall
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

# Remember
httpx.post(f"{API}/ingest", headers=HEADERS, json={
    "source_id": "my-app",
    "events": [{"text": "User completed onboarding on July 15"}]
})

# Recall
result = httpx.post(f"{API}/query", headers=HEADERS, json={
    "query": "What did the user do?"
})
print(result.json()["results"])
```

---

## ⚙️ Environment Configuration (MCP)

These variables are set by the end user when configuring the MCP client. No server-side setup is required.

| Variable | Required | Description |
|---|---|---|
| `SMRITI_API_KEY` | ✅ | Your Smriti API key (`chrn_...`) from [smriti-kaal.vercel.app](https://smriti-kaal.vercel.app) |
| `SMRITI_SOURCE_ID` | No | Namespace for your memories (e.g. `claude-desktop`, `my-project`) |
| `SMRITI_SUPABASE_URL` | No | Session Pooler URL to route memory to your own Supabase DB (BYODB) |
| `SMRITI_SCOPE` | No | Memory scope (`default` unless you need multi-tenant isolation) |

---

## 📊 Dashboard & Pricing

Manage your memories, keys, and view timelines via the Dashboard:  
**[smriti-kaal.vercel.app](https://smriti-kaal.vercel.app)**

| Tier | Price | Limits |
|---|---|---|
| **Explorer** | Free | 10,000 events/mo, 3 connected tools |
| **Builder** | $49/mo | 500,000 events/mo, 25 tools |
| **Scale** | $249/mo | 5,000,000 events/mo, unlimited tools |

---

<p align="center">
  <em>🕰️ Memory that persists. Context that continues.</em><br>
  <strong>© 2026 Smriti / Chronos Labs</strong>
</p>
