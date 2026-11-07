# IncidentIQ agent guide

## Objectives and scope

Build a local AI-powered incident monitoring platform: ingest events, persist incidents, analyze asynchronously, retrieve runbook context, and present evidence-backed recommendations. Keep execution and data local. Do not create remote repositories, deploy cloud resources, or use paid services without explicit authorization. Incident creation/query and diagnosis lookup are implemented. Transactional outbox publication and idempotent Python receipt consumption are implemented. Local embedding inference and runbook retrieval are implemented; optional Ollama structured diagnosis generation is implemented, defaulting to clearly labeled retrieval-only results. The React/TypeScript dashboard lists, filters, submits and inspects real incidents and diagnosis evidence. Actual CPU Ollama generation has been exercised end to end. An initial forward-offset contradiction was repaired with a fail-closed guard and retested against actual model output. Keep provider none by default; see docs/ollama-verification.md for measured results and remaining quality limits.

## Architecture

Current flow: React dashboard → Spring Boot API → PostgreSQL incident + outbox → separate Spring Kafka publisher → `incident.created` → Python worker → pgvector top-five runbook context + durable receipt + diagnosis (RETRIEVAL_ONLY/RECEIVED or GENERATED/DIAGNOSED). Future flow extends React → API → Python worker → local generative diagnosis analysis → PostgreSQL and `incidents.analyzed` → API → React. Prometheus scrapes API/worker metrics; Grafana visualizes them. Treat DB/event dual writes with an outbox when implementing ingestion. Consumers must be idempotent, commit offsets after successful persistence, and support bounded retries/dead-letter handling.

## Technologies and versions

Java 21; Spring Boot 3.5.16 (use its dependency management for Spring Kafka, JDBC and Micrometer); Maven 3.6.3+; Python 3.12; LangChain 0.3.27; PostgreSQL 16; pgvector 0.8.7; Kafka 3.9.1 in single-node KRaft; React 19.1.1; Vite 6.4.5; Node 22.12+; Docker Compose v2; Prometheus 3.5.0; Grafana 12.1.0; Alertmanager 0.28.1; Dockerized k6 1.3.0. See manifests for remaining Python pins. Verify compatibility before dependency upgrades; generate dependency locks with actual tools, never fabricate them.

## Directories

`api` owns HTTP, database migrations and incident writes. `worker` owns asynchronous analysis/retrieval. `runbooks` stores Markdown knowledge. `frontend` owns React UI. `infra` owns local service configuration. `scripts` holds repeatable automation. `docs` records architecture and validation evidence.

## Implemented API and persistence

Spring Web + Spring Data JPA + Jakarta Validation + Flyway, managed by Spring Boot. Package com.incidentiq has incident/diagnosis/common layers. DTOs are records; services own transactions; controllers use constructor injection. UUID incident IDs, UTC microsecond timestamps, severity LOW/MEDIUM/HIGH/CRITICAL, server-owned initial status PENDING. POST /api/incidents returns 201 + Location + incident DTO. GET collection returns a page envelope (page >= 0, size 1–100, default 20); GET /{id} and /{id}/diagnosis return 404 when absent. Worker diagnosis generation is implemented with provider none/ollama; GET exposes structured provenance and cited evidence. Errors use centralized Problem Detail handling. Unknown JSON fields are rejected.

Flyway owns the incidentiq_api schema, separate from public.runbook_chunks/pgvector. V1 creates incidents and diagnoses, one diagnosis per incident, with foreign keys and checks. Hibernate ddl-auto=validate and open-in-view=false. Never change an applied migration or use Hibernate auto-DDL. Create persists incident and outbox together. Flyway V2 adds outbox_events, processed_events and failed_events plus RECEIVED status; V3 retains NULL Kafka tombstones. Never modify applied migrations (V1–V6). V5 adds structured diagnosis/provenance fields and DIAGNOSED while labeling old rows LEGACY. V4 adds managed runbook documents/chunks and immutable incident retrieval snapshots; public.runbook_chunks is preserved as legacy. The publisher is a separate non-web Java process enabled with OUTBOX_PUBLISHER_ENABLED=true; keep scheduling disabled for API/tests. Compose API uses postgres:5432 and kafka:29092; PostgreSQL host port remains 55432. Preserve working Kafka/storage settings.

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
- Frontend: `cd frontend && npm ci && npm run dev`; verify: `npm run build`

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

