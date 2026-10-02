# Smriti × Supabase — Bring Your Own Database

Connect your own Supabase database to Smriti in **3 steps, under 2 minutes**. Your memory data never touches the Smriti cloud — it lives entirely in your Supabase project.

---

## Connect in 3 Steps

### Step 1 — Create a Supabase Project
1. Go to [supabase.com](https://supabase.com) → **New Project** (free tier is fine).
2. Choose a region close to you. Wait ~1 minute for it to provision.

### Step 2 — Run the Migration
1. In your Supabase dashboard, go to **SQL Editor → New Query**.
2. Copy the entire contents of [`migrations/001_smriti_schema.sql`](./migrations/001_smriti_schema.sql).
3. Paste it in and click **Run** (▶).  Done. All Smriti tables and indexes are created.

### Step 3 — Copy your Connection String

1. Go to **Project Settings → Database → Connection Pooling**.
2. Set **Pool mode** to **Session**.
3. Copy the **Connection string** — it looks like:
   ```
   postgresql://postgres.xxxx:YOUR_PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
   ```

> [!IMPORTANT]
> **Use the Session Pooler URL** (from Connection Pooling, not Connection String).
> The direct connection URL (`db.xxxx.supabase.co`) only works from local machines.
> It **fails on Hugging Face Spaces, Railway, Render, and most cloud hosts** due to IPv6 routing.
> The Session Pooler URL works everywhere.

---

## Use It — Just Add One Header

From this point, add `X-Supabase-Url` to every Smriti API call:

```bash
# Without Supabase (default — data goes to Smriti cloud DB)
curl -X POST https://smriti-kaal.vercel.app/ingest \
  -H "X-API-Key: chrn_your_key" \
  -d '{"source_id": "my-app", "events": [{"text": "Alice joined the team"}]}'

# With Supabase (data goes to YOUR Supabase DB)
curl -X POST https://smriti-kaal.vercel.app/ingest \
  -H "X-API-Key: chrn_your_key" \
  -H "X-Supabase-Url: postgresql://postgres.xxxx:pw@aws-0-REGION.pooler.supabase.com:5432/postgres" \
  -d '{"source_id": "my-app", "events": [{"text": "Alice joined the team"}]}'
```

Same for queries:
```bash
curl -X POST https://smriti-kaal.vercel.app/query \
  -H "X-API-Key: chrn_your_key" \
  -H "X-Supabase-Url: postgresql://postgres.xxxx:pw@aws-0-REGION.pooler.supabase.com:5432/postgres" \
  -d '{"query": "What happened with Alice?"}'
```

**That's it.** The full Smriti pipeline (SVO extraction → supersession → semantic search → temporal retrieval) runs identically — data just lands in your Supabase instead.

---

## Eject (Disconnect)

To stop using your Supabase and go back to the default Smriti storage, simply **remove the `X-Supabase-Url` header**. No configuration to undo. No data deleted. Instant.

Your Supabase data stays in your Supabase. Our cloud data stays in our cloud. They are fully independent.

---

## MCP Integration

If you use the Smriti MCP server, set `SMRITI_SUPABASE_URL` in your environment and it will be forwarded automatically:

```json
{
  "mcpServers": {
    "smriti": {
      "command": "uvx",
      "args": ["smriti-kaal-mcp"],
      "env": {
        "SMRITI_API_KEY": "chrn_your_key",
        "SMRITI_SUPABASE_URL": "postgresql://postgres.xxxx:pw@aws-0-REGION.pooler.supabase.com:5432/postgres"
      }
    }
  }
}
```

---

## What Stays in Smriti's Cloud

| Data | Location |
|------|----------|
| Your API key & usage quota | Smriti Neon DB (always) |
| Billing / tier info | Smriti Neon DB (always) |
| Events, turns, vectors | **Your Supabase** (when header is set) |

Your memory data, your database. We process and extract — you own the store.

---

## Verify It's Working

After running the migration and making your first request, check your Supabase dashboard:

1. **Table Editor** → `events` — you should see rows appearing.
2. **Table Editor** → `event_vectors` — you should see vector embeddings.

You can also query directly in Supabase SQL Editor:
```sql
SELECT subject, verb, object, timestamp
FROM events
ORDER BY timestamp DESC
LIMIT 10;
```
