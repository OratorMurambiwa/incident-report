> Historical milestone snapshot: capability/version statements and counts below describe that run. See the [current overview](../README.md) and [latest application/security regression](security/VERIFICATION.md) for subsequent implementation and verification.

# Automatic detection verification — Step 5B

Executed locally on 2026-11-06 UTC (2026-11-05 America/Chicago). Docker Desktop through WSL; Java/Maven and Python dependencies run in containers. No remote model or paid service was used.

## Automated checks actually executed

- `./scripts/test-api.sh`: **59 tests, 0 failures, 0 errors, 0 skipped; BUILD SUCCESS**. Includes existing tests plus webhook validation, standard Alertmanager metadata, mixed firing/resolved notifications, persistent deduplication, concurrent delivery, outbox rollback, stale notifications, new occurrences and timestamp precision. Simulation tests cover dev opt-in, flag disabled, default disabled and production override safety.
- `./scripts/test-worker.sh`: **73 passed in 7.08s**. Existing retrieval/model/database and failure tests preserved; added resolution-before-processing regression.
- Base and development override `docker compose config --quiet`: successful.
- `amtool check-config` using `prom/alertmanager:v0.28.1`: SUCCESS, one receiver.
- `promtool check config` using `prom/prometheus:v3.5.0`: SUCCESS, three rules.
- `promtool test rules /etc/prometheus/alerts_test.yml`: SUCCESS. Five scenarios / six rule evaluations cover positive error/latency/availability alerts, recursion exclusions and insufficient error volume.

Reproduce configuration/rule checks:

```bash
docker compose config --quiet
docker compose -f compose.yaml -f compose.dev.yaml config --quiet
docker run --rm --entrypoint amtool -v "$PWD/infra/alertmanager/alertmanager.yml:/config.yml:ro" prom/alertmanager:v0.28.1 check-config /config.yml
docker run --rm --entrypoint promtool -v "$PWD/infra/prometheus:/etc/prometheus:ro" prom/prometheus:v3.5.0 check config /etc/prometheus/prometheus.yml
docker run --rm --entrypoint promtool -v "$PWD/infra/prometheus:/etc/prometheus:ro" prom/prometheus:v3.5.0 test rules /etc/prometheus/alerts_test.yml
```

## Real container smoke test

`python3 scripts/smoke-auto-detection.py` rebuilt/started application containers and monitoring, generated real HTTP requests, and stopped/restarted the actual worker. It did not manually submit webhook payloads or create incidents directly.

Observed chain: simulated failure or service outage → Prometheus firing rule → Alertmanager active alert → real HTTP webhook → committed incident/outbox → Kafka → worker receipt/retrieval/diagnosis → GET diagnosis HTTP 200 → resolved webhook/RESOLVED status.

| Real condition | Fingerprint | Stored incident |
| --- | --- | --- |
| Repeated HTTP 500 responses | f9f1ad978cc8cb34 | 93d6cc58-2a07-4cd3-b9f7-5c29152d1fa2 |
| 750ms HTTP latency | 0aeab1d847d33a9a | 117e51a3-83c1-4422-b6ed-84682295014e |
| Worker container stopped | 599bd47622a7dab9 | a3da05ab-62ca-434b-b5e7-063482653bb6 |

Each occurrence had exactly one published outbox event, one durable receipt, five retrieval snapshots and one diagnosis. An independent Kafka consumer matched all three outbox event IDs without changing application consumer offsets. Real repeated Alertmanager notifications for the error/latency fingerprints left the same incident, outbox, receipt and diagnosis unchanged. All three incidents resolved. Zero alert incidents referenced excluded internal routes. Evidence JSON is retained locally under ignored `.incidentiq-backups/automatic-detection/verification.json`.

Both simulator endpoints returned 404 before the smoke test and after its finally block restored the base API configuration. Production-profile exclusion was tested by JUnit. Simulated latency is bounded to 2000ms. The worker recovered healthy after the intentional outage.

Actual diagnosis mode was **RETRIEVAL_ONLY**, using local MiniLM embeddings and five real runbook chunks. This verifies the configured RAG pipeline and persistence, not live generative inference. Actual Ollama generation was not tested; mocked Ollama paths remain covered by Python tests.

## Existing functionality and final health

- `python3 scripts/verify-api.py`: all **12 HTTP checks passed**.
- `python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY`: HTTP 200 diagnosis, one receipt/five snapshots, outbox acknowledgement and unchanged diagnosis/evidence after duplicate delivery.
- `./scripts/verify-infra.sh`: PostgreSQL TCP connectivity, installed vector extension, vector distance arithmetic and real Kafka producer/consumer round trip (`Consumed: incidentiq-smoke-ok`). Only its own disposable smoke topic was deleted.
- `python3 scripts/verify-monitoring.py`: live API/worker scrape metrics and **16 Grafana panels verified through the real datasource query API**. It deliberately retains synthetic success/error/quarantine fixtures. No new browser screenshot was taken for Step 5B.
- Final Prometheus API: incidentiq-api, incidentiq-worker, incidentiq-alertmanager and prometheus targets all UP. All three alert rules health=ok, state=inactive; zero active alerts.
- API, worker, PostgreSQL, Kafka, Prometheus, Grafana and Alertmanager healthy; separate publisher running.

PostgreSQL host port remains **55432**. Existing PostgreSQL/Kafka volume creation timestamps remain 2026-11-06T00:00:34Z; existing Prometheus/Grafana volumes remain 2026-11-06T01:22:39Z. New alertmanager_data was created at 2026-11-06T01:58:52Z. No persistent volume was deleted or recreated.

URLs: API http://localhost:8080; Prometheus http://localhost:9090; Alertmanager http://localhost:9093; Grafana http://localhost:3001/d/incidentiq-overview. Grafana credentials remain in ignored .env.

## Scope and practical limits

Error/latency rules intentionally exclude actuator, incident and alert webhook paths to prevent feedback loops; these paths are not covered by those two alerts. Availability uses exporter reachability rather than dependency readiness. The single-host API/Alertmanager cannot receive/deliver its own outage notification while unavailable; recovery is required, so this is not an independent external watchdog. Local short evaluation/repeat intervals are demonstration settings.

Fingerprint history and resolved tombstones survive restarts. New alert occurrences create new incidents after resolution. Stale firing/resolved messages are ignored, and concurrent active notifications serialize in PostgreSQL. Webhook incident creation and outbox enqueue share one transaction; downstream delivery retains existing at-least-once/idempotent semantics. Alert metadata is untrusted input and never executed.