LLM_PROVIDER=none (default): persist a clearly labeled RETRIEVAL_ONLY result; no generated causes/steps/remediation. Original excerpts only under retrievedEvidence. LLM_PROVIDER=ollama requires OLLAMA_MODEL for an already-installed local model and a reachable local OLLAMA_BASE_URL. Never auto-pull models or fall back silently to none on generation failure. Actual qwen3:0.6b generation and sampled evidence-backed fields were checked separately from mocked unit tests. The initial semantic failure is documented and guarded; citation checks and the narrow offset guard do not verify general entailment.

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

## Monitoring

Actuator/Micrometer HTTP request histograms and JVM metrics are enabled. IncidentMetrics registers PostgreSQL-backed incident totals and six bounded status gauges; DB outages return NaN. HTTP URI labels use MVC templates and a 32-value MeterFilter cap. Never add incident IDs, event IDs, filenames, model names, service names or unbounded exception messages to metric labels.

worker/metrics.py defines processing/retrieval histograms and diagnosis outcomes. Increment success only after PostgreSQL commit, never on duplicates or rolled-back attempts. Increment valid workflow failure after durable quarantine, excluding malformed/conflicting records. Processing time includes retries/offset commit; retrieval time includes embeddings/vector SQL per attempt. Counter values are process-lifetime measurements, not durable database totals.

Use `docker compose --profile observability up -d --build --wait`; Prometheus scrapes api:8080/actuator/prometheus and worker:8001/metrics internally. Grafana uses the provisioned prometheus datasource and incidentiq-overview dashboard. Preserve prometheus_data/grafana_data plus all existing volumes. URLs: http://localhost:9090 and http://localhost:3001/d/incidentiq-overview; admin password remains in ignored .env.

Run `python3 scripts/verify-monitoring.py` for live datasource/panel checks (creates explicit synthetic success/error/failure fixtures). Optional scripts/capture-monitoring.py runs inside Playwright, never the application container. Set a valid browser locale (en-US); screenshots/JSON evidence remain under ignored .incidentiq-backups/monitoring. Read docs/monitoring-verification.md for actual results.

SimpleMeterRegistry in the installed Micrometer version has close() but does not implement AutoCloseable: use a normal variable and try/finally cleanup in tests. Verify all Java/Python suites and actual Grafana rendering before applying the Git publication workflow.

## Automatic detection

Prometheus rules in infra/prometheus/alerts.yml send firing/resolved webhooks through Alertmanager to POST /api/alerts/alertmanager. V6 persists lowercase fingerprint locks, occurrence history and resolved tombstones. Keep incident creation/outbox atomic; serialize each fingerprint with a database row lock and sort batches to avoid lock-order deadlocks. Repeated active alerts reuse one incident; stale firing/resolved notifications must not reopen or close newer occurrences. Standard webhook metadata is accepted only on alert DTOs. Never execute payload commands or follow payload URLs. Worker processing must preserve RESOLVED status even if resolution precedes consumption.

Error and latency rules exclude /actuator.*, /api/incidents.* and /api/alerts.* to prevent recursive incident storms. Availability rules monitor scrape reachability, not database readiness. Local Alertmanager repeats every 20 seconds for demonstration. Preserve alertmanager_data alongside existing volumes. Alertmanager UI: http://localhost:9093.

Simulation requires BOTH the dev profile and incidentiq.simulation.enabled=true; prod/production profiles always disable it. Base Compose leaves simulation disabled. Explicit local opt-in: docker compose -f compose.yaml -f compose.dev.yaml up -d --wait api. Restore with docker compose up -d --no-deps --wait api. Never enable the dev override in production.

Run python3 scripts/smoke-auto-detection.py for real HTTP 500, latency and stopped-worker alert flows, repeat deduplication, resolution, Kafka evidence and stored diagnoses. It temporarily enables development simulation, restarts the worker and restores the base API in finally; retains synthetic evidence, never deletes volumes. Promtool rule tests are infra/prometheus/alerts_test.yml. See docs/automatic-detection-verification.md for executed checks and limitations.

## React dashboard

Frontend uses React 19, strict TypeScript 5.8.3 and Vite 6.4.5 with a generated npm lock. No UI/router/chart libraries. Docker builds with Node 22 and serves static assets through nginx on http://localhost:5173 (FRONTEND_PORT). Same-origin /api requests proxy to api:8080 through Docker DNS, avoiding CORS and browser-visible internal hostnames. Vite host development proxies /api to localhost:8080; API_PROXY_TARGET overrides that local development target. Never put credentials in VITE_* variables or frontend source.

Incident list uses server-side severity/status/service filters plus 20-row pagination. Service search is case-insensitive literal substring matching; % and _ are literal characters. Keep unfiltered API pagination backward compatible. List polls every ten seconds; selected incident and diagnosis poll every five seconds with stale-response protection. Incident detail URLs use ?incident=UUID. Do not fetch all rows just to filter in the browser.

