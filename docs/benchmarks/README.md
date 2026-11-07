# Local performance benchmarks

These are bounded, reproducible **retrieval-only** baselines for a 7.2 GiB WSL machine, not saturation/capacity claims. k6 runs locally in Docker; no Grafana Cloud, paid API or hosted model is used. Ollama is never started by this harness. Keep any future Ollama results in a separate run/provider report; model verification timings in ../ollama-verification.md are not comparable to these baselines.

## Reproduce

Start the existing local platform and build its current images first. Host Python 3 standard library and Docker are sufficient; no host k6, Java, Maven or Python package installation is needed.

```bash
docker compose --profile observability up -d --build --wait
docker pull grafana/k6:1.3.0
python3 -m unittest discover -s benchmarks -p 'test_*.py' -v
python3 scripts/benchmark.py run
```

The runner requires at least 2.9 GB available RAM. Only one benchmark runner is allowed. It creates a uniquely named `incidentiq_bench_<run-id>` database on the existing PostgreSQL server, marked with an ownership comment, and starts the separate `incidentiq-bench` Compose project. A separate single-node KRaft broker holds the benchmark's `incident.created` topic. The normal topic, consumer group, incidents and runbooks are never written by the benchmark. Port 18080 is temporary/localhost-only; normal PostgreSQL stays on 55432. Normal platform services remain running, sharing CPU and the PostgreSQL server; conditions are not a dedicated-host comparison.

Resource ceilings (only the services needed for each phase run):

| Container | CPU quota | Memory cap |
| --- | ---: | ---: |
| Benchmark API | 1.5 | 512 MiB; JVM heap 128–256 MiB, Hikari max 5 |
| Benchmark Kafka | 1 | 640 MiB; JVM heap 128–256 MiB |
| Benchmark publisher | 0.5 | 384 MiB; JVM heap 64–128 MiB, Hikari max 3 |
| Benchmark worker | 1 | 1024 MiB; existing embedding code uses two Torch threads within this quota |
| k6 | 0.5 | 256 MiB |
| Independent observer | 0.5 | 128 MiB |

The harness declares no named volumes and never deletes Docker volumes. The pinned Kafka image declares three ancillary anonymous mountpoints (/etc/kafka/secrets, /mnt/shared/config, /var/lib/kafka/data); Docker creates those mounts and down without --volumes retains them. Broker logs use the explicitly configured /tmp path in its temporary container filesystem, not those mounts. A lightweight TCP readiness probe avoids JVM health-command interference under the one-CPU quota; actual topic creation and produce/consume/persistence checks verify Kafka functionality.

## API methodology

24 deterministic synthetic incident payloads with unique UUIDs seed the isolated database. No worker/publisher runs during HTTP measurement, so POST measures the real incident + transactional outbox commit without concurrent analysis load.

1. k6 warmup: 2 VUs, 5 seconds, excluded from reported API read/write results.
2. Read mix: 4 VUs, 20 seconds, 50ms think time; equal round-robin list, severity/status/service-filtered list and detail GETs. Seed rows are PENDING. Lists use the real default page size of 20.
3. Create: 2 VUs, 40 total POST iterations, 100ms think time, at most 20 seconds. Every request must return 201.

Read/write phases use separate k6 invocations so each throughput denominator belongs to that phase. k6 `http_req_duration` measures sending + waiting + receiving (milliseconds); it excludes connection-blocked/setup time. Throughput is k6's actual request count / test elapsed time, including think time. Errors are the HTTP-failure rate plus explicit status checks. Thresholds require zero HTTP failures and all status checks passing; no invented latency SLO is imposed. p95/p99 are k6 sample percentiles, not Prometheus histogram estimates. Forty POST samples give a noisy p99 close to the slowest observation. Four VUs and think time deliberately bound offered load; results do not establish maximum API capacity or production SLOs.

## Asynchronous methodology

The worker ingests the real ten runbooks / 60 chunks using pinned local MiniLM embeddings. The 24 seeds + 40 measured API writes become 64 **unmeasured** warmup events, processed through the actual outbox, Kafka and retrieval worker. Model weights and database pages are warm. No event-result embedding cache is added.

The publisher then stops while k6 creates a separate fixed 60-event batch (2 VUs, at most 20 seconds). Its HTTP summary is saved as enqueue.json but is not combined with the API write result. A read-only independent consumer/DB observer starts before the publisher is released. It never commits application offsets or joins the worker's group.

