> Historical milestone snapshot: capability/version statements and counts below describe that run. See the [current overview](../README.md) and [latest application/security regression](security/VERIFICATION.md) for subsequent implementation and verification.

# Step 5A monitoring verification — 2026-11-05 (America/Chicago)

## Implemented and repaired

Read AGENTS.md and preserved the existing RAG implementation and pending monitoring work. Fixed both SimpleMeterRegistry test blocks to use a normal variable and explicit close() in finally, as supported by the installed Micrometer version. No dependency version changes or database migrations were needed.

Actuator/Micrometer supplies HTTP request counters, status/error labels, JVM metrics and configured histogram buckets for aggregatable p95 estimates. Added incident gauges reading PostgreSQL totals and six enum statuses. Database failures return NaN instead of false zero counts. The HTTP URI label is templated and capped at 32 values.

Worker instrumentation adds processing-duration and RAG-retrieval histograms plus outcome/mode counters. Success increments after PostgreSQL commit, not on retries/duplicates. Valid workflow failures increment after durable quarantine; malformed and conflicting events remain separate quarantine records. Processing includes retry delays and offset acknowledgement; retrieval includes embedding and vector search attempts. Labels never include incident/event IDs, services, source filenames, model names or exception text.

Prometheus scrapes api:8080/actuator/prometheus and worker:8001/metrics every five seconds through Docker networking. Grafana provisions the existing Prometheus datasource and a 16-panel dashboard. Persistent prometheus_data/grafana_data volumes and health checks are configured. PostgreSQL remains on host port 55432. Existing PostgreSQL/Kafka volumes were not deleted or replaced.

## Automated tests actually executed

`./scripts/test-api.sh`: exit 0, including PostgreSQL integration tests:

