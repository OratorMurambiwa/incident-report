# IncidentIQ agent guide

## Objectives and scope

Build a local AI-powered incident monitoring platform: ingest events, persist incidents, analyze asynchronously, retrieve runbook context, and present evidence-backed recommendations. Keep execution and data local. Do not create remote repositories, deploy cloud resources, or use paid services without explicit authorization. Incident creation/query and diagnosis lookup are implemented. Transactional outbox publication and idempotent Python receipt consumption are implemented. Local embedding inference and runbook retrieval are implemented; optional Ollama structured diagnosis generation is implemented, defaulting to clearly labeled retrieval-only results. The live frontend remains a scaffold. Actual Ollama generation was not verified in the current environment.

## Architecture

Current flow: Spring Boot API → PostgreSQL incident + outbox → separate Spring Kafka publisher → `incident.created` → Python worker → pgvector top-five runbook context + durable receipt + diagnosis (RETRIEVAL_ONLY/RECEIVED or GENERATED/DIAGNOSED). Future flow extends React → API → Python worker → local generative diagnosis analysis → PostgreSQL and `incidents.analyzed` → API → React. Prometheus scrapes API/worker metrics; Grafana visualizes them. Treat DB/event dual writes with an outbox when implementing ingestion. Consumers must be idempotent, commit offsets after successful persistence, and support bounded retries/dead-letter handling.

## Technologies and versions

Java 21; Spring Boot 3.5.16 (use its dependency management for Spring Kafka, JDBC and Micrometer); Maven 3.6.3+; Python 3.12; LangChain 0.3.27; PostgreSQL 16; pgvector 0.8.7; Kafka 3.9.1 in single-node KRaft; React 19.1.1; Vite 6.3.5; Node 22.12+; Docker Compose v2; Prometheus 3.5.0; Grafana 12.1.0. See manifests for remaining Python pins. Verify compatibility before dependency upgrades; generate dependency locks with actual tools, never fabricate them.

## Directories

`api` owns HTTP, database migrations and incident writes. `worker` owns asynchronous analysis/retrieval. `runbooks` stores Markdown knowledge. `frontend` owns React UI. `infra` owns local service configuration. `scripts` holds repeatable automation. `docs` records architecture and validation evidence.

## Implemented API and persistence

Spring Web + Spring Data JPA + Jakarta Validation + Flyway, managed by Spring Boot. Package com.incidentiq has incident/diagnosis/common layers. DTOs are records; services own transactions; controllers use constructor injection. UUID incident IDs, UTC microsecond timestamps, severity LOW/MEDIUM/HIGH/CRITICAL, server-owned initial status PENDING. POST /api/incidents returns 201 + Location + incident DTO. GET collection returns a page envelope (page >= 0, size 1–100, default 20); GET /{id} and /{id}/diagnosis return 404 when absent. Worker diagnosis generation is implemented with provider none/ollama; GET exposes structured provenance and cited evidence. Errors use centralized Problem Detail handling. Unknown JSON fields are rejected.

Flyway owns the incidentiq_api schema, separate from public.runbook_chunks/pgvector. V1 creates incidents and diagnoses, one diagnosis per incident, with foreign keys and checks. Hibernate ddl-auto=validate and open-in-view=false. Never change an applied migration or use Hibernate auto-DDL. Create persists incident and outbox together. Flyway V2 adds outbox_events, processed_events and failed_events plus RECEIVED status; V3 retains NULL Kafka tombstones. Never modify applied migrations (V1–V5). V5 adds structured diagnosis/provenance fields and DIAGNOSED while labeling old rows LEGACY. V4 adds managed runbook documents/chunks and immutable incident retrieval snapshots; public.runbook_chunks is preserved as legacy. The publisher is a separate non-web Java process enabled with OUTBOX_PUBLISHER_ENABLED=true; keep scheduling disabled for API/tests. Compose API uses postgres:5432 and kafka:29092; PostgreSQL host port remains 55432. Preserve working Kafka/storage settings.

## Coding standards