Render untrusted incident/evidence/model text as escaped React text, never raw HTML. Retrieval-only displays original excerpts with an explicit no-language-model label and no generated action sections. GENERATED displays cited causes/investigation/remediation with human-review guidance. Similarity is relevance, never confidence. Legacy diagnoses are explicitly labeled. No remediation execution controls.

Build and unit tests: docker compose build frontend (npm ci, seven Node test cases, strict typecheck, Vite production build). Optional host: cd frontend && npm ci && npm test && npm run build. Start: docker compose up -d --build --wait frontend. Browser E2E: bash scripts/test-dashboard.sh after API/publisher/worker and dependencies are running; browser tooling is isolated in infra/browser, not a runtime dependency. Tests retain synthetic incidents and screenshots under ignored .incidentiq-backups/dashboard. Report UI-only generated/error fixtures separately from actual model inference. See docs/dashboard-verification.md.

## Local CPU Ollama verification and safety limits

The optional compose.ollama.yaml override uses private Docker DNS ollama:11434 and a separate ollama_data volume; it exposes no host port. Base Compose/.env.example remain provider none, and the verification helper restores the base worker in finally. No silent per-event downgrade on model failure: retries/quarantine and offset safety remain intact. Never delete model or application volumes without authorization.

This x86-64 machine has AVX2/FMA/F16C, 14 logical CPUs and 7.2 GiB Docker/WSL RAM; Intel Graphics is not exposed to containers. The verified sample uses qwen3:0.6b Q4_K_M (523 MB); do not choose a larger model without evaluating available resources. The runtime is pinned Ollama 0.6.8: hash-verified official executable layer plus matching upstream AVX2 CPU libraries built locally. Source/binary fetches have size limits and SHA-256 checks. Do not replace this with an automatic multi-GB GPU image pull. Keep CPU build concurrency at two and runtime at four CPUs/2500 MiB.

Ollama requests use 8192 context tokens, max 512 output tokens, four threads and the existing 1–30 second timeout. The request grammar restricts one cited item per category; the public/storage schema remains compatible with earlier multi-item results. Prompt evidence omits unnecessary chunk IDs/scores; all five full snapshots remain in PostgreSQL. Log successful generation duration only, never incident/evidence/model payloads. Citation checks cannot prove semantic correctness; human review remains mandatory.

Setup: docker compose -f compose.yaml -f compose.ollama.yaml build ollama worker; start only ollama with --no-deps --wait; explicitly exec ollama ollama pull qwen3:0.6b once. Runtime/worker never pull models automatically. Build optional browser tooling from infra/browser, then python3 scripts/verify-local-ollama.py from the base retrieval-only configuration. It runs three real React-to-generated-diagnosis cases, actual adversarial model-output rejection, missing-model and one-second-timeout quarantine checks. It retains synthetic evidence under ignored .incidentiq-backups/ollama-verification and restores none even on failure. The unsupported-output test deliberately constrains an actual model to emit an invalid source; it is not a naturally occurring production hallucination or a mocked response.

After verification, run the existing retrieval-only RAG and dashboard checks to prove default mode remains working. Report actual inference and end-to-end latency separately. Never execute generated suggestions. See docs/ollama-verification.md for executed commands and remaining quality limits.

A real initial answer inverted kafka-lag.md and advised restoring offsets forward. The worker now rejects forward-offset references in generated investigation/remediation, including benign prohibitions conservatively. Do not remove this guard without an equivalent verified policy. Model text remains untrusted, often shallow or imprecise; exact citations do not prove factual correctness. Prior unsafe synthetic trial diagnosis e7716ad9-f31a-4bae-aad5-ebc1efa5206a is retained unchanged as evidence and must not be treated as operational advice.

## Bounded local performance benchmarks

Use python3 scripts/benchmark.py run after the normal platform/images are ready and grafana/k6:1.3.0 is pulled. No host k6/Java/Maven/new Python dependencies. Harness requires at least 2.9 GB available RAM. Separate incidentiq-bench project, owned incidentiq_bench_<run-id> database on the existing PostgreSQL server, separate single-node Kafka broker/topic/group, prefixed service names on the existing network. Never point benchmark writes at the normal database/topic. No production application source/config changes are needed. PostgreSQL stays published at 55432; temporary benchmark API uses localhost:18080.

Limits are fixed in benchmarks/api.js and benchmarks/compose.yaml: 5s/2-VU warmup, 20s/4-VU reads, 40 creates/2 VUs/max20s; separate 60-event batch/max120s observer after 64 real warm pipeline events. API/worker/publisher/broker quotas are recorded; do not quietly increase bounds or mix provider modes. Retrieval-only is forced. Ollama performance must have a separate opt-in methodology/result set and never be mixed with this baseline.