```text
Tests run: 36, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

This preserves all 34 prior cases and adds two gauge tests: live database count reads and missing-data behavior on database unavailability.

`./scripts/test-worker.sh`: exit 0, including real local embedding/PostgreSQL integration tests:

```text
72 passed in 12.83s
```

This preserves all 68 prior cases and adds processing success/failure timing, failed retrieval timing without a successful diagnosis, and bounded-label tests. Existing duplicate/unavailable-model database cases additionally assert success/failure counters are incremented once at the correct durable boundary.

Image builds also ran their database-independent tests; database/model-dependent cases are deliberately skipped inside ordinary builds and ran in the complete suites above. Python syntax checks and git diff --check passed.

## Build, startup and scrape verification

`docker compose --profile observability config --quiet`: exit 0.

`docker compose --profile observability up -d --build --wait`: exit 0. API, worker, PostgreSQL, Kafka, Prometheus and Grafana are healthy; publisher is running; kafka-init and runbook-ingest exited 0. No Docker volume deletion was used.

`python3 scripts/verify-monitoring.py`: exit 0 after fixing a verification-helper bug (urllib Request uses get_method(), not a method attribute). Its expected async diagnosis polling now accepts 404 until the diagnosis becomes available. This was a verifier failure, not an application test-suite failure.

Actual targets:

```text
incidentiq-api     UP  http://api:8080/actuator/prometheus
incidentiq-worker  UP  http://worker:8001/metrics
prometheus         UP  http://localhost:9090/metrics
```

The verifier generated real HTTP traffic with validation/not-found errors, a real incident through Kafka/RAG, and a deliberately orphaned synthetic event. The latter exercised actual durable failure/quarantine metrics with ForeignKeyViolation; it was not an Ollama/model failure and could not change an existing incident. Its retained record is incident.created partition 0 offset 15, eventId 143e327c-7da5-42c9-b48c-5ddfdd0a0886. Synthetic success incident c120162f-9df2-4ef7-bb38-137d3558bbd3 received a RETRIEVAL_ONLY diagnosis.

Observed sample values (later traffic naturally changed counters/gauges):

| Metric | Actual sampled value |
|---|---:|
| http_requests | 43.0 |
| http_p95_seconds | 0.011945869085051679 |
| http_client_errors | 16.0 |
| jvm_memory_bytes | 169954856.0 |
| incident_total | 9.0 |
| worker_success | 2.0 |
| worker_failure | 1.0 |
| worker_processing_p95_seconds | 4.625 |
| rag_retrieval_p95_seconds | 0.02425 |


The incident gauge matched PostgreSQL's count at sampling time (9). HTTP URI tags were only /actuator/health, /actuator/prometheus, /api/incidents, /api/incidents/{id} and /api/incidents/{id}/diagnosis. No raw UUID appeared in URI labels. Worker outcome labels were confined to outcome and mode, plus Prometheus job/instance metadata.

## Grafana data and actual browser rendering

Datasource health returned OK. The dashboard API returned the provisioned incidentiq-overview definition. Every one of its 16 panels was queried through Grafana /api/ds/query and returned actual finite numeric Prometheus data, including zero-valued server-error/generated-mode series where no such event occurred.

A real Chromium browser inside the optional Playwright verification container logged in, loaded the dashboard and produced:

```json
{
  "dashboard": "incidentiq-overview",
  "chart_canvases": 7,
  "no_data_messages": 0,
  "page_errors": [],
  "screenshot": "monitoring-dashboard.png"
}
```

The screenshot was visually inspected: API and worker UP, real request/latency/error curves, JVM memory, worker processing/retrieval curves, status gauges and outcome/count panels were visible. At capture time the database gauge was 11, successful diagnoses since worker restart were 4, failed workflows 1 and timed records 6, reflecting additional regression traffic.

The initial browser attempt exposed an invalid inherited browser language tag (en-US@posix), which prevented Grafana frontend startup. Explicit locale=en-US in the capture context fixed it; no Grafana application workaround or weakened browser security was required. Screenshots and verification JSON remain under ignored .incidentiq-backups/monitoring and are not committed. No cookies or credentials are saved there.

## API, Kafka, RAG and data preservation

`python3 scripts/verify-rag-flow.py`: exit 0, actual output:

```text
POST /api/incidents: HTTP 201, incidentId=7b8b034b-8ba3-40d3-b246-f262801ea933, status=PENDING
GET diagnosis: HTTP 200, mode=RETRIEVAL_ONLY, provider=none, incident status=RECEIVED
Diagnosis id=9199b820-3428-44c0-ad86-9005df85ce6d, eventId=c7c78cba-99d6-4193-9407-28e36e0389f9, evidence=5, citations=['database-failures.md']
Outbox acknowledged; one receipt, five snapshots, one diagnosis; duplicate offset=17, committed=18
Diagnosis and evidence unchanged on duplicate; real end-to-end verification passed.
```

`python3 scripts/verify-api.py`: exit 0; all 12 HTTP checks passed. `./scripts/verify-infra.sh`: exit 0; PostgreSQL connectivity, pgvector 0.8.7, both legacy topics and an isolated Kafka produce/consume round trip passed (`Consumed: incidentiq-smoke-ok`); the temporary test topic was deleted.

PostgreSQL and Kafka volume creation timestamps remain 2026-11-06T00:00:34Z, matching their pre-verification timestamps. The new monitoring volumes were created at 2026-11-06T01:22:39Z. Synthetic incidents/diagnoses/quarantine evidence from checks are retained; no original application rows or snapshots were removed. Counters are per-process; persisted incident gauges and historical monitoring storage have separate durability semantics.

RAG validation here used the actual local embedding model with LLM_PROVIDER=none. Actual Ollama generation remains untested; its client behavior continues to be covered by mocks. Monitoring has no remaining blocker.

## Accessible URLs

- Dashboard: http://localhost:3001/d/incidentiq-overview
- Grafana: http://localhost:3001 (admin; use password from ignored .env)
- Prometheus: http://localhost:9090
- Targets: http://localhost:9090/targets
- API metrics: http://localhost:8080/actuator/prometheus

## Repeating browser verification

scripts/capture-monitoring.py is an optional verification helper, not an application dependency. It runs inside an image built from mcr.microsoft.com/playwright/python:v1.55.0-noble with playwright==1.55.0. Pass GRAFANA_USER/GRAFANA_PASSWORD through environment variables, mount that script at /capture.py, and mount an ignored evidence directory at /evidence on the project's Docker network. Invoke python /capture.py. The helper obtains a transient session through /login, uses en-US locale and America/Chicago timezone, verifies chart rendering and saves only screenshot/nonsensitive status JSON. Never put credentials in tracked files or command arguments.

## Publication

The preceding RAG milestone is already preserved in commit [d82d561](https://github.com/OratorMurambiwa/incident-report/commit/d82d561d2a9164d8e1a8c9513ba3643526a911b6). This monitoring milestone is committed only after the successful checks above, with the requested message `feat: add Prometheus and Grafana observability`, the existing author identity and no co-author trailers. Staged files are reviewed for secrets/artifacts before a normal push; final commit SHA and remote verification are reported with completion.
