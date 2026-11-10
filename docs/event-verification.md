> Historical milestone snapshot: capability/version statements and counts below describe that run. See the [current overview](../README.md) and [latest application/security regression](security/VERIFICATION.md) for subsequent implementation and verification.

# Outbox and worker verification — 2026-11-05 (America/Chicago)

## Changes and preservation

Read AGENTS.md and inspected existing API, migrations, tests, worker and Compose before changing code. Kept the existing 26 test cases; only constructor wiring in IncidentServiceTest was adapted for the new outbox dependency, with an additional enqueue assertion. Kept V1 unchanged. Added Flyway V2 for outbox/receipts/failures/RECEIVED and V3 to retain NULL Kafka tombstones faithfully.

PostgreSQL and Kafka images, settings, named volumes and host port 55432 were preserved. Compose adds publisher and worker and initializes incident.created without removing legacy topics. Publisher uses the existing Java image in non-web mode; API writes outbox but does not schedule sends. The worker image runs as a non-root user, and its build runs unit tests. Prometheus worker target now uses worker:8001 over internal networking. No volumes or application rows were deleted. Original incident 71b88560-3f88-4811-8531-49e0c1692300 and diagnosis 14cbca3b-e7a5-4298-8c03-5ebd7072ddcb were queried and still exist. pgvector remains 0.8.7.

## Executed commands and results

- `docker compose config --quiet`: exit 0, including final validation.
- `docker compose build api worker`: exit 0 after correcting a kafka-python 2.2.15 API mismatch discovered by pytest: OffsetAndMetadata requires leader_epoch, now supplied as -1. Final ordinary image build: 25 Java cases executed, 7 database cases explicitly skipped; 24 Python cases executed, 5 database cases explicitly skipped. PostgreSQL tests run separately below, not inside image builds.
- `./scripts/test-api.sh`: exit 0, using isolated incidentiq_api_test. Actual final summary:

```text
Tests run: 17, Failures: 0, Errors: 0, Skipped: 0 -- IncidentControllerTest
Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- IncidentServiceTest
Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- PostgresIntegrationTest
Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- OutboxDeliveryTest
Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- OutboxPostgresTest
Tests run: 32, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

Outbox tests cover JSON fields, atomic incident/event rollback, real PostgreSQL retry metadata/backoff, failure then retry success, send acknowledgement before marking published, and a database failure after acknowledgement. Kafka failures in these JUnit tests are simulated with a mocked KafkaTemplate; real Kafka is exercised by the flow test below.

- `./scripts/test-worker.sh`: exit 0. Actual final summary:

```text
29 passed in 0.37s
```

24 unit cases and 5 PostgreSQL cases cover event validation, delayed offset commits, transient failures, bounded retries, durable quarantine, database/commit failure propagation, shutdown, event-ID conflicts, receipt deduplication, non-regression of advanced statuses, missing-incident rollback, and byte-for-byte/NULL failed-record retention. Database test fixtures are cleaned in the isolated database; application data is not touched by unit/integration tests.

- `docker compose up -d --wait api publisher worker`: exit 0. API, PostgreSQL, Kafka and worker healthy; publisher running; kafka-init exited 0. API is on localhost:8080, PostgreSQL localhost:55432, Kafka localhost:9092. Publisher has no HTTP health endpoint. Worker health checks metrics HTTP responsiveness, not absence of failures/backlog.
- `python3 scripts/verify-event-flow.py`: exit 0. Real HTTP, actual Kafka produce/consume, actual PostgreSQL and running worker:

```text
POST: HTTP 201, incidentId=5ea31031-90d5-4b62-a899-d7375e733494, status=PENDING
GET: HTTP 200, status=RECEIVED
Outbox published: eventId=4af22867-5bf3-4eab-b779-27257053c676, attempts=1; durable receipts=1
Kafka observed: topic=incident.created, offset=0, matching JSON contract
Duplicate offset=1: one receipt, incident timestamp unchanged
Malformed offset=2: original bytes durably quarantined; group offset=3
Full event flow, duplicate delivery and malformed-record checks passed
```

Publisher log confirmed Outbox delivered for that event ID. Worker logs confirmed received, duplicate and quarantined actions. A consumer-group query after the additional HTTP smoke test returned:

```text
GROUP                TOPIC            PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG
incidentiq-worker-v1 incident.created 0         4              4              0
```

The flow script verified the original event JSON on Kafka through an independent observer, checked published_at and receipt rows, replayed the event and verified one receipt plus unchanged incident timestamp. It also injected synthetic malformed bytes and confirmed their durable failure record before the group offset advanced.

- `python3 scripts/verify-api.py`: exit 0; original real HTTP smoke checks pass with asynchronous status evolution:

```text
GET /actuator/health: HTTP 200
POST /api/incidents: HTTP 201
Created incident adaad2ab-c49a-4f91-bfce-e55cb12003b1, status=PENDING
GET /api/incidents/adaad2ab-c49a-4f91-bfce-e55cb12003b1: HTTP 200
GET /api/incidents?page=0&size=20: HTTP 200
GET /api/incidents/adaad2ab-c49a-4f91-bfce-e55cb12003b1/diagnosis: HTTP 404
GET /api/incidents/55f262a5-0775-4ce6-a0c9-a84a0f767d18: HTTP 404
GET /api/incidents/6165a3d5-9ef5-411d-b781-e5e463b939af/diagnosis: HTTP 404
POST /api/incidents: HTTP 400
POST /api/incidents: HTTP 400
POST /api/incidents: HTTP 400
GET /api/incidents/not-a-uuid: HTTP 400
GET /api/incidents?size=101: HTTP 400
All 12 HTTP checks passed; synthetic incident retained.
```

- Container psql confirmed Flyway V1/V2/V3 success and pgvector 0.8.7. It also confirmed the prior incident/diagnosis fixture still exists unchanged by backfill (no backfill is performed).
- Python syntax compilation and `bash -n scripts/test-worker.sh` passed.

## Retained verification data and limits

Two new synthetic HTTP incidents remain in the application database, with their outbox rows/receipts. One synthetic malformed record remains quarantined at incident.created partition 0 offset 2; this is deliberate verification evidence, not an unreported processing success. No automatic quarantine replay/deletion is implemented. Publisher retries unsent rows indefinitely; worker processing retries three times then retains failures durably. PostgreSQL unavailability preventing durable quarantine causes worker restart without offset acknowledgement.

Kafka delivery is at least once. A real crash during the broker-ack/database-commit window and a real broker outage were not injected; related failure behavior is covered by tests with simulated failures. AI inference, diagnosis generation and live frontend integration remain future work. No cloud resources, remote repository, paid services or host Java/Maven installations were used. The monitoring profile was not started/tested in this continuation.
