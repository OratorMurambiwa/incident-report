-- A Kafka tombstone has a NULL value, distinct from empty bytes. Retain it faithfully.
ALTER TABLE failed_events ALTER COLUMN payload DROP NOT NULL;
