> Historical milestone snapshot: capability/version statements and counts below describe that run. See the [current overview](../README.md) and [latest application/security regression](security/VERIFICATION.md) for subsequent implementation and verification.

# Step 6 dashboard verification — 2026-11-06 (America/Chicago)

## Implementation

React 19.1.1 + strict TypeScript 5.8.3 and Vite 6.4.5. React/React DOM are the only runtime JavaScript dependencies. Docker uses Node 22.14.0 for npm ci, unit tests, typecheck and production build; nginx 1.28.0 serves the result on localhost:5173 with same-origin /api proxying to api:8080. nginx resolves Docker DNS periodically so API recreation does not require rebuilding frontend assets. Vite dev proxy supports optional host development.

Server-side severity/status/service filters compose with existing pagination. Service search is a case-insensitive literal substring (including literal % and _); empty filters preserve existing behavior. No database migrations or existing volume configuration changes.

The UI handles periodic list/detail refresh, stale asynchronous responses, bounded request timeouts, creation validation, errors, empty results and pending/failed diagnoses. Accessible native controls, associated labels, visible focus styles, skip navigation, focus on detail/form entry and expandable evidence support keyboard use. Small screens scroll the table within its container. React escapes all incident/model/runbook text; no raw HTML or command execution.

Retrieval-only evidence is explicitly labeled as using no language model, with no generated-action sections. GENERATED results display cited causes/investigation/remediation and human-review guidance. Legacy results are labeled separately. Similarity is relevance, not confidence. Monitoring links open local services in separate tabs.

## Automated checks actually executed

- `./scripts/test-api.sh`: **62 tests, failures 0, errors 0, skipped 0; BUILD SUCCESS**, including all existing tests and three real PostgreSQL filtering cases (combined filters, literal wildcard characters/pagination, invalid filters).
- `./scripts/test-worker.sh`: **73 passed in 75.69s**, including real MiniLM/database relevance and durable event-processing tests. Ingestion skipped all ten unchanged runbooks.
- `docker compose config --quiet`: successful.
- `docker compose build frontend api`: successful. Frontend ran **7 Node tests**, strict TypeScript checking and Vite production compilation. Generated JS: 200.57 kB / 63.36 kB gzip; CSS: 5.41 kB / 1.93 kB gzip.
- Real npm lock generation with Node container: successful. Initial scaffold Vite 6.3.5 audit reported one high vulnerability. Updated within Vite 6 to 6.4.5; final lock generation reported **0 vulnerabilities**. Compatibility checked against Vite 6 documentation and upstream security advisory: https://v6.vite.dev/guide/ and https://github.com/vitejs/vite/security/advisories/GHSA-rq7h-c2jc-7f22 .

The WSL Docker credential helper initially prevented new public image pulls. Using an empty temporary DOCKER_CONFIG for public pulls/build metadata resolved this without changing user credentials or project .env.

Browser and live regression results are recorded below. Build-time JUnit deliberately skips database tests; the complete 62-case test result above includes them against the isolated test database. Screenshots/evidence remain under ignored .incidentiq-backups/dashboard, never in Git.

## Real browser and container results

`DOCKER_CONFIG=/tmp/incidentiq-docker-public bash scripts/test-dashboard.sh`: **14 checks passed, zero browser JavaScript errors**. Uses pinned Playwright/Chromium in an isolated verification container on the Compose network. Source screenshots were visually inspected at desktop 1440px and mobile 390px widths.

Checks cover held-response loading state; real list; monitoring links; required fields and focus; manual creation HTTP 201 with escaped hostile markup; actual asynchronous diagnosis and five evidence chunks; combined severity/status/service filters; empty results; pagination; periodic discovery of a real externally created incident; simulated browser-only 503/retry recovery; generated-mode UI-only fixture; mobile/direct URL; and a real missing-record 404.

Real UI-created incident: `b5abd0ad-bbb1-40b5-9ff6-e9b438b08731`, service `ui-e2e-c4c25294`. Its diagnosis came from the existing outbox/Kafka/worker pipeline and was **RETRIEVAL_ONLY**. Expanded evidence showed actual database-failures.md excerpts and similarity scores. The generated-mode display was exercised only by substituting a browser response fixture, not by running Ollama. Actual Ollama generation remains untested.

Early browser attempts exposed unstable accessible names when validation messages/options were included in control labels. Corrected field/error associations and select names; the complete final suite then passed. A transient WSL working-directory error interrupted one existing verifier startup; rerunning from the canonical path passed. A browser attempt overlapped a frontend container replacement and lost its connection; the successful final run used stable containers with no replacement during verification.

Evidence: ignored `.incidentiq-backups/dashboard/verification.json`, `detail.png`, `mobile.png`. No test incidents or existing application records were deleted.

Live regression commands:

- `python3 scripts/verify-api.py`: all **12 HTTP checks passed**.
- `python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY`: HTTP 200 diagnosis, outbox acknowledged, one receipt/five snapshots/one diagnosis; duplicate delivery preserved diagnosis/evidence.
- `./scripts/verify-infra.sh`: PostgreSQL TCP, pgvector 0.8.7 and vector arithmetic passed; Kafka round trip consumed `incidentiq-smoke-ok`. Only its own disposable smoke topic was deleted.
- Final Prometheus targets: API, worker, Alertmanager and Prometheus all UP; zero active alerts. API/frontend/worker/PostgreSQL/Kafka/Prometheus/Grafana/Alertmanager healthy, publisher running.

Existing volume creation times remain unchanged: PostgreSQL/Kafka 2026-11-06T00:00:34Z; Prometheus/Grafana 2026-11-06T01:22:39Z; Alertmanager 2026-11-06T01:58:52Z. PostgreSQL remains on host **55432**, frontend on **5173**. No volumes were removed or recreated, no applied migrations changed, and all previous tests remain covered.

## Reproduction

```bash
./scripts/test-api.sh
./scripts/test-worker.sh
docker compose --profile observability config --quiet
docker compose --profile observability up -d --build --wait
bash scripts/test-dashboard.sh
```

Use an empty temporary DOCKER_CONFIG for public image builds only if the WSL credential helper fails; no credentials belong in the frontend or test artifacts. Host Node/Java/Maven/Python packages are unnecessary for the container build and browser suite.
