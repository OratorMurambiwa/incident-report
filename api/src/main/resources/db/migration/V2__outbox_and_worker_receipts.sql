ALTER TABLE incidents DROP CONSTRAINT incidents_status_check;
ALTER TABLE incidents ADD CONSTRAINT incidents_status_check
    CHECK (status IN ('PENDING', 'RECEIVED', 'ANALYZING', 'RESOLVED', 'FAILED'));

CREATE TABLE outbox_events (
    event_id uuid PRIMARY KEY,
    incident_id uuid NOT NULL REFERENCES incidents(id) ON DELETE RESTRICT,
    topic varchar(100) NOT NULL CHECK (topic = 'incident.created'),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error varchar(200)
);
CREATE INDEX outbox_unsent_idx ON outbox_events (next_attempt_at, created_at)
    WHERE published_at IS NULL;

CREATE TABLE processed_events (
    event_id uuid PRIMARY KEY,
    incident_id uuid NOT NULL REFERENCES incidents(id) ON DELETE RESTRICT,
    payload_hash char(64) NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now()
);

-- Durable dead-letter storage. Retain original bytes for explicit investigation/replay.
CREATE TABLE failed_events (
    topic varchar(249) NOT NULL,
    partition_id integer NOT NULL CHECK (partition_id >= 0),
    offset_id bigint NOT NULL CHECK (offset_id >= 0),
    payload bytea NOT NULL,
    error_code varchar(100) NOT NULL,
    attempts integer NOT NULL CHECK (attempts > 0),
    failed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (topic, partition_id, offset_id)
);
