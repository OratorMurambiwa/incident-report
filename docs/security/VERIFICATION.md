# Actual Step 8D verification

Executed locally on 2026-11-08 UTC (2026-11-07 America/Chicago), from baseline commit `3fc8ac8dfe85abd84cbba91550afa384cf8c4331` plus the reviewed working-tree security changes. Runtime image IDs and tested source hashes are recorded separately; the baseline commit alone does not identify these uncommitted candidate builds.

Host: Intel Core Ultra 5 225U, 14 logical CPUs, approximately 7.2 GiB WSL RAM; CPU-only MiniLM, local Docker. Major application/integration suites run serially. Static scans/checks can overlap bounded private-container startup; measured recovery timings are local observations, not controlled benchmarks. No GPU, hosted AI, cloud credentials, Azure activity or image publication.

## Completed checks

| Command / workflow | Actual outcome |
|---|---|
| `ci/test.sh java` | **64 JUnit**, zero failures/errors/skips; real fresh PostgreSQL/Flyway integration; Maven BUILD SUCCESS, 1:07 observed Maven duration. Includes the original 62 tests and two new codec round-trip tests. |
| `ci/test.sh python` | Fresh private DB initialized by the existing ten Java PostgreSQL tests; ten runbooks/60 chunks ingested; **77 pytest passed in 12.99s**, zero skipped; real MiniLM retrieval/DB tests (including database, Kafka, memory and authentication relevance) and mocked LLM/error tests; `pip check`: No broken requirements found. |
| `ci/test.sh frontend` | **Seven Node tests**, TypeScript test compilation, strict production TypeScript check and Vite build passed. Docker image build repeats npm tests/build. |
| `docker build` API/worker/frontend candidates | All succeeded; worker build's DB-independent subset: 59 passed/18 skipped. This subset is not a substitute for the full 77 real-DB tests above. API's ordinary build skips DB cases; full 64-test DB run is separate. |
| `security/scan.sh before`, `security/scan.sh after` | Three preserved baseline and three final images scanned with identical final options, Trivy 0.69.3 and frozen DBs; no suppression. CH 144 → 50. Streaming SHA256 of all four DB files unchanged. |
| `security/triage.py --cache ...` | All 144 original CH rows reviewed, duplicate groups retained, zero new final CH rows; fixes/removals checked against package inventory. |
| Frozen-snapshot frontend lockfile scan | Dev dependencies included; node_modules/dist/test-build skipped to inspect the lock source; **no findings detected**. Separate from nginx runtime scan. |
| `ci/security.py` on all three candidates | Source credential-pattern, baked credential-field and API/worker nonroot checks passed. Pattern checks are not a complete secret guarantee; nginx master retains its existing root startup model. |
| Maven `dependency:tree -Dscope=runtime`; worker `pip inspect` | Actual resolved runtime graph and installed dependency metadata saved in docs/security; no broken requirements. |
| Offline MiniLM old/new parity | Five queries ×384 dimensions, model weights identical; min cosine 0.9999999999998836, max absolute difference 8.475e-8; no runtime model downloads. |
| `docker compose config --quiet` | Passed; Compose definitions and applied migrations unchanged. |
| `scripts/verify-api.py` | **12 real HTTP checks**, including validation and missing records. Synthetic new incident retained. |
| `scripts/verify-infra.sh` | PostgreSQL TCP connectivity, pgvector 0.8.7/vector arithmetic, Kafka real produce/consume with a unique smoke topic passed. |
| `scripts/verify-event-flow.py` | HTTP → incident/outbox → Kafka contract → worker; one durable receipt, five snapshots; duplicate preserves outcome, malformed bytes quarantined before offset advancement. |
| `scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY` | Stored diagnosis returned HTTP 200, provider none, status RECEIVED, five evidence chunks and valid runbook sources. |
| `scripts/verify-monitoring.py` | API and worker Prometheus targets UP; actual success and quarantined-failure metrics; **16 Grafana panels** queried through the real datasource API. |
| `scripts/test-dashboard.sh` | **14 real browser checks**, including nginx proxy, manual submission → Kafka/RAG → displayed retrieval-only diagnosis, filters, pagination, keyboard focus, safe text rendering, loading/error states and responsive layout; no unexpected browser errors. |
| `scripts/smoke-auto-detection.py --skip-build` | Real HTTP 500, p95 latency and worker outage alerts → webhook → outbox/Kafka → stored diagnoses, repeats deduplicated, resolved notifications close incidents. Independent Kafka observer matched all three IDs; zero internal recursive incidents. Default simulation endpoints restored to 404. |
| `ci/infra.sh` | Terraform fmt/init -backend=false/validate; **55 unit/helper tests** (10 HCL, 9 Kubernetes, 10 pipeline, 8 fault contracts, 8 benchmark helpers, 3 alert observer, 7 new security-comparison tests). Local 17 and both Azure 19-resource schema checks passed without errors/skips. Static-only: no Kubernetes deployment or Azure access. |

