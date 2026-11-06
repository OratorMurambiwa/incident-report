CREATE TABLE incidents (
    id uuid PRIMARY KEY,
    service varchar(100) NOT NULL CHECK (length(btrim(service)) > 0),
    title varchar(200) NOT NULL CHECK (length(btrim(title)) > 0),
    description varchar(10000) NOT NULL CHECK (length(btrim(description)) > 0),
    severity varchar(16) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status varchar(16) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ANALYZING', 'RESOLVED', 'FAILED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT incidents_timestamp_order CHECK (updated_at >= created_at)
);
CREATE INDEX incidents_created_at_idx ON incidents (created_at DESC, id DESC);

CREATE TABLE diagnoses (
    id uuid PRIMARY KEY,
    incident_id uuid NOT NULL UNIQUE REFERENCES incidents(id) ON DELETE RESTRICT,
    summary varchar(10000) NOT NULL CHECK (length(btrim(summary)) > 0),
    recommendations varchar(20000) NOT NULL CHECK (length(btrim(recommendations)) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT diagnoses_timestamp_order CHECK (updated_at >= created_at)
);