Results under docs/benchmarks/runs are intentionally tracked measurement artifacts (not build output). Include conditions/source hashes, raw k6 summaries, exact async samples, completion markers and honest limitations. Never write resolved Compose configuration, credentials, full envs, raw application payloads or DB dumps there. Temporary logs/fixtures/active lock stay in ignored .incidentiq-backups/benchmarks. Final results are not saturation/capacity/SLO claims; read/write phases include think time. Async latency is broker LogAppendTime to first visible committed diagnosis, including observer delay; do not misuse transaction-start now() timestamps as commit times.

Runner removes only temporary benchmark containers without --volumes and retains isolated databases. Kafka image ancillary anonymous volumes are retained too; never prune volumes to clean a run. Explicit optional cleanup: python3 scripts/benchmark.py cleanup EXACT_RUN_ID. It validates a strict ID and database ownership marker, refuses active connections and never force-drops. Tests: python3 -m unittest discover -s benchmarks -p 'test_*.py' -v (statistics and cleanup safety). Existing Java/Python/frontend/browser regressions must still pass before publishing. See docs/benchmarks/README.md and RESULTS.md for reproduction and actual measurements.

## Private distributed fault verification

Run `python3 -m unittest discover -s faults -p 'test_*.py' -v` and `python3 scripts/faults.py run`. Requires existing API/worker images and at least 3 GB available RAM. The run-specific Docker project has a private network, separate PostgreSQL container/database and Kafka broker/topic/group; API binds localhost:18081. Never inject failures into normal services or use normal data/topics. Preserve host PostgreSQL port 55432 and every existing volume.

`faults/worker_adapter.py` is test-only, mounted around actual processing/offset boundaries, not copied into runtime images. Only the private fixture database changes the fixed-topic outbox constraint and installs routing/publication gates. Never alter applied migrations for testing. Real Kafka membership expiry uses a pinned kafka-python private heartbeat seam with 6000/1000ms session/heartbeat settings; normal worker settings stay unchanged. Commit failures must fail closed, then replay through durable deduplication after restart. Do not suppress UnknownMemberIdError or claim exactly-once delivery.

Results/conditions/source hashes under docs/faults/runs are intentional tracked measurement artifacts. Logs, random credential environments and gates are private/ignored; never save resolved Compose config or environment dumps. The runner stops only its own containers, retaining all containers and volumes for review. No volume deletion/pruning. See docs/faults/README.md and RESULTS.md for actual measurements, failed harness attempts, recovery clock definitions and single-host/retrieval-only limitations.

Automatic-detection regression observers must match both fingerprint and current startsAt (API truncates to microseconds). A historical resolved occurrence with the same fingerprint is not evidence that the new firing webhook was processed. Observer regression: `python3 -m unittest discover -s scripts -p 'test_alert_smoke.py' -v`; rerun the real smoke test after observer changes.

## Isolated local Kubernetes

Kustomize: infra/kubernetes/base and overlays/local; namespace incidentiq-local in dedicated kind-incidentiq-dev context. Read docs/kubernetes/README.md before deployment. `python3 scripts/kubernetes-preflight.py` requires 6 GiB available RAM; if insufficient, validate only and explicitly report runtime unverified. Never stop Compose to bypass the gate, connect to Compose data, mount host Docker volumes, delete PVCs/clusters/volumes or deploy cloud resources. PostgreSQL host port 55432 remains reserved for Compose.

Validate: `./scripts/validate-kubernetes.sh` (kubectl render, checksum-verified kubeconform v0.6.7/Kubernetes 1.35 schemas, Dockerized cross-resource checks and local image inspection). Negative tests: Docker worker image, unittest discover -s /repo/infra/kubernetes/tests -v with repo mounted at /repo. Never claim schema validation is a real Kubernetes deployment. Current client kubectl 1.36.1/Kustomize 5.8.1.

Only API owns Flyway; publisher disables it. Worker init gates verify migrations/current full corpus and Kafka topic before consuming. runbooks/kustomization.yaml references original Markdown files; keep it synchronized when adding/removing runbooks. Secret database-credentials is generated outside tracked manifests and preserved for retained PostgreSQL claims. StatefulSets retain dedicated claims, but deleting a kind cluster can still lose local data. Deployment helper guards memory/named local context and never deletes storage. Kubernetes smoke helper is opt-in, synthetic, retrieval-only and has not been executed on the current resource-constrained host.