The Python run has one FutureWarning: sentence-transformers renamed `get_sentence_embedding_dimension` to `get_embedding_dimension`. The compatibility alias works and all tests passed; it remains a future maintenance item, not a hidden test failure. No warning filter was added.

## Corrections during candidate verification

- After fault recovery passed, a long-lived WSL working directory became unresolvable and the first Ollama verifier invocation failed during Python imports (`FileNotFoundError`) before any model check. Rerunning the absolute script from `/tmp` avoids stale relative import paths; this failed invocation is not counted as a model test.
- New public image pulls initially failed through the global Docker credential helper. Retrying with the existing isolated, public-only CI Docker config succeeded; no cloud credential was used.
- An early resolver experiment tried uninstalling setuptools to remove its vulnerable embedded helpers. Torch requires it on Python 3.12; the final image keeps explicit patched setuptools 84.2.1 and verifies both its dependency requirement and embedded jaraco.context/wheel versions. The lock was regenerated through actual successful pip resolution/freeze, and the final images pass pip check. No broken resolver attempt is counted as passing.
- An environment probe mistakenly requested a Python entrypoint from the Java image and returned 127. Corrected probes executed `java -version` (21.0.13+9) and `nginx -v` (1.28.3). This was not an application test failure.
- The first slim frontend candidate still had five high nginx OS findings: CVE-2026-42055, 42533, 49975, 60005 and 9256. Its pinned `/etc/apk/world` revision prevented generic apk upgrade. Explicit `nginx=1.28.3-r7` clears them under the same DB; no advisory was ignored.
- Installing that distribution package overwrote global nginx config, causing a **real unhealthy container** (`server directive is not allowed here`). The Dockerfile now preserves the original compatible global config, tests `nginx -t` at build time, and the rebuilt candidate passed readiness plus all 14 browser/proxy tests. Failed candidates are not counted as successful deployment checks. PostgreSQL/Kafka were not recreated to fix this.

## Isolated recovery and actual Ollama

`python3 scripts/faults.py run` passed all **eight real-container scenarios** in its own project/database/topic. [Conditions](../faults/runs/20261108t015220z_fde9792c/conditions.json), [complete results](../faults/runs/20261108t015220z_fde9792c/results.json). Ten valid events produced ten diagnoses and 50 immutable snapshots; seven duplicate handlings, one byte-preserved quarantined poison, committed/end offsets **15/15**, and zero observed data loss in this sample. Private containers were stopped; their separate volumes and normal data were retained.

| Scenario | Observed elapsed seconds |
|---|---:|
| crash_before_db_commit | 34.514 |
| crash_after_db_commit | 35.825 |
| duplicates_and_rebalance | 50.129 |
| broker_outage | 81.93 |
| database_outage | 22.216 |
| publisher_crash_after_kafka_ack | 111.055 |
| unknown_member_id_recovery | 27.525 |
| poison_retained | 12.478 |

