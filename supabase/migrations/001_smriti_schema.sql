-- =============================================================================
-- Smriti Memory Schema — Supabase Migration
-- =============================================================================
-- Run this ONCE in your Supabase SQL Editor before connecting to Smriti.
-- Copy → Paste → Run. That's all. Takes ~2 seconds.
--
-- Supabase Dashboard → SQL Editor → New Query → Paste this → Run
-- =============================================================================

-- Enable pgvector (Supabase has this built-in)
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- Event Calendar — S-V-O structured memory events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    subject         TEXT NOT NULL,
    verb            TEXT NOT NULL,
    object          TEXT NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    datetime_start  TIMESTAMPTZ,
    datetime_end    TIMESTAMPTZ,
    entity_aliases  JSONB DEFAULT '[]',
    confidence      REAL DEFAULT 1.0,
    metadata_json   JSONB DEFAULT '{}',
    raw_text        TEXT DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL,
    scope           TEXT NOT NULL DEFAULT 'default',
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to        TIMESTAMPTZ,          -- NULL = still active fact
    superseded_by   TEXT                  -- ID of the newer event that replaced this
);

CREATE INDEX IF NOT EXISTS idx_events_source    ON events(source_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_subject   ON events(subject);
CREATE INDEX IF NOT EXISTS idx_events_scope     ON events(scope);
CREATE INDEX IF NOT EXISTS idx_events_active    ON events(valid_to) WHERE valid_to IS NULL;

-- ---------------------------------------------------------------------------
-- Turn Calendar — raw conversation turns for full context replay
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS turns (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'user',
    content     TEXT NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL,
    event_ids   JSONB DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_turns_source    ON turns(source_id);
CREATE INDEX IF NOT EXISTS idx_turns_timestamp ON turns(timestamp DESC);

-- ---------------------------------------------------------------------------
-- Connectors — registered SaaS tool integrations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS connectors (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    base_url    TEXT NOT NULL,
    auth_header TEXT,
    endpoints   JSONB DEFAULT '[]',
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_connectors_source ON connectors(source_id);

-- ---------------------------------------------------------------------------
-- Vector Embeddings — pgvector semantic search (384-dim, all-MiniLM-L6-v2)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_vectors (
    event_id    TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    source_id   TEXT NOT NULL,
    owner_id    TEXT NOT NULL,
    scope       TEXT NOT NULL DEFAULT 'default',
    embedding   vector(384) NOT NULL,
    embed_text  TEXT NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vectors_source ON event_vectors(source_id);
CREATE INDEX IF NOT EXISTS idx_vectors_owner  ON event_vectors(owner_id);
CREATE INDEX IF NOT EXISTS idx_vectors_scope  ON event_vectors(scope);

-- HNSW index for fast approximate nearest-neighbour search
-- (Supabase recommends HNSW over IVFFlat for most workloads)
CREATE INDEX IF NOT EXISTS idx_vectors_hnsw
    ON event_vectors USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- =============================================================================
-- Done! Your Smriti memory schema is ready.
-- Now add X-Supabase-Url to your API calls and you're live.
-- =============================================================================