Use Java 4-space indentation, constructor injection, explicit DTOs and input validation. Keep controllers thin; place logic in services. Use Python type hints, small functions, structured logging and explicit configuration. React should use function components and accessible semantic HTML. Never log secrets or entire incident payloads. Keep credentials in ignored `.env` files. Use parameterized SQL, versioned schema migrations, UTC timestamps and explicit event schema versions. Match embedding dimensions (currently 384) to the selected local model. Do not silently fall back to hosted AI. Recommendations must cite retrieved runbooks and express uncertainty.

## Commands

- Inspect environment: `./scripts/doctor.sh`
- Validate Compose: `docker compose config --quiet`
- Start dependencies: `./scripts/start.sh`
- Start monitoring too: `./scripts/start.sh --profile observability`
- Status/logs: `docker compose ps -a`, `docker compose logs --tail=100`
- Stop preserving data: `docker compose --profile observability down`
- Build Spring Boot API without host Java/Maven: `docker build --progress=plain -t incidentiq-api:local ./api` (multi-stage Maven/Java 21 build runs `mvn verify`).
- Test API with real PostgreSQL using Docker only: `./scripts/test-api.sh` (isolated incidentiq_api_test database; transactional rollback). Ordinary Docker build runs controller/service tests and skips database tests.
- Build/start API: `docker compose up -d --build --wait`; API http://localhost:8080.
- Real HTTP checks: `python3 scripts/verify-api.py` (creates and retains a synthetic incident; requires running API).
- Verify infrastructure: `./scripts/verify-infra.sh` (PostgreSQL TCP, vector arithmetic and Kafka produce/consume).
- Optional host API workflow: `cd api && mvn spring-boot:run`; verify: `mvn test`
- Worker tests: run `./scripts/test-api.sh` then `./scripts/test-worker.sh` (Docker-only tests using isolated incidentiq_api_test database).
- Full event flow and replay/quarantine checks: `python3 scripts/verify-event-flow.py` (requires running Compose, retains synthetic evidence).
- Worker: Compose builds/tests/runs the Python 3.12 worker; optional host development uses worker/requirements.txt.
- Worker syntax: `python3 -m compileall worker`
- Frontend: `cd frontend && npm install && npm run dev`; verify: `npm run build`

Before reporting success, distinguish static checks, dependency resolution, builds and real integration checks. Add meaningful tests for event contracts, retries, persistence and analysis as implemented. Never delete persistent volumes without explicit authorization. See docs/environment.md for known missing tools.

## Delivery reliability

Contract: incident.created JSON schemaVersion=1, eventId/incidentId UUID strings, service/title/description strings, severity enum and timezone-aware timestamp. Publisher locks one eligible outbox row with FOR UPDATE SKIP LOCKED, waits for acks=all, then commits published_at. Persist retry/backoff metadata; never remove failed outbox rows. At-least-once delivery is intentional.

Worker receipt and PENDING→RECEIVED transition are atomic. Deduplicate by eventId and canonical payload hash; do not regress later statuses. Commit only the specific consumed offset after PostgreSQL commit or durable quarantine. Bounded retries: 3 for processing; malformed/conflicting events go directly to failed_events. If quarantine storage or offset commit fails, crash/restart without consuming later offsets. Quarantined payloads are sensitive, local data: do not log them; inspect and replay explicitly after fixing causes. See docs/event-delivery.md and docs/event-verification.md. Original 26 test cases must remain covered; constructor dependency wiring can change as needed.

## Local retrieval

Model: sentence-transformers/all-MiniLM-L6-v2, revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf, 384 dimensions, normalized CPU embeddings. sentence-transformers 3.4.1, transformers 4.48.3 and CPU torch 2.6.0+cpu are pinned; worker/requirements.lock records actual resolved transitive versions and is used as constraints. Never fabricate locks or silently download another model. Runtime uses local_files_only plus offline/tracing-disabled environment flags.

LangChain MarkdownHeaderTextSplitter + token-aware RecursiveCharacterTextSplitter use 180 tokens, 30 overlap and a chunking-version fingerprint. Ingestion skips unchanged files and atomically replaces chunks of changed sources using deterministic UUIDs; filenames are unique. README.md is excluded. Missing disk files are not automatically purged. The default ten runbooks produce 60 chunks. Compose runbook-ingest runs after API migration and before the worker starts.

