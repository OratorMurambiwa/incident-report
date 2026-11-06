-- Preserve existing diagnoses and label their previously unknown provenance honestly.
ALTER TABLE diagnoses
    ADD COLUMN mode varchar(24) NOT NULL DEFAULT 'LEGACY',
    ADD COLUMN provider varchar(16) NOT NULL DEFAULT 'none',
    ADD COLUMN model text,
    ADD COLUMN event_id uuid UNIQUE REFERENCES processed_events(event_id) ON DELETE RESTRICT,
    ADD COLUMN likely_causes jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN investigation_steps jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN suggested_remediation jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN cited_runbooks jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN retrieved_evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN uncertainty text NOT NULL DEFAULT 'Legacy result; generation provenance was not recorded.';
ALTER TABLE diagnoses ADD CONSTRAINT diagnoses_mode_check CHECK (mode IN ('LEGACY','RETRIEVAL_ONLY','GENERATED'));
ALTER TABLE diagnoses ADD CONSTRAINT diagnoses_provider_check CHECK (provider IN ('none','ollama'));
ALTER TABLE diagnoses ADD CONSTRAINT diagnoses_provenance_check CHECK (
    mode = 'LEGACY' OR
    (mode = 'RETRIEVAL_ONLY' AND provider = 'none' AND model IS NULL AND event_id IS NOT NULL
        AND likely_causes = '[]'::jsonb AND investigation_steps = '[]'::jsonb AND suggested_remediation = '[]'::jsonb) OR
    (mode = 'GENERATED' AND provider = 'ollama' AND model IS NOT NULL AND length(btrim(model)) > 0 AND event_id IS NOT NULL)
);
ALTER TABLE diagnoses ADD CONSTRAINT diagnoses_arrays_check CHECK (
    jsonb_typeof(likely_causes) = 'array' AND jsonb_typeof(investigation_steps) = 'array'
    AND jsonb_typeof(suggested_remediation) = 'array' AND jsonb_typeof(cited_runbooks) = 'array'
    AND jsonb_typeof(retrieved_evidence) = 'array'
);
ALTER TABLE incidents DROP CONSTRAINT incidents_status_check;
ALTER TABLE incidents ADD CONSTRAINT incidents_status_check
    CHECK (status IN ('PENDING','RECEIVED','ANALYZING','DIAGNOSED','RESOLVED','FAILED'));
