CREATE TABLE alert_states (
    fingerprint varchar(64) PRIMARY KEY CHECK (fingerprint ~ '^[0-9a-f]{16,64}$'),
    active_incident_id uuid REFERENCES incidents(id) ON DELETE RESTRICT,
    active_starts_at timestamptz,
    resolved_through timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((active_incident_id IS NULL) = (active_starts_at IS NULL))
);
CREATE TABLE alert_incidents (
    incident_id uuid PRIMARY KEY REFERENCES incidents(id) ON DELETE RESTRICT,
    fingerprint varchar(64) NOT NULL REFERENCES alert_states(fingerprint) ON DELETE RESTRICT,
    starts_at timestamptz NOT NULL,
    resolved_at timestamptz,
    labels jsonb NOT NULL CHECK (jsonb_typeof(labels) = 'object'),
    annotations jsonb NOT NULL CHECK (jsonb_typeof(annotations) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (resolved_at IS NULL OR resolved_at >= starts_at)
);
CREATE UNIQUE INDEX alert_one_active_incident_idx ON alert_incidents (fingerprint) WHERE resolved_at IS NULL;
