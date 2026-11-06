CREATE EXTENSION IF NOT EXISTS vector;
-- Future migrations belong in api/src/main/resources/db/migration.
CREATE TABLE IF NOT EXISTS runbook_chunks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source text NOT NULL,
    content text NOT NULL,
    embedding vector(384),
    created_at timestamptz NOT NULL DEFAULT now()
);