Durations use each existing scenario's clock boundaries and include container restart/rejoin/backoff where applicable. They are not comparable controlled SLO benchmarks. Publisher recovery deliberately caused Kafka replay (at least two copies), with the original diagnosis/snapshots preserved. **No exactly-once Kafka delivery is claimed.**

The forced membership-expiry test under kafka-python **2.3.2** found real `UnknownMemberIdError` and `CommitFailedError`, stopped the worker after the failed offset commit, then restarted/rejoined/re-read and deduplicated without rewriting the committed result. This verifies the intended failure behavior; it does not prove the original naturally occurring benchmark error's cause is resolved. The private heartbeat seam was unchanged. Its old 2.2.15 comment was subsequently clarified to include the now-tested 2.3.2; the conditions file retains the original start-of-run source hash, and that annotation changes no runtime behavior. Eight helper contract tests passed again after the comment change.

`python3 /absolute/path/scripts/verify-local-ollama.py` then passed its real model/transport/guard checks using the cached **qwen3:0.6b**, **Ollama 0.6.8**, CPU only. No new model pull, hosted API or remediation execution. [Measured report](ollama-verification.json), [actual selected stored fields](ollama-samples.json).

- Database and memory browser submissions produced real GENERATED/DIAGNOSED rows, each with one outbox event, one receipt, one diagnosis and five snapshots; valid citations were `database-failures.md` and `memory-exhaustion.md`. Browser end-to-end times: **53.159 s** and **30.226 s**. Accepted Ollama calls logged **16.889 s** and **28.668 s**. The database case first experienced one ModelUnavailable timeout, then succeeded through the existing retry path; its 53.159 s includes that delay.
- Kafka model output was **rejected**, not a successful diagnosis: three InvalidDiagnosis attempts, durable FAILED/quarantine, no receipt/diagnosis/snapshots, then offset commit. Its three actual model calls logged 24.909/23.368/24.134 s. This known small-model/guard limitation remains visible; no guard was relaxed to manufacture a passing answer.
- Two actual adversarial model responses (invented citation and forward-offset advice) were rejected, with zero database writes (18.818/14.034 s).
- Real unavailable-model and one-second-timeout incidents each reached durable ModelUnavailable quarantine after three attempts, with no partial result and offset advancement only afterward (125→126 and 126→127).
- Base worker restored to **LLM_PROVIDER=none**. A fresh HTTP → outbox/Kafka → RAG → stored diagnosis check passed again, including replay preservation; optional Ollama stopped with its volume retained. A final stronger offline parity rerun asserted identical model name/revision/weight SHA as well as embedding parity. Existing corpus ingestion returned **files=10, skipped=10, changed=0, chunks_written=0**.

These checks verify transport, persistence, schema/citations and narrow guard behavior, not general semantic entailment. The stored database remediation is general rather than a demonstrated root-cause fix; human review remains necessary. `semantic_grounding_verified=false` is preserved in the measured report. No suggestion was executed.

Final health: eight health-checked normal services healthy; publisher running (no healthcheck configured). Prometheus's API, worker, Alertmanager and self-scrape targets UP; all rules healthy. Grafana database health OK; production simulation endpoints return 404. PostgreSQL still binds 127.0.0.1:55432. All six original volume creation timestamps match; final conditions are recorded in verification.json.



## Data preservation and limitations

The five normal Compose-managed volumes and the separately retained Ollama volume have their original creation timestamps (see verification.json). PostgreSQL/Kafka storage was not recreated, no volumes were deleted/pruned, no historical backfill/rewrite was performed and no applied migrations changed. Private fault-test volumes are retained separately. Real HTTP/browser/monitoring tests add synthetic records and poison fixtures with durable quarantine; they do not delete old data.

This is regression and inventory evidence, not exploit testing or certification of every model answer. Runtime checks do not prove general semantic grounding. All remaining CH findings and their deferral reasons are in [README](README.md) and the full ledger; medium/low findings are retained in totals and locally ignored raw reports. Other services, build-stage images, compiler tools and future cloud deployments are not covered by this runtime scan. See the image/database manifests to distinguish this verified snapshot from future mutable-tag rebuilds.
