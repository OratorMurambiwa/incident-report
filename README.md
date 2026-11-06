# IncidentIQ

Local incident monitoring platform with a working Java 21 REST API and PostgreSQL persistence. Incident creation now flows through a transactional outbox and Kafka to a Python worker that records RECEIVED. The worker now retrieves local runbook context with LangChain and pgvector. Diagnosis generation and the live frontend remain future work. No paid or hosted AI service is configured.

## Run locally with Docker

Docker with Compose is sufficient to build, test and run the API. Host Java and Maven are optional.

```bash
# Only on first setup; preserve an existing .env:
[ -f .env ] || cp .env.example .env
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps -a
```

`compose.yaml` is the canonical Compose file. It starts API, a separate outbox publisher (the same Java image in non-web mode), the Python worker, PostgreSQL/pgvector, Kafka KRaft and the idempotent topic initializer. A one-shot runbook-ingest service indexes the mounted Markdown corpus after migrations; the worker waits for it to succeed. PostgreSQL remains published at `127.0.0.1:55432`; the API connects through `postgres:5432` and uses `kafka:29092`. API: `http://localhost:8080` (`API_PORT` is configurable). Kafka: `localhost:9092`. Containers retain their existing named volumes. Topic initialization normally finishes with exit 0.

```bash
# Optional monitoring:
docker compose --profile observability up -d --wait
# Inspect:
docker compose logs --tail=100 api postgres kafka
curl http://localhost:8080/actuator/health
# Stop, preserving persistent data:
docker compose --profile observability down
```

Adding `--volumes` to `down` permanently deletes data. Do not do that for migrations. Credentials in .env.example are local development defaults. Images and Maven artifacts need initial downloads; execution and data remain local.

## REST API

```bash
curl -i -X POST http://localhost:8080/api/incidents \
  -H 'Content-Type: application/json' \
  -d '{"service":"billing","title":"Elevated timeouts","description":"Requests exceed 5 seconds","severity":"HIGH"}'
curl 'http://localhost:8080/api/incidents?page=0&size=20'
curl http://localhost:8080/api/incidents/REPLACE_WITH_UUID
curl http://localhost:8080/api/incidents/REPLACE_WITH_UUID/diagnosis
```

- `POST /api/incidents`: 201, Location header and full incident DTO including UUID, PENDING status and UTC timestamps.
- `GET /api/incidents`: 200 with `content`, `page`, `size`, `totalElements`, `totalPages`. Page starts at 0; size defaults to 20 and must be 1–100. Ordered newest first, with UUID as a stable tie breaker.
- `GET /api/incidents/{id}`: 200 with incident; 404 if missing.
- `GET /api/incidents/{id}/diagnosis`: 200 with diagnosis UUID, incidentId, summary, recommendations and timestamps. Returns 404 when the incident is missing or its diagnosis is not yet available. No diagnosis generation or write endpoint exists yet.

Creation requires nonblank `service` (max 100), `title` (max 200), `description` (max 10000), and severity `LOW`, `MEDIUM`, `HIGH` or `CRITICAL`. Strings are trimmed. Status is server-owned; client-supplied status and unknown properties are rejected. Stored status values are PENDING, RECEIVED, ANALYZING, RESOLVED and FAILED. Creation returns PENDING; the asynchronous worker changes it to RECEIVED. Invalid JSON, enum values, UUIDs or pagination produce 400. Errors use Problem Detail JSON; field-validation errors include an `errors` map. Database constraint conflicts produce 409, unexpected failures produce a generic 500.

## Persistence and migrations

Flyway owns schema `incidentiq_api`. V1 creates UUID-keyed incidents and diagnoses with UTC timestamps, nonblank/length/enum constraints, timestamp ordering, a foreign key and a unique incident_id (one diagnosis per incident). Hibernate validates the schema; it does not create or alter tables. New changes require new migrations, never edits to an already applied migration.

