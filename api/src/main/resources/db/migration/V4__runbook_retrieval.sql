-- Keep the pre-existing public.runbook_chunks table and all previous migrations intact.
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

CREATE TABLE runbook_documents (
    id uuid PRIMARY KEY,
    source varchar(255) NOT NULL UNIQUE,
    fingerprint char(64) NOT NULL,
    model_name text NOT NULL,
    model_revision varchar(40) NOT NULL,
    chunk_count integer NOT NULL CHECK (chunk_count > 0),
    ingested_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE runbook_chunks (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES runbook_documents(id) ON DELETE CASCADE,
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    content text NOT NULL CHECK (length(btrim(content)) > 0),
    embedding public.vector(384) NOT NULL,
    UNIQUE (document_id, chunk_index)
);
-- Exact cosine search is intentional for this small corpus; no approximate index loses recall.
CREATE TABLE incident_retrievals (
    event_id uuid NOT NULL REFERENCES processed_events(event_id) ON DELETE CASCADE,
    incident_id uuid NOT NULL REFERENCES incidents(id) ON DELETE RESTRICT,
    rank integer NOT NULL CHECK (rank BETWEEN 1 AND 5),
    chunk_id uuid NOT NULL,
    source varchar(255) NOT NULL,
    content text NOT NULL,
    similarity double precision NOT NULL CHECK (similarity BETWEEN -1.000001 AND 1.000001),
    model_name text NOT NULL,
    model_revision varchar(40) NOT NULL,
    retrieved_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, rank),
    UNIQUE (event_id, chunk_id)
);
CREATE INDEX incident_retrievals_incident_idx ON incident_retrievals (incident_id);
-- Retrievals store immutable content snapshots: ingestion may replace a chunk later.
