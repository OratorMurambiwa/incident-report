# IncidentIQ

Local incident monitoring platform with a working Java 21 REST API and PostgreSQL persistence. Incident creation now flows through a transactional outbox and Kafka to a Python worker that records RECEIVED. The worker now retrieves local runbook context with LangChain and pgvector. Optional local Ollama RAG diagnosis generation is implemented; default mode is explicitly retrieval-only. The React/TypeScript dashboard provides live incident filtering, submission and diagnosis evidence. No paid or hosted AI service is configured.

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
- `GET /api/incidents/{id}/diagnosis`: 200 with diagnosis UUID, incidentId, summary, recommendations and timestamps. Returns 404 when the incident is missing or its diagnosis is not yet available. The worker persists retrieval-only or Ollama-generated diagnoses asynchronously; no public diagnosis write endpoint exists.

Creation requires nonblank `service` (max 100), `title` (max 200), `description` (max 10000), and severity `LOW`, `MEDIUM`, `HIGH` or `CRITICAL`. Strings are trimmed. Status is server-owned; client-supplied status and unknown properties are rejected. Stored status values are PENDING, RECEIVED, ANALYZING, DIAGNOSED, RESOLVED and FAILED. Creation returns PENDING. The worker sets RECEIVED for retrieval-only results or DIAGNOSED for a generated diagnosis; DIAGNOSED does not mean RESOLVED. Invalid JSON, enum values, UUIDs or pagination produce 400. Errors use Problem Detail JSON; field-validation errors include an `errors` map. Database constraint conflicts produce 409, unexpected failures produce a generic 500.

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
- `worker/`: Python 3.12 / Kafka receipt consumer, PostgreSQL idempotency and metrics (local sentence-transformers retrieval; optional local Ollama RAG diagnoses).
- `frontend/`: React 19 / TypeScript / Vite dashboard connected through the nginx API proxy.
- `runbooks/`: Markdown sources for future local retrieval.
- `infra/`: database bootstrap and monitoring configuration.
- `scripts/`: environment checks and repeatable testing/startup commands.
- `docs/`: architecture and verification evidence.

For optional host API development, install Java 21/Maven and export the database variables from .env, then `cd api && mvn spring-boot:run`. Stop the Compose API first to free port 8080. Run the worker through Compose so the pinned CPU packages and model files are available. For the frontend: Node 22.12+ and npm, then `cd frontend && npm ci && npm run dev`. No host Python/Node is needed for the Dockerized dashboard, API or tests.

Optional Prometheus runs at localhost:9090 and Grafana at localhost:3001 (admin/password from .env). API metrics are exposed at /actuator/prometheus. Both application scrapes use internal Docker addresses, independent of API_PORT. A 16-panel dashboard is provisioned. Optional local Ollama diagnosis generation is implemented but live model inference was not available in this verification environment. Local embedding inference and runbook retrieval are implemented.

## Event delivery and worker

`POST /api/incidents` inserts an `incident.created` event into `incidentiq_api.outbox_events` in the same transaction as the incident. JSON contains schemaVersion=1, eventId, incidentId, service, title, description, severity and an ISO-8601 timestamp. Kafka keys are incident UUIDs. The separate publisher uses Spring Kafka with acks=all and producer idempotence, marks published_at only after acknowledgement and retries unsent rows with persisted exponential backoff (2–256 seconds). Delivery is at least once; a crash after acknowledgement can cause a duplicate.

The Python worker validates the contract, inserts a processed_events receipt keyed by eventId, and stores retrieval snapshots plus a diagnosis in one PostgreSQL transaction. Its resulting status is RECEIVED for retrieval-only or DIAGNOSED for generated analysis. Replayed IDs with the same payload do not change status or timestamps. IDs reused with different payloads are rejected. Advanced statuses never regress. Kafka auto-commit is disabled; only the current partition's offset is committed after durable handling.

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

Verification retains synthetic incidents and a malformed-message failure record. See [event-delivery.md](docs/event-delivery.md) for the contract, retries and operations, and [event-verification.md](docs/event-verification.md) for executed results. RECEIVED denotes retrieval-only processing; only GENERATED diagnoses use Ollama, with status DIAGNOSED.

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

Scores are cosine similarities, not calibrated confidence or proof that a runbook applies. Five chunks can come from the same source file. Long queries are subject to the model's 256-token window; service/title appear before the description. Optional Ollama diagnosis generation is described below. Retrieved evidence is returned with the existing diagnosis endpoint. Inspect snapshots directly in PostgreSQL:

