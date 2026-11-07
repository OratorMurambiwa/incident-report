# Measured retrieval-only baseline — 2026-11-07

Completed run: **20261107t181836z_e97e5b4b**. [Concise machine-readable results](runs/20261107t181836z_e97e5b4b/summary.json), [test conditions/source hashes](runs/20261107t181836z_e97e5b4b/conditions.json), [completion marker](runs/20261107t181836z_e97e5b4b/status.json).

Hardware: Intel Core Ultra 5 225U, 14 logical CPUs; Docker/WSL RAM 7.22 GiB, 2 GiB swap. About 3.99 GiB available before the run and 2.78 GiB while benchmark containers were still active at the end. Existing local platform/monitoring remained running. Ollama was not started. Total harness time before teardown was 258.75 seconds, including container startup, ingestion, HTTP warmup and 64 warm pipeline events.

Application images were the existing f8912f0 application baseline, with exact image IDs recorded. Load generator: pinned grafana/k6:1.3.0; actual version output reports v1.3.0+dirty, commit 5870e99ae8-dirty, Go 1.25.1 linux/amd64. The suffix is the published k6 build label, not a claim that this project's Git source was modified by k6.

## API

| Workload | Requests | Throughput | Average | p95 | p99 | HTTP error rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Read mix, 4 VUs / 20s | 1371 | 65.80 requests/s | 7.36 ms | 14.53 ms | 40.53 ms | 0% |
| Create, 2 VUs / 40 iterations | 40 | 17.02 requests/s | 15.85 ms | 21.35 ms | 22.28 ms | 0% |

All explicit status checks passed (GET 200 / POST 201). These throughputs include the configured 50ms read / 100ms create think times and are not maximum server capacity. Creation commits the incident plus outbox; workers/publishers were stopped during API measurement. Reads use 24 synthetic rows. The short warmup and small POST sample mean percentile tails should not be treated as production SLO evidence.

Raw k6 summaries: [warmup](runs/20261107t181836z_e97e5b4b/warmup.json), [reads](runs/20261107t181836z_e97e5b4b/read.json), [writes](runs/20261107t181836z_e97e5b4b/write.json), [separate async enqueue](runs/20261107t181836z_e97e5b4b/enqueue.json).

## Asynchronous Kafka / retrieval pipeline

| Measurement | Observed |
| --- | ---: |
| Measured events | 60 |
| Committed retrieval-only diagnoses | 60 |
| Throughput, first append to final observed commit | 6.1872 events/s |
| Batch drain window | 9.6974 s |
| Average append → committed visibility | 2730.88 ms |
| p95 append → committed visibility | 5204.01 ms |
| p99 append → committed visibility | 5369.19 ms |
| Maximum append → committed visibility | 5385.44 ms |
| Processing failures / error rate | 0 / 0% |
| Duplicate Kafka deliveries observed | 0 |
| Maximum observer cycle | 115.54 ms |

[Raw async samples and completion checks](runs/20261107t181836z_e97e5b4b/async.json).

Verified 60 Kafka events, 60 RECEIVED incidents, 60 receipts, 300 evidence snapshots, 60 published outboxes and 60 diagnoses. Worker committed offset **124**, equal to topic end offset **124** (64 warmup + 60 measured events). No quarantined records were present in the isolated database.

Latency includes queueing, local embeddings/pgvector retrieval, persistence and observation delay, not just execution inside process_event. It excludes HTTP submission and publisher startup before the first Kafka append. Kafka uses broker LogAppendTime, compared with PostgreSQL clock_timestamp from fresh committed snapshots on the same host. Polling makes measurements upper bounds on commit latency; no transaction-start timestamp is presented as exact completion time.

The worker was limited to **one CPU / 1024 MiB**, API 1.5 CPUs / 512 MiB, publisher 0.5 CPU / 384 MiB and broker one CPU / 640 MiB. Torch still uses the existing two embedding threads within the worker quota. Publisher pacing and this worker CPU quota affect backlog; do not interpret the result as standalone Kafka capacity, an unconstrained production worker result, or an Ollama benchmark. Only one complete trial is reported, with a fixed repeated incident shape and warm corpus. Rerun rather than infer statistical significance from these 60 samples.

## Calibration and retained data

Run **20261107t181450z_740b24bd** was deliberately cancelled after HTTP measurement: the initial Java-based Kafka health probe consumed much of the broker's CPU quota and timed out. Its [incomplete marker](runs/20261107t181450z_740b24bd/status.json) and raw HTTP measurements are retained for audit, but excluded from the baseline table. The benchmark-only probe was replaced with lightweight TCP readiness; topic creation and actual event processing verify function. Normal Kafka configuration was never changed.

Temporary benchmark containers were removed without --volumes. Both uniquely owned benchmark databases were retained, as were existing platform volumes and any anonymous volumes declared by the Kafka image. No existing incident was modified by the benchmark. Explicit optional database cleanup:

```bash
python3 scripts/benchmark.py cleanup 20261107t181450z_740b24bd
python3 scripts/benchmark.py cleanup 20261107t181836z_e97e5b4b
```

These cleanup commands are documented, not executed. The helper validates ownership and refuses active connections; it does not delete Docker volumes. See [reproduction and methodology](README.md).

## Regression and final service verification

Executed after benchmark containers stopped, so these tests did not contaminate the measurements:

- `./scripts/test-api.sh`: **62 tests, 0 failures, 0 errors, 0 skipped; BUILD SUCCESS**.
- `./scripts/test-worker.sh`: **77 passed in 10.72s**; ten unchanged runbooks skipped on test ingestion.
- Frontend `npm test && npm run build` inside Docker: **7 tests passed**, strict TypeScript and production build passed.
- Benchmark standard-library unit tests: **8 passed**, covering interpolated statistics and cleanup refusal/ownership/active-connection checks. Cleanup tests mock SQL; they do not drop real databases.
- `python3 scripts/verify-api.py`: **12 HTTP checks passed**.
- `python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY`: actual diagnosis, one receipt/five snapshots, and unchanged evidence after duplicate delivery passed.
- `./scripts/verify-infra.sh`: PostgreSQL TCP/pgvector arithmetic and Kafka produce/consume round trip passed; only its own disposable smoke topic was deleted.
- `bash scripts/test-dashboard.sh`: **14 browser checks passed**, zero browser JavaScript errors.

One normal worker offset commit encountered Kafka UnknownMemberIdError during post-benchmark regression (not in the isolated benchmark). Its existing fail-closed behavior exited/restarted, then deduplicated the already-committed event. Subsequent real RAG/duplicate and browser flows passed; an additional follow-up RAG/duplicate flow passed with restart count remaining one. No OOM was reported. The commit-failure restart policy was preserved rather than bypassing offset safety. This transient is not hidden in the benchmark's zero-failure statistic, which describes only the isolated measured batch.

Final API, frontend, worker, Kafka, PostgreSQL, Prometheus, Grafana and Alertmanager were healthy; publisher running. All four Prometheus targets were UP with zero active alerts. Normal worker provider remained none. PostgreSQL was still published on 55432. Existing named volume creation times were unchanged (PostgreSQL/Kafka 2026-11-06T00:00:34Z; Prometheus/Grafana 01:22:39Z; Alertmanager 01:58:52Z; Ollama 16:26:37Z). No benchmark containers remained. A query of the normal incident database found **zero rows with either benchmark run suffix**.