PgRunbookRetriever.invoke uses exact pgvector cosine distance to return five LangChain Documents. Worker snapshots rank/source/content/score/model/revision in incident_retrievals in the same transaction as receipt/status. Duplicate event IDs return before retrieval. Retrieval failure or insufficient corpus rolls back and follows existing retries/quarantine. Do not backfill prior processed receipts implicitly. Scores are similarities, not confidence. Optional local Ollama generation is implemented; retrievedEvidence is exposed by the diagnosis endpoint.

Commands: `docker compose exec worker python ingest.py /runbooks`; `docker compose exec worker python retrieval.py "query"`; `./scripts/test-api.sh` followed by `./scripts/test-worker.sh` for real model/database relevance, ingestion and pipeline regression tests. `python3 scripts/verify-event-flow.py` checks five persisted snapshots and their preservation on replay. See docs/retrieval-verification.md for executed evidence.

## RAG diagnosis rules

LLM_PROVIDER=none (default): persist a clearly labeled RETRIEVAL_ONLY result; no generated causes/steps/remediation. Original excerpts only under retrievedEvidence. LLM_PROVIDER=ollama requires OLLAMA_MODEL for an already-installed local model and a reachable local OLLAMA_BASE_URL. Never auto-pull models or fall back silently to none on generation failure. Ollama generation has not been exercised against an actual model yet; tests use mocked responses.

worker/diagnosis.py uses LangChain prompt/runnable/parser with Ollama JSON-schema output, strict complete-JSON validation and application citation checks. Treat both incident text and evidence as untrusted user data. No tools/agents/command execution. Every generated statement needs nonempty exact filenames from supplied snapshots. Reject unknown citations/extra fields/partial JSON; derive citedRunbooks from validated sources. Always state uncertainty and require human review; validation does not prove semantic correctness. Keep none-mode evidence distinct from AI-generated text.

Diagnoses persist to the existing table with structured JPA mappings. Legacy text is preserved as LEGACY. Receipt/snapshots/diagnosis/status are atomic. Duplicates return before LLM invocation. None → RECEIVED; successful generation → DIAGNOSED, never RESOLVED. Exhausted ModelUnavailable/InvalidDiagnosis/MissingEvidence failures retain the raw record and mark only still-pending incidents FAILED in the quarantine transaction. Offsets advance only afterward. Quarantine persistence/offset commit failures must still stop processing; manual unchanged replay can recover FAILED incidents. Never overwrite pre-existing diagnoses or implicitly regenerate historical receipts.

Run all Java tests: ./scripts/test-api.sh. Then Python real-model/database tests: ./scripts/test-worker.sh (forces none for predictable integration tests; explicit mocks exercise ollama). Verify actual diagnosis endpoint: python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY; use --expect-mode GENERATED only with a reachable installed local model configured in the worker. Report actual Ollama generation separately from mocked tests and retrieval-only runtime checks. Current evidence: docs/rag-verification.md.

## Git workflow after each major milestone

After completing and successfully testing each major development milestone:

1. Review `git status` and all changes.
2. Run relevant automated tests and fix failures before treating the milestone as complete.
3. Verify no secrets, `.env` files, credentials, database files or generated artifacts are staged. Review the staged diff and ignored files explicitly; retain `.env.example` only with documented local-development placeholders.
4. Create a descriptive commit using the user's existing Git author identity. Do not replace it with a placeholder or tool identity.
5. Do not add AI tools as co-authors or include `Co-authored-by` trailers.
6. Push the commit to `origin/main` using a normal push.
7. Verify the remote branch contains the new commit.
8. Report the commit SHA, tests passed and GitHub link.

Never force-push, rewrite history or delete unrelated files. If tests fail or a push is rejected, stop the publication workflow and explain the issue instead of claiming success; do not commit/push failing changes or bypass a rejection. Keep all work and data intact. Obtain no additional confirmation for this explicitly authorized workflow, but respect any later instruction to stop publishing.