```sql
SELECT rank, source, similarity, content
FROM incidentiq_api.incident_retrievals
WHERE incident_id = 'REPLACE_WITH_UUID' ORDER BY rank;
```

See [retrieval-verification.md](docs/retrieval-verification.md) for actual ingestion, relevance and end-to-end results. Model details: [official model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2); retriever interface: [LangChain BaseRetriever](https://reference.langchain.com/python/langchain-core/retrievers/BaseRetriever).

## RAG diagnosis providers

Default `LLM_PROVIDER=none` persists mode `RETRIEVAL_ONLY`, provider `none`, model `null`. Summary/recommendations explicitly say no language model was used. `likelyCauses`, `investigationSteps` and `suggestedRemediation` are empty; the five original excerpts appear only under `retrievedEvidence`, with chunkId/source/similarity. Retrieved content is not presented as AI-generated analysis.

To use an already-running local Ollama server, edit the ignored `.env`:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_MODEL=your-installed-local-model
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_TIMEOUT_SECONDS=30
```

```bash
# Existing dependencies must already be running. Recreate only the worker after .env changes:
docker compose up -d --no-deps --force-recreate worker
python3 scripts/verify-rag-flow.py --expect-mode GENERATED
```

The model must already be installed in Ollama; IncidentIQ never pulls it automatically. The server must be reachable from the container. Supported configured endpoint hosts are localhost, 127.0.0.1, ::1, host.docker.internal and ollama (a local Docker service name). Loopback inside a container refers to that container. HTTP proxies, redirects, credential-bearing URLs and nonlocal endpoint names are rejected/disabled. No hosted provider is supported. Request timeout is bounded to 1–30 seconds, with three worker attempts before durable quarantine.

The LangChain LCEL chain uses ChatPromptTemplate → a local Ollama /api/chat adapter → PydanticOutputParser. The client requests JSON-schema output and strictly validates complete JSON before the parser, rejecting partial responses. Schema fields are summary, likely_causes, investigation_steps, suggested_remediation and uncertainty; each list item contains text and a nonempty sources array. Allowed filenames come only from the five retrieved chunks. Unknown citations, including invented Markdown filenames in prose, are rejected; the server derives citedRunbooks from validated item sources. The prompt treats incident/evidence text as untrusted data and does not expose tools or execute remediation. Generated suggestions require human review; syntactic citation checks do not prove that a hypothesis is correct.

Flyway V5 extends the existing diagnoses table and labels pre-existing rows LEGACY without rewriting their original summary/recommendations. The existing GET /api/incidents/{id}/diagnosis now includes mode/provider/model/eventId, likelyCauses, investigationSteps, suggestedRemediation, citedRunbooks, retrievedEvidence and uncertainty, alongside the original fields.

Receipt, five snapshots, diagnosis and incident status commit atomically. Duplicate event IDs return before retrieval/generation; no diagnosis is overwritten. A successful GENERATED result sets DIAGNOSED, never RESOLVED. Retrieval-only sets RECEIVED. Unavailable models, invalid outputs and missing evidence roll back new processing; after bounded retries, the original event is durably quarantined and a still-pending incident is marked FAILED. No silent retrieval-only fallback occurs. Kafka offsets advance only after the successful transaction or durable quarantine transaction. Manual unchanged replay after fixing configuration can recover FAILED incidents. Existing receipts are not backfilled or regenerated automatically.

```bash
# Restore/default safe mode by setting LLM_PROVIDER=none in .env and recreating the worker.
./scripts/test-api.sh
./scripts/test-worker.sh
python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY
```

Verified here: 34 Java tests, 68 Python tests, actual retrieval-only HTTP/Kafka/database diagnosis flow and duplicate preservation. Ollama client/generation paths used mocked responses and unavailable-model simulations. **At that milestone, actual Ollama generation was not tested**: no model was configured and the local endpoint was unreachable. See [rag-verification.md](docs/rag-verification.md) for commands and actual outputs.

## Prometheus and Grafana observability

```bash
docker compose --profile observability up -d --build --wait
python3 scripts/verify-monitoring.py
```

- Grafana dashboard: http://localhost:3001/d/incidentiq-overview (login `admin`, password from ignored `.env`).
- Prometheus: http://localhost:9090 (targets at http://localhost:9090/targets).
- API exporter: http://localhost:8080/actuator/prometheus.

Prometheus scrapes `api:8080/actuator/prometheus` and `worker:8001/metrics` every five seconds over Docker networking. Grafana's Prometheus datasource and 16-panel **IncidentIQ · Local Operations** dashboard are provisioned from infra/grafana. Existing named volumes store Prometheus history and Grafana state; stopping services without `--volumes` preserves them. PostgreSQL remains published at 55432.

The dashboard shows request traffic/counts, estimated HTTP p95 latency, separate 4xx/5xx error rates, JVM heap/nonheap memory, persisted incident totals/by-status counts, worker processing/retrieval latency and diagnosis outcomes. Actuator traffic is excluded from API traffic/error panels. API p95 uses histogram buckets rather than averaging percentiles.

HTTP URI tags use MVC templates and a 32-value cap. Custom incident labels are restricted to the six status values; worker diagnosis labels are only outcome=success/failure and mode=retrieval_only/generated. No incident/event IDs, service names, filenames or model names become metric labels.

Worker diagnosis successes increment after database commit, and duplicate events do not increment them. Valid workflows durably quarantined after failure increment failure counters; malformed/conflicting events remain in the separate quarantine counter. Processing duration covers retries and offset commit. Retrieval latency covers local query embeddings and vector search, including failed attempts. Counters reset on process restart; Prometheus rate calculations handle resets, and dashboard totals explicitly say 'since restart'. Persisted incident gauges read PostgreSQL and survive API restarts. Database outages produce NaN for those gauges, not a misleading zero.

`verify-monitoring.py` creates synthetic HTTP success/error traffic and one valid Kafka event referencing a nonexistent synthetic incident to exercise failure metrics. It retains the incident/diagnosis and durable quarantine evidence. It verifies both targets, real metric samples, database count agreement, bounded labels, datasource health and numeric data for every dashboard panel. `--no-fixtures` avoids new fixtures but requires recent metric activity for latency checks.

Full verification, including browser rendering, is documented in [monitoring-verification.md](docs/monitoring-verification.md). The optional browser capture helper runs in a temporary Playwright container; it adds no host/application dependency and saves screenshots under ignored .incidentiq-backups/monitoring.

## Automatic incident detection

Prometheus → Alertmanager → `POST /api/alerts/alertmanager` → transactional incident/outbox → Kafka → retrieval/RAG worker → stored diagnosis. Alertmanager is available at http://localhost:9093 with the observability profile. Fingerprints deduplicate active incidents across retries and API restarts. Resolved notifications mark the incident RESOLVED; a delayed worker preserves that status. A new occurrence after resolution creates a new incident. Webhook payloads are validated and retained as untrusted evidence.

Rules detect HTTP 500 rates above 20% with at least three failures in one minute, p95 latency above 500ms with at least three requests, and unavailable API/worker/Alertmanager scrape targets. Error/latency conditions persist 15 seconds; unavailability persists 30 seconds. Internal monitoring, incident and webhook routes are excluded from error/latency alerts to prevent recursion. Thresholds and short repeat intervals are intended for local development.

```bash
docker compose --profile observability up -d --build --wait
# Temporarily enables bounded dev simulators and restores the default API afterward:
python3 scripts/smoke-auto-detection.py
```

Simulators return 404 by default. Explicit opt-in uses `docker compose -f compose.yaml -f compose.dev.yaml up -d --wait api`; GET `/api/dev/simulate/failure` returns 500 and GET `/api/dev/simulate/latency?delayMs=750` delays up to 2000ms. Both the dev profile and simulation flag are required; prod/production profiles disable them even with the flag. Restore default settings with `docker compose up -d --no-deps --wait api`.

Availability alerts measure exporter reachability. An unavailable API cannot receive its own webhook until recovery; an unavailable Alertmanager cannot deliver until recovery. This single-host setup is not an external watchdog. See [actual verification results](docs/automatic-detection-verification.md).

## React incident dashboard

Open **http://localhost:5173** after starting Compose:

```bash
docker compose --profile observability up -d --build --wait
# Optional real-browser verification (creates and retains synthetic incidents):
bash scripts/test-dashboard.sh
```

The dashboard uses real API data: newest-first paginated incidents, severity/status filters, case-insensitive service search, manual incident reporting and shareable incident details. Click Apply service after entering a service substring; Clear filters resets all filters. Lists refresh every ten seconds, details and diagnoses every five seconds. Times display in the browser's local timezone. Loading, empty results, processing failures and request errors have explicit states and retry controls.

Details show the incident description, diagnosis provenance, cited runbooks and expandable original evidence with similarity scores. RETRIEVAL_ONLY means no language model was used; excerpts are not generated advice. AI-generated results show cited likely causes, investigation steps and suggested remediation with a human-review notice. No commands are executed. Monitoring links open Grafana, Prometheus and Alertmanager in separate tabs; start the observability profile to use them.

The multi-stage frontend Dockerfile runs Node tests, strict TypeScript checking and Vite build, then nginx serves static files and proxies /api over internal Docker networking. No host Node installation or CORS configuration is required. FRONTEND_PORT defaults to 5173; PostgreSQL stays at 55432. Keep .env ignored; no credentials are embedded in the browser bundle.

Optional host development: `cd frontend && npm ci && npm run dev` (Node 22.12+). The Vite proxy targets localhost:8080; API_PROXY_TARGET can override it for local development. Run `npm test && npm run build` for frontend unit tests and compilation. See [verification evidence](docs/dashboard-verification.md).

## Optional local CPU Ollama verification

Actual qwen3:0.6b generation was verified through React and stored diagnoses. Initial review found a contradicted Kafka offset prohibition; a fail-closed guard now rejects that advice, tested with real model output. Keep retrieval-only as the default and review every generated suggestion. These tests verify sampled fields and failure behavior, not general semantic correctness. See [actual findings and limitations](docs/ollama-verification.md).

Retrieval-only (`LLM_PROVIDER=none`) remains the base configuration. The explicit `compose.ollama.yaml` override uses private Docker DNS `http://ollama:11434`; container localhost is not the host. It publishes no Ollama port and uses no paid/hosted model service. It is for x86-64 CPUs with AVX2/FMA/F16C support.

```bash
# Build a small CPU runtime and the worker; no GPU toolkit/image downloads:
docker compose -f compose.yaml -f compose.ollama.yaml build ollama worker
docker compose -f compose.yaml -f compose.ollama.yaml up -d --no-deps --wait ollama
# Explicit one-time model download, about 523 MB (never automatic):
docker compose -f compose.yaml -f compose.ollama.yaml exec ollama ollama pull qwen3:0.6b
docker build -t incidentiq-browser:local infra/browser
# Requires the existing API/frontend/publisher/dependencies running, initially in none mode:
python3 scripts/verify-local-ollama.py
```

The verifier submits three real React incidents, checks generated diagnoses and persisted receipts/evidence, then exercises an actual adversarial model response, a missing model and a one-second timeout. It retains synthetic records and negative-case quarantine evidence. It restores the base worker in a finally block. Generated/error answers are never executed as commands. Browser captures and proof JSON stay in ignored .incidentiq-backups/ollama-verification.

To opt in outside the verifier, start only the worker with `docker compose -f compose.yaml -f compose.ollama.yaml up -d --no-deps --wait worker` after the runtime and model are ready. Restore retrieval-only with `docker compose up -d --no-deps --wait worker`. Failed generation is durably quarantined, never silently relabeled retrieval-only; restoring the base configuration affects new events, not historical diagnoses. Stop the optional runtime with `docker compose -f compose.yaml -f compose.ollama.yaml stop ollama`; preserve ollama_data.

The CPU image assembles a hash-pinned official Ollama 0.6.8 executable (11 MB compressed) and AVX2 libraries compiled from the matching pinned upstream source (8 MB compressed). This avoids the release image's large GPU library layer. A separate persistent volume caches the explicitly selected model. CPU resources are limited to four CPUs and 2500 MiB; requests use four threads, 8192 context tokens and at most 512 output tokens, with one cited item per category for this small model. The API/storage schema still supports earlier multi-item diagnoses. See [actual local generation verification](docs/ollama-verification.md).

## Local performance benchmarks

```bash
docker pull grafana/k6:1.3.0
python3 -m unittest discover -s benchmarks -p 'test_*.py' -v
python3 scripts/benchmark.py run
```

Uses bounded Dockerized k6 workloads, a separate owned database and Kafka broker, and retrieval-only mode. Measures API request rate/average/p95/p99/error rate separately from a 60-event Kafka-to-committed-diagnosis batch. Existing incidents, main Kafka data, PostgreSQL port 55432 and Docker volumes are preserved. Benchmarks retain their isolated database and results; explicit guarded cleanup is documented.

The measured local baseline observed 65.80 read requests/s, 17.02 incident creates/s and 6.19 asynchronously processed events/s, with zero failures under the recorded quotas/workloads. These are bounded offered-load measurements, not maximum capacity claims. See [actual results and hardware](docs/benchmarks/RESULTS.md) and [methodology/reproduction/cleanup](docs/benchmarks/README.md). Ollama is excluded and must be measured separately.
