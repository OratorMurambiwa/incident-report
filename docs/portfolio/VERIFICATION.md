# Step 9 portfolio verification

Documentation work on November 9, 2026 (America/Chicago; capture/check timestamps are November 10 UTC), starting from security commit `a4d5025a91d09bd6806c97ca36c95d49d4d83f65`. No application feature, dependency pin, migration, Compose configuration or infrastructure behavior was changed. [Portfolio overview](../../README.md) · [Structured checks](verification.json).

## Evidence review and corrections

Reviewed AGENTS.md, the former README, every milestone verification report, benchmark/fault result reports and their structured run/completion evidence. The failed calibration/fault attempts remain incomplete historical records; only completed runs supply README figures. A reviewed-report hash manifest is recorded in verification.json.

- Replaced the accumulated scaffold/milestone README with the implemented platform, actual screenshot, Mermaid architecture, a Docker-first setup, demo, measured results and evidence links.
- Corrected outdated architecture language: frontend and alerts are implemented, Flyway V6 owns alert occurrence state, and incident.created is the active pipeline. incidents.raw/incidents.analyzed remain reserved/legacy topics.
- Historical reports keep their original measurements and failures; their old navigation banners now point readers to the current overview/latest application regression. Statements that Ollama/frontend were untested describe those earlier milestones, not the current platform.
- Performance numbers explicitly identify the earlier f8912f0 baseline, resource bounds and retrieval-only mode. Current dependencies were not rebenchmarked. Fault figures identify the completed later security-regression run and do not imply a uniform recovery SLA or exactly-once delivery.
- Retained the measured **50 critical/high occurrences**, scanner/database date, duplicate/CVE distinction and deferred risks. No new vulnerability scan or security certification is claimed.
- Kubernetes and Terraform remain statically validated; Azure DevOps organization execution, image publishing and deployment remain unverified. Actual CPU Ollama results remain separate from retrieval-only and mocked/UI fixture coverage; every AI recommendation requires human review.

## Actual screenshot

[Published screenshot](../images/dashboard.png), [capture provenance](../images/capture.json), [capture helper](capture-dashboard.py).

Playwright/Chromium in the existing optional incidentiq-browser image submitted one new synthetic incident through the real React form. The API returned HTTP 201; the actual outbox/Kafka/worker/MiniLM/pgvector pipeline stored a RETRIEVAL_ONLY diagnosis; the browser fetched it with HTTP 200, provider none and five evidence chunks. The screenshot shows only that incident's detail view, public runbook text and its synthetic service label. The UUID was masked at browser capture; there was no DOM replacement, network response interception, synthetic image generation or later pixel editing. No existing incident list, private payload, credential, cookie or browser session was published. The image was visually inspected before staging.

Capture size is 1360 ×1724 pixels; SHA256 is stored in capture.json. The incident is retained as a labeled synthetic record; no prior record was edited/deleted. An initial helper launch was blocked by the workspace's read-only mapping and consequently had no Python script to execute; it failed before submitting an incident. Writing the helper through the authorized workspace path and rerunning succeeded. No failed invocation is counted as a successful capture.

Reproduce only when the existing Compose services are running with provider none (this creates a new synthetic incident):

```bash
docker build -t incidentiq-browser:local infra/browser
docker run --rm --memory 768m --cpus 1 --network incidentiq_default --ipc=host \
  --mount type=bind,src="$PWD/docs/portfolio/capture-dashboard.py",dst=/capture.py,readonly \
  --mount type=bind,src="$PWD/docs/images",dst=/output \
  --entrypoint python incidentiq-browser:local /capture.py
```

If COMPOSE_PROJECT_NAME differs from the default, use its own Docker network. Never substitute a private incident for the synthetic capture or publish raw test screenshots/traces.

## Documentation checks

`python3 docs/portfolio/check-readme.py` checks relative links/anchors, PNG header/dimensions/hash, capture provenance and README values against completed benchmark/fault/security JSON. Its result is recorded in verification.json; it does not infer deployment or fresh benchmark success from prose. Local HTTP links are checked separately against the running services.

The single README Mermaid block parsed and rendered in Chromium **offline** using **mermaid 11.12.0**; 13 nodes and all requested component labels were verified by check-diagram.py. Tools were installed in /tmp, without modifying application manifests or dependency locks. This is local rendering, not a claim of GitHub server-side preview execution. Reproduction uses the optional browser image with the pinned package's dist directory mounted at /mermaid, README at /README.md and check-diagram.py at /check.py, then runs python /check.py with --network none.

## Setup and runtime boundaries

The README's env-copy guard preserves an existing .env. Base/observability Compose configuration and the three image build commands are checked; startup uses a Docker Compose dry run rather than recreating healthy services. This verifies the plan against the current environment, **not a new empty-volume installation**. No stop/down/volume cleanup or dev simulator is run for this documentation milestone.

Fresh runtime verification includes the actual capture flow and the existing dashboard regression; completed build/browser/link/health results and preservation checks are recorded in verification.json. The full Java/Python/fault/Ollama suites and k6 benchmark were not deliberately rerun for this prose edit; latest historical full counts remain dated and linked. Database-specific image-build skips are not represented as complete database integration suites.

Build verification artifacts are kept separately and the working application image tags are restored from the unchanged running containers. No service recreation or deployment is needed to publish documentation. Original six data/model volumes, worker provider none, production simulation-disabled behavior and PostgreSQL host port 55432 are checked at completion. No cloud credentials, cloud resources, paid services or optional Ollama model pulls were used. Unchanged Dockerfiles fetched public build dependencies and the pinned MiniLM model as needed.

## Completed checks in this milestone

| Check | Actual result |
|---|---|
| Relative Markdown links/anchors, exact GitHub path casing | 92 targets across README, architecture and milestone reports; all valid |
| README localhost addresses | All five returned HTTP 200 |
| Mermaid diagram | Pinned 11.12.0 parse + offline Chromium render passed, 13 nodes |
| Screenshot | Actual UI submission HTTP 201, stored diagnosis HTTP 200, five chunks, no browser errors; PNG hash/dimensions verified and pixels inspected |
| Existing browser regression | 14 checks passed, zero JavaScript errors; actual retrieval-only mode; generated-mode UI fixture remains explicitly separate |
| README Docker builds | API, worker and frontend builds succeeded; worker freshly ran 59 tests with 18 DB/model skips. Other cached layers are not claimed as freshly executed suites |
| Startup / configuration | Base/observability and Ollama override valid; startup dry run passed; no clean-volume startup attempted |
| Preservation | All 197 prior application/infrastructure/test source hashes match; nine running container IDs/images and six volume creation times unchanged; working image tags restored; .env unchanged; provider none; simulation endpoints 404; PostgreSQL 55432 retained |

The README's full-suite counts, security totals, performance and fault timings remain explicitly historical. No new benchmark, Trivy scan, real Ollama run, cloud deployment or Azure DevOps organization execution is claimed for Step 9. No model suggestion was executed.