A separate schema avoids baselining or altering the pre-existing public.runbook_chunks table. Existing pgvector initialization and Kafka settings are preserved. Flyway V2 adds the transactional outbox, worker receipts, durable failed-event storage and RECEIVED status. V3 permits NULL failed-event payloads to retain Kafka tombstones. V1 is unchanged. New incidents and their outbox events commit together; existing incidents are not backfilled.

## Build and tests without host Java/Maven

```bash
docker build --progress=plain -t incidentiq-api:local ./api
./scripts/test-api.sh
./scripts/verify-infra.sh
# Optional real HTTP smoke checks (Python 3 standard library; creates a synthetic incident):
python3 scripts/verify-api.py
```

The multi-stage Dockerfile runs `mvn verify` with Maven 3.9.11 and Java 21, then packages a non-root Java 21 JRE image. Build-time tests cover controllers and service logic; PostgreSQL integration tests are explicitly skipped during an ordinary image build because no database is available inside that build.

`test-api.sh` starts PostgreSQL, creates/reuses the isolated `incidentiq_api_test` database, builds the Maven stage and runs all JUnit tests against real PostgreSQL over Docker networking. Integration test transactions roll back. It checks persistence, diagnosis retrieval, enum constraints, foreign keys and one-diagnosis uniqueness. It retains the test database, without changing application rows. Do not point integration tests at the application database.

`verify-infra.sh` checks PostgreSQL TCP/password access inside its container, pgvector arithmetic, both application topics and an isolated Kafka produce/consume round trip. The temporary topic is deleted afterward. `docs/api-verification.md` records the latest actual build, test and HTTP results.

## Project layout and optional host development

- `api/`: Spring Web, Data JPA, Validation, Flyway, repositories, DTOs, services and controllers.
- `worker/`: Python 3.12 / Kafka receipt consumer, PostgreSQL idempotency and metrics (local sentence-transformers retrieval; diagnosis generation remains future work).
- `frontend/`: React 19 / Vite shell; not connected to the API.
- `runbooks/`: Markdown sources for future local retrieval.
- `infra/`: database bootstrap and monitoring configuration.
- `scripts/`: environment checks and repeatable testing/startup commands.
- `docs/`: architecture and verification evidence.

For optional host API development, install Java 21/Maven and export the database variables from .env, then `cd api && mvn spring-boot:run`. Stop the Compose API first to free port 8080. Run the worker through Compose so the pinned CPU packages and model files are available. For the frontend: Node 22.12+ and npm, then `cd frontend && npm install && npm run dev`. No host Python/Node is needed for the API or its JUnit tests.

Optional Prometheus runs at localhost:9090 and Grafana at localhost:3001 (admin/password from .env). API metrics are exposed at /actuator/prometheus. The existing Prometheus host target reaches the published API port; custom API_PORT changes require updating that target. Worker metrics use the internal worker:8001 target. Dashboards and generative diagnosis inference remain unimplemented. Local embedding inference and runbook retrieval are implemented.

## Event delivery and worker

`POST /api/incidents` inserts an `incident.created` event into `incidentiq_api.outbox_events` in the same transaction as the incident. JSON contains schemaVersion=1, eventId, incidentId, service, title, description, severity and an ISO-8601 timestamp. Kafka keys are incident UUIDs. The separate publisher uses Spring Kafka with acks=all and producer idempotence, marks published_at only after acknowledgement and retries unsent rows with persisted exponential backoff (2–256 seconds). Delivery is at least once; a crash after acknowledgement can cause a duplicate.

The Python worker validates the contract, inserts a processed_events receipt keyed by eventId, and transitions PENDING → RECEIVED in one PostgreSQL transaction. Replayed IDs with the same payload do not change status or timestamps. IDs reused with different payloads are rejected. Advanced statuses never regress. Kafka auto-commit is disabled; only the current partition's offset is committed after durable handling.

