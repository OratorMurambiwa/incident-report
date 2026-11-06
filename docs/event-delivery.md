# Event contract and delivery operations

## Version 1 JSON

Topic `incident.created`; Kafka key is incidentId. New incidents return PENDING immediately, then become RECEIVED (retrieval-only) or DIAGNOSED (generated) asynchronously. Pre-existing incidents are preserved, with no event backfill.

```json
{
  "schemaVersion": 1,
  "eventId": "4af22867-5bf3-4eab-b779-27257053c676",
  "incidentId": "5ea31031-90d5-4b62-a899-d7375e733494",
  "service": "event-flow-smoke",
  "title": "Synthetic event flow",
  "description": "Local outbox and worker verification",
  "severity": "HIGH",
  "timestamp": "2026-11-06T00:19:39Z"
}
```

The worker requires exactly these fields. UUIDs must parse, strings must satisfy API length/nonblank limits, severity must be LOW/MEDIUM/HIGH/CRITICAL, timestamp must have a timezone, schemaVersion must be integer 1. The timestamp is incident creation time, not publish time. The worker now persists a retrieval-only or local Ollama diagnosis. See README RAG configuration and docs/rag-verification.md; no hosted provider is used.

## Atomicity and retries

IncidentService flushes JPA's incident write and inserts outbox JSON through the same transactional connection. Failure rolls back both. Publisher runs in a separate Compose service using the API image with web mode disabled. Its scheduler invokes a transactional delivery service; row locks and SKIP LOCKED allow multiple publishers without claiming the same row concurrently. Each send waits for Kafka acknowledgement; only afterward does published_at commit. Kafka producer idempotence handles internal retries; durable event IDs handle crash/restart duplicates.

Unsent outbox rows retry indefinitely, with attempt count, safe last_error class name and next_attempt_at. Backoff is 2,4,8,…256 seconds. No outbox cleanup or retention policy deletes them. A crash after Kafka acknowledgement and before database commit causes replay, not a lost event. PostgreSQL and Kafka are not in a distributed transaction, and exactly-once delivery is not claimed.

Worker inserts a processed_events record and persists five evidence snapshots plus a diagnosis and changes status appropriately in the same psycopg transaction. The database event-ID uniqueness constraint serializes duplicate handling; matching canonical payload hashes make replays no-ops. Reusing an ID for changed data is quarantined. Later incident statuses never regress. Offset commits explicitly acknowledge only the current record after successful database commit.

Worker processing attempts are bounded at three, with short backoff. Invalid contracts and conflicting IDs are quarantined immediately. Transient/exhausted processing failures are quarantined after the third failure. failed_events records original bytes (NULL for Kafka tombstones), topic/partition/offset, attempt count and safe error class. Only a successful quarantine commit permits offset acknowledgement. Database unavailability preventing quarantine stops the process; Docker restarts it. Kafka offset commit failure also stops processing; subsequent redelivery is safe.

## Inspect and recover

```bash
docker compose ps -a
docker compose logs --tail=100 publisher worker
docker compose exec postgres psql -U incidentiq -d incidentiq -c \
  "SELECT count(*) AS pending, min(created_at) AS oldest FROM incidentiq_api.outbox_events WHERE published_at IS NULL;"
docker compose exec postgres psql -U incidentiq -d incidentiq -c \
  "SELECT event_id, attempts, next_attempt_at, last_error FROM incidentiq_api.outbox_events WHERE published_at IS NULL;"
docker compose exec postgres psql -U incidentiq -d incidentiq -c \
  "SELECT topic, partition_id, offset_id, error_code, attempts, failed_at FROM incidentiq_api.failed_events ORDER BY failed_at DESC;"
docker compose exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:29092 --group incidentiq-worker-v1 --describe
```

For custom database credentials, adapt the psql user/database flags without printing passwords. Monitor failed_events and incidentiq_worker_quarantined_total: Kafka lag can be zero while quarantined incidents remain unprocessed. The health endpoint only checks that the worker metrics HTTP server responds; it does not establish absence of backlog or failures. Publisher has no HTTP health endpoint; inspect its process, logs and outbox age.

Fix the underlying database/event-contract problem before replay. An operator can read the retained payload and republish it to incident.created with the incident UUID as key. Preserve eventId for unchanged transient-failure replay. Do not reuse eventId for a changed payload already in processed_events. Invalid schema/UUID/missing-incident records require explicit correction and review. Preserve failure records as evidence; this implementation does not automatically replay, resolve or delete quarantine entries. Never reset a consumer group past unpersisted records or delete volumes to clear backlog.

## Tests

Run test-api.sh, then test-worker.sh for all tests against isolated incidentiq_api_test. Image builds run their database-independent tests and explicitly skip database-dependent cases. verify-event-flow.py creates a real HTTP incident, checks outbox/receipt state, observes its Kafka JSON, replays it and checks no extra receipt/status write, then injects a malformed record and verifies quarantine before committed group advancement. It retains synthetic evidence in the application database.

## Diagnosis extension

V5 adds structured diagnoses and provenance. Provider none leaves generated sections empty and stores RETRIEVAL_ONLY. Optional Ollama generation sets DIAGNOSED after citation/schema validation. Model/evidence/output failures roll back new receipt/context/diagnosis writes; after retries their quarantine transaction marks pending incidents FAILED. This does not remove previous snapshots or change resolved incidents. Unchanged replay after fixing configuration can recover FAILED incidents. Read rag-verification.md for the latest actual mode-specific results.
