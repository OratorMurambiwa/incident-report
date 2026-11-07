# Step 8A actual verification

Executed locally on 2026-11-07 against application commit a24e98188d2750824c1f6f58a192a066d40c0d7a. [Structured evidence, complete Docker image inventory and source hashes](verification.json). [Reproduce/deploy](README.md).

**Kubernetes deployment is not verified. No cluster was created and no Kubernetes incident smoke test was run.** This is the explicitly permitted manifest-validation path, not a successful cluster rollout.

## Resource decision

Initial inspection: WSL Intel Core Ultra 5 225U / 14 logical CPUs, MemTotal 7,751,802,880 bytes (~7.2 GiB), MemAvailable 4,031,352,832 bytes (~3.75 GiB); swap already in use. Existing Compose remained running. kubectl v1.36.1 with embedded Kustomize v5.8.1 was accessible, but kind/k3d were absent and kubectl had zero configured contexts. Available memory was below the conservative 6,442,450,944-byte gate. Steady main-container limits are 3008 MiB, plus up to 1024 MiB ingestion, control plane and headroom. This is a safety budget, not a measured deployment requirement.

The guarded `bash scripts/kubernetes-local.sh deploy` command was deliberately tested and exited 1 with:

```text
Insufficient headroom: validation only. Do not stop Compose or delete data to bypass this gate.
```

That refusal happened before kind/context access, Secret creation, image loading or apply. It is an expected guard test, not a failed Kubernetes rollout. No node image was pulled. The kindest/node:v1.35.0 multi-platform manifest reference was inspected successfully for future instructions only.

## Actual checks passed

| Command/check | Actual result |
| --- | --- |
| `kubectl kustomize infra/kubernetes/overlays/local` + kubeconform v0.6.7 `-strict -summary -kubernetes-version 1.35.0` | 17 resources valid; 0 invalid, errors or skipped |
| `kubectl kustomize infra/kubernetes/base` + same schema validator | 16 resources valid; 0 invalid, errors or skipped |
| `./scripts/validate-kubernetes.sh` | Seven workloads, five Services, four ConfigMaps/ten runbooks plus namespace; cross-resource checks passed; five image references exist locally |
| Docker worker `unittest discover -s /repo/infra/kubernetes/tests -v` | 9 tests passed; rejects host mounts, normal DB, bad Service ports, missing probes/maps, generative mode, publisher migrations and Kafka bootstrap DNS deadlock |
| Actual frontend container, Kubernetes nginx mount, `nginx -t` | Syntax successful; simulated api hostname supplied only for syntax resolution, no Kubernetes DNS/routing test claimed |
| Actual worker image, PYTHONPATH=/app, imports db/kafka.admin/model and compiles bootstrap | Passed without database/network connections |
| Existing Compose API probe paths | /actuator/health/liveness and /actuator/health both HTTP 200, UP |
| Existing publisher `/bin/sh -ec 'kill -0 1'` | Passed; only process presence, not delivery progress |
| Shell syntax/Python compilation and `git diff --check` | Passed |
| `docker compose config --quiet` | Valid; normal configuration unchanged |

kubeconform's downloaded Linux amd64 v0.6.7 archive matched the official release CHECKSUMS before extraction. Schema retrieval used public upstream Kubernetes JSON schemas. No API-server dry-run/admission test was possible without a cluster. No Azure, cloud or paid API was used.

The read-only nginx ConfigMap mount causes the existing entrypoint's IPv6-default script to report that it cannot modify default.conf; startup continues and nginx -t succeeds. The configured IPv4 listener is intentional. A transient WSL working-directory error affected one final Git whitespace invocation; rerunning from the canonical project path passed. It did not affect application tests.

## Regressions actually run

- `./scripts/test-api.sh`: **62 JUnit tests, zero failures/errors/skips**, including isolated PostgreSQL integration. BUILD SUCCESS.
- `./scripts/test-worker.sh`: **77 pytest tests passed in 7.23s**, including real MiniLM/database retrieval; unchanged ingestion skipped all ten runbooks.
- Existing frontend test image: `npm test && npm run build`: **7 tests passed**, TypeScript and Vite production build successful.
- `bash scripts/test-dashboard.sh`: **14 real browser checks passed**, zero browser errors; actual runtime RETRIEVAL_ONLY. Generated-mode UI fixture remains distinct from real model inference.
- Fault, benchmark and alert-observer helper unittests: **8 + 8 + 3 = 19 passed**.
- `python3 scripts/verify-api.py`: **12 real HTTP checks passed**.
- `./scripts/verify-infra.sh`: actual PostgreSQL TCP/vector 0.8.7/vector arithmetic and Kafka produce/consume passed, `Consumed: incidentiq-smoke-ok`.
- `python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY`: HTTP 201 → outbox → Kafka → worker → stored diagnosis HTTP 200, one receipt/diagnosis/five snapshots; duplicate preserved diagnosis/evidence. Incident `7957de9c-e8c5-4121-9639-603266bd56b3`, event `7367478a-1bee-45df-8202-55575a6a3ab8`, diagnosis `c37ce937-c4be-4aeb-84cf-88c85bc91b55`; duplicate offset 95, committed 96.

These real integration results belong to the existing Compose environment; they are **not Kubernetes smoke results**. They retain synthetic fixtures and preserve prior records. The expensive distributed fault suite, automatic-alert fault flow and live Ollama tests were not rerun for this manifest-only change; their existing unit coverage ran, application sources were unchanged, and no claim is made that they ran again.

## Preservation and unresolved runtime checks

Normal API, publisher, worker, frontend, PostgreSQL, Kafka and monitoring services remained running/healthy (publisher has no container health check). PostgreSQL still maps localhost:55432 to 5432. Original volume timestamps are unchanged: postgres_data/kafka_data 2026-11-06T00:00:34Z; prometheus_data/grafana_data 2026-11-06T01:22:39Z; alertmanager_data 2026-11-06T01:58:52Z; ollama_data 2026-11-06T16:26:37Z. No Compose data/volume was used by Kubernetes or deleted. No normal Docker Compose configuration, runtime source or applied migration changed.

Remaining checks require adequate available RAM and a local cluster: scheduling/resource fit, dynamic PVC binding/permissions, CoreDNS and controller quorum bootstrap, Secret creation, Flyway startup, Job completion, actual pod probes, image loading, StatefulSet persistence across restarts, and the provided incident smoke helper. Monitoring is intentionally outside this overlay. Local development constraints and storage-loss risks are documented in README.md. Do not present this as production-ready or deployed.