Processing failures receive up to three attempts. Malformed/conflicting events and exhausted processing failures are retained in failed_events before acknowledging their offsets. Original bytes (or NULL for a tombstone), source coordinates and safe error metadata remain available for investigation and explicit replay. A quarantine database failure or offset-commit failure terminates the worker; Docker restarts it, and the uncommitted record is safe to redeliver. A quarantined event has not been successfully processed: monitor the table and worker quarantine counter. No event is automatically discarded or deleted.

```bash
# Java tests, original 26 plus outbox cases, using an isolated PostgreSQL database:
./scripts/test-api.sh
# Python unit and real PostgreSQL tests, after test-api.sh creates/migrates that database:
./scripts/test-worker.sh
# Real HTTP → outbox → Kafka → worker, duplicate and malformed-message verification:
python3 scripts/verify-event-flow.py
docker compose logs --tail=100 publisher worker
```

Verification retains synthetic incidents and a malformed-message failure record. See [event-delivery.md](docs/event-delivery.md) for the contract, retries and operations, and [event-verification.md](docs/event-verification.md) for executed results. No AI-generated diagnosis is produced by RECEIVED processing.

## Local runbook retrieval

Ten detailed Markdown guides in runbooks/ are split by headings, then into at most 180-token chunks with 30-token overlap. Headings are retained in chunk text and the complete embedding input is checked against the model context window. The current corpus produces 60 chunks. LangChain Documents, text splitters, an Embeddings adapter and a BaseRetriever provide the retrieval path; PostgreSQL pgvector performs exact cosine-distance search.

The worker image pins sentence-transformers 3.4.1, transformers 4.48.3, CPU-only torch 2.6.0+cpu and the remaining direct dependencies. requirements.lock was generated from the resolved Docker environment and constrains transitive versions. Model revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf of sentence-transformers/all-MiniLM-L6-v2 is downloaded at build time and smoke-tested. Model loading and embeddings are offline at runtime; no hosted inference, API key or paid service is used. Model and package downloads need internet at build time.

```bash
docker compose up -d --build --wait
# Repeat safely; unchanged documents produce no writes:
docker compose exec worker python ingest.py /runbooks
# Real query returns five chunks with filenames, text and similarity scores:
docker compose exec worker python retrieval.py "Kafka consumer lag and committed offsets stopped advancing"
./scripts/test-api.sh
./scripts/test-worker.sh
python3 scripts/verify-event-flow.py
```

Flyway V4 adds incidentiq_api.runbook_documents, runbook_chunks and incident_retrievals. Existing public.runbook_chunks is preserved as a legacy table and is not the new retriever's corpus. Content/config fingerprints and deterministic UUIDs make ingestion idempotent. Updates replace a changed file's chunks in one transaction; existing retrieved content snapshots remain intact. Files removed from disk are not automatically purged from the database.

For each newly processed event, the worker retrieves five nearest chunks using service/title/description. It saves rank, source filename, chunk UUID, content snapshot, cosine similarity, model/revision and retrieval time together with the receipt and RECEIVED status. A replay does not overwrite retrievals or regenerate embeddings. Retrieval failure rolls back receipt/status/context and enters the existing retry/quarantine path; no successful offset acknowledgement occurs before durable handling. Existing pre-retrieval receipts are not backfilled or reprocessed.

Scores are cosine similarities, not calibrated confidence or proof that a runbook applies. Five chunks can come from the same source file. Long queries are subject to the model's 256-token window; service/title appear before the description. No LLM diagnosis is generated and no new REST endpoint for retrieved context is added in this milestone. Inspect snapshots directly in PostgreSQL:

```sql
SELECT rank, source, similarity, content
FROM incidentiq_api.incident_retrievals
WHERE incident_id = 'REPLACE_WITH_UUID' ORDER BY rank;
```

See [retrieval-verification.md](docs/retrieval-verification.md) for actual ingestion, relevance and end-to-end results. Model details: [official model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2); retriever interface: [LangChain BaseRetriever](https://reference.langchain.com/python/langchain-core/retrievers/BaseRetriever).