- Broker topic timestamps are forced to **LogAppendTime** and asserted on consumed records.
- Each latency sample is Kafka append timestamp → first visible committed RETRIEVAL_ONLY diagnosis in a fresh PostgreSQL snapshot. All containers share one Docker host clock. This includes consumer queueing, embeddings/vector retrieval, transaction commit and observer delay; it excludes HTTP creation and initial outbox/JVM startup before the first Kafka append.
- Throughput is 60 committed diagnoses / (first Kafka append → last committed diagnosis observation). This includes later publisher pacing and backlog draining. The unchanged publisher sends batches of at most 20 then waits one second, so this is the full pipeline under that pacing, **not standalone broker capacity**.
- Polling targets 100ms; Kafka polling, SQL and scheduling add overhead. Observations are upper bounds on true commit visibility, not exact commit timestamps. The measured maximum observer cycle is recorded. We deliberately do not subtract diagnoses.created_at from incidents.created_at: PostgreSQL now() can represent transaction start rather than the durable completion being measured.
- Average/p95/p99 use the 60 retained millisecond samples with linear interpolation; small-batch tails are noisy.
- Completion requires 60 published outboxes, 60 unique Kafka events, 60 RECEIVED incidents, 60 receipts, 300 snapshots and 60 visible retrieval-only diagnoses. Failure table count must be zero, and the worker's committed offset must reach the broker end offset after durable processing.

The asynchronous observation deadline is 120 seconds; subprocesses/startup phases also have finite timeouts. Processing failures/timeouts make the run incomplete and block a successful benchmark claim. Payloads are a repeated synthetic PostgreSQL connection-exhaustion example, not a representative distribution of production incidents. No remediation is executed.

## Files and interpretation

`runs/<run-id>/conditions.json` records hardware, memory before/after, application image IDs/commit, harness hashes, CPU/memory bounds and actual runtime caps. `warmup.json`, `read.json`, `write.json`, `enqueue.json` retain raw k6 summaries. `async.json` retains exact observation samples, counts and offset checks; `summary.json` is the concise result; `status.json` identifies a complete/incomplete run. No resolved Compose configuration, credentials, .env files or incident descriptions are saved in these public result artifacts.

Do not compare different source hashes, image IDs, quotas, input sizes, warmup states or busy-host conditions as if they were identical. Repeated runs may differ because of WSL scheduling, caches and concurrent local activity. A cancelled calibration run is retained with complete=false: its Java health checks consumed the broker CPU quota, so it is not the reported baseline. See RESULTS.md for the actual measured final run.

Detailed logs and temporary fixture UUIDs live under ignored `.incidentiq-backups/benchmarks/<run-id>/`. The runner's finally block removes only temporary benchmark containers with `compose down` **without --volumes**. It retains the isolated database and all measurements; normal services/volumes are unaffected.

## Explicit cleanup of isolated test data

After reviewing a run, use its exact recorded ID:

```bash
python3 scripts/benchmark.py cleanup RUN_ID_FROM_CONDITIONS_JSON
```

Cleanup accepts only the strict timestamp/hex run-ID format, derives a benchmark-only database name, verifies its ownership comment, and refuses active connections. It never terminates connections, uses DROP ... FORCE, edits normal rows or removes Docker volumes. Cleanup is not automatic and has not been run on the retained measurements' databases. Raw result files remain after database cleanup. Ancillary anonymous Kafka-image volumes are intentionally retained too; do not use volume prune or --volumes as part of this cleanup.

If an interrupted process leaves `.incidentiq-backups/benchmarks/active.lock`, inspect `docker ps --filter label=com.docker.compose.project=incidentiq-bench` and the recorded run's logs first. Only after confirming no runner is active, remove the stale lock. Do not run normal-project down commands or delete volumes to recover a benchmark run.

Upstream k6 summary API: https://grafana.com/docs/k6/latest/results-output/end-of-test/custom-summary/ . Pinned release: https://github.com/grafana/k6/releases/tag/v1.3.0 . Scripts use only bundled k6 modules; no remote JS imports or cloud output.

Raw k6 Rate metrics use boolean sample names: http_req_failed.values.passes counts true HTTP-failure samples, while its field named fails counts false samples (successful requests). Use its rate for HTTP error rate; do not misread fails as the number of failed HTTP requests.
