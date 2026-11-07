# Step 7C actual fault-recovery results

Executed locally on 2026-11-07. Successful run: **20261107t190041z_909be1ac**. [Machine/images/source hashes](runs/20261107t190041z_909be1ac/conditions.json), [complete case observations and final accounting](runs/20261107t190041z_909be1ac/results.json), [reproduction and injection boundaries](README.md).

WSL Linux, Intel Core Ultra 5 225U, 14 logical CPUs, approximately 7.2 GiB RAM; 4,256,112,640 bytes available before starting. Private service CPU/memory caps are documented in the methodology. Existing application commit debc2894970673291140cc58dc7da9770cddfa5a and recorded image IDs were used. Actual local all-MiniLM-L6-v2 embeddings, 10 runbooks/60 chunks, PostgreSQL/pgvector and Kafka; LLM_PROVIDER=none throughout the fault workload. No mocked diagnosis or broker/DB response.

| Real injected case | Observed recovery/verification interval | Durable result |
| --- | ---: | --- |
| Worker SIGKILL before transaction commit | 13.538 s | Uncommitted receipt/evidence rolled back; replay committed one diagnosis |
| Worker SIGKILL after DB commit, before offset commit | 13.595 s | Redelivery preserved diagnosis UUID and evidence hash |
| Three duplicate records plus peer join/leave | 17.515 s | Stable two-member then one-member group; unchanged single diagnosis |
| Private broker stopped; three API creates queued | 38.289 s after restoration began | All three outbox events recovered; total attempts 5/4/4 including success |
| Private PostgreSQL stopped during processing | 8.477 s after restoration began | Failed processing/quarantine left offset 10 unadvanced with end 11; restart recovered it |
| Publisher killed after Kafka acknowledgement, before outbox DB commit | 62.871 s | Two actual Kafka copies; published_at recovered; one unchanged diagnosis |
| Broker expires real consumer membership | 35.519 s after stale commit released | UnknownMemberIdError/CommitFailedError caused restart, deduplication and fresh offset commit |
| Malformed Kafka bytes | 4.876 s | Original payload hash retained in InvalidEvent quarantine before committing offset |

These are single-run monotonic-clock observations including startup, polling, case-specific history/group audits and retries, not percentile or production RTO guarantees. Crash cases explicitly start containers after Docker SIGKILL; automatic process-crash recovery is separately verified in the database and stale-membership cases. The duplicate interval includes peer/model startup, join, delivery and leave. Outage dwell time before restoration is excluded. No OOM was observed in recorded worker/publisher states.

## Final accounting

- 10 distinct valid events, all outboxes published, all incidents RECEIVED.
- Exactly one durable receipt and diagnosis per valid event: **10 diagnoses and 50 immutable retrieval snapshots**.
- Kafka contained 14 valid records for those 10 IDs: three intentional duplicate records and one actual ambiguous-ack publisher resend. Replay also occurred without adding records. Seven duplicate-handling log entries were observed across workers.
- One additional malformed record at offset 14 was durably quarantined, InvalidEvent/one attempt. Payload SHA-256: `8ca5c6a84840a219b2519e54117fcf52a3fc70d2fb3b4742c041f2a8669a501c`.
- Final committed offset **15 = end offset 15**; Stable group, one member before teardown. Independent history observer scanned all records without committing application offsets.
- **Zero observed valid-event loss, zero duplicate database effects, zero unexpected quarantines** in this workload. This is at-least-once delivery with tested idempotent effects, not exactly-once Kafka delivery.

## UnknownMemberIdError investigation

The mounted adapter disabled the actual pinned client's heartbeat thread after committing a diagnosis and before committing its offset. The real broker expired the member: group Empty/members 0, end 14, committed 13. Releasing the stale commit produced broker UnknownMemberIdError wrapped as client CommitFailedError. Production handling propagated the failure, Docker restarted the worker, the receipt detected redelivery, and the rejoined consumer committed offset 14. The diagnosis UUID and evidence hash stayed unchanged. Worker RestartCount increased; it was 3 after the preceding broker/database faults and this case.

No production logic was weakened to hide this error. Committing ahead or swallowing a failed commit would undermine the durability boundary. The old overnight benchmark occurrence is consistent with membership expiration, but its original host/network/heartbeat trigger is not established by this reproduction.

## Harness failures corrected before the successful run

- Run 20261107t184738z_8d63aac4 stopped at warmup: the isolated routing trigger selected the run topic but the unchanged fixed-topic CHECK rejected the insert. Corrected only the private fixture's constraint; production migrations remain untouched. [Incomplete result](runs/20261107t184738z_8d63aac4/results.json).
- Run 20261107t185003z_d94dc47c passed five cases, then the independent Kafka history observer exceeded its 40-second host timeout using lazy seek_to_beginning/position lookup. Numeric seek to offset 0 on the fresh topic and supported client timeout configuration fixed the observer. An exploratory unsupported end_offsets(timeout_ms=...) argument was rejected and removed before rerunning. [Incomplete result](runs/20261107t185003z_d94dc47c/results.json).
- The entire eight-case suite was rerun successfully with the final source hashes. Failed attempts remain marked complete=false; their stopped containers and volumes are retained too.

## Limitations and preservation

One host/broker/partition, ten valid events, brief controlled faults, shortened test-only membership timeouts and retrieval-only diagnoses. This does not verify multi-broker quorum recovery, disk/WAL loss, arbitrary long outages, multi-partition ownership transfer or Ollama inference under fault. With one partition, the second member can be idle; the test verifies real join/leave rebalancing, not parallel processing. Durable quarantine remains the policy after bounded failures when its database is available; explicit operator replay is required for such events.

The new suite never stopped or wrote to normal services. All private containers were stopped after completion; all test and existing volumes were retained. Existing integration regressions separately add their documented synthetic records and temporarily exercise normal development services. Port 55432 remains unchanged. Runtime sources, normal Compose configuration and applied migrations were preserved.

## Regression commands executed

The following passed before publication (Docker supplies Java/Maven/Node/Python dependencies):

| Command/check | Actual result |
| --- | --- |
| `./scripts/test-api.sh` | 62 JUnit tests; zero failures/errors/skips, including real PostgreSQL integration |
| `./scripts/test-worker.sh` | 77 pytest tests passed, including real local embeddings/database retrieval |
| `docker build --target build -t incidentiq-frontend-tests ./frontend`, then container `npm test && npm run build` | 7 Node tests passed; strict TypeScript and Vite build passed |
| `python3 -m unittest discover -s faults -p 'test_*.py' -v` | 8 accounting/isolation tests passed |
| `python3 -m unittest discover -s benchmarks -p 'test_*.py' -v` | 8 existing benchmark helper tests passed |
| `python3 scripts/faults.py run` | Eight real fault scenarios passed; complete=true |
| `python3 scripts/verify-api.py` | 12 real HTTP checks passed |
| `./scripts/verify-infra.sh` | Actual PostgreSQL TCP/vector 0.8.7 arithmetic and Kafka produce/consume passed |
| `python3 scripts/verify-event-flow.py` | Actual outbox/Kafka/worker, duplicate preservation, five snapshots and malformed-byte quarantine passed |
| `python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY` | Stored diagnosis/evidence and duplicate preservation passed |
| `python3 scripts/verify-monitoring.py` | Both scrape targets UP; all 16 Grafana panels returned real datasource values |
| `bash scripts/test-dashboard.sh` | 14 browser checks passed; no browser errors; actual runtime RETRIEVAL_ONLY, generated-mode UI fixture labeled separately |
| `docker compose --profile observability config --quiet` | Valid |
| `docker compose exec -T prometheus promtool check config /etc/prometheus/prometheus.yml` | Config and three alert rules valid |
| Docker `promtool test rules /etc/prometheus/alerts_test.yml` | SUCCESS with fixtures mounted at /etc/prometheus |
| `docker compose exec -T alertmanager amtool check-config /etc/alertmanager/alertmanager.yml` | SUCCESS; one receiver |
| `python3 -m unittest discover -s scripts -p 'test_alert_smoke.py' -v` | 3 recurring-occurrence observer tests passed |

An initial rule-test invocation mounted fixtures at /rules while the existing fixture references /etc/prometheus/alerts.yml. It failed to find the rules; correcting only the test invocation produced SUCCESS. No alert configuration was changed. Existing performance measurements were not rerun or replaced by these recovery intervals.

The first automatic-detection regression failed because its observer accepted an old resolved occurrence sharing the current alert fingerprint before the new webhook arrived, then compared that old occurrence against the new one. This was a test-observation race with preserved historical data. The helper now matches startsAt to the current Alertmanager occurrence, using the same microsecond truncation as the API. Three targeted mocked-observer tests passed (historical rejection, current nanosecond/UTC normalization, missing webhook). These are observer unit tests, not substitutes for the real container rerun. No existing incidents were edited or removed to make the test pass.

The corrected `python3 scripts/smoke-auto-detection.py --skip-build` rerun passed all three real alert flows (HTTP 500, elevated p95 and actual stopped worker), repeat-notification deduplication, resolution and independent Kafka event-ID checks. All three retained one outbox/receipt/diagnosis and five snapshots. Zero recursive internal-route incidents; default simulation returned 404 afterward. The initial invocation already rebuilt API/worker images; --skip-build reused them.

- IncidentIQHighHttp500Rate: `25d2e63f-fdb3-43c2-a19e-37666bac72cb`, RESOLVED
- IncidentIQHighP95Latency: `6dcf52d2-ce1c-45ef-ad62-285ade925f53`, RESOLVED
- IncidentIQServiceUnavailable: `a141ffb5-57e0-4f2b-893d-dece17ebe703`, RESOLVED

## Separate existing Ollama regression

The fault suite above uses retrieval-only. Separately, the existing real-container `python3 scripts/verify-local-ollama.py` verifier exercised cached qwen3:0.6b through Ollama 0.6.8 on CPU. All three React-to-GENERATED diagnosis cases completed:

| Case | End-to-end | Successful model call | Earlier 30-second timeouts |
| --- | ---: | ---: | ---: |
| Database | 95.715 s | 25.894 s | 2 |
| Memory | 55.373 s | 22.964 s | 1 |
| Kafka | 61.059 s | 24.559 s | 1 |

Each had one published outbox, receipt, diagnosis and five snapshots. The full end-to-end times include retries and observation overhead. Actual adversarial model outputs with an invented citation and prohibited forward-offset advice were rejected in 21.886/16.384 s, with no database writes. These deliberately constrained model-output contract tests do not certify semantic grounding of all generated advice. No recommendations were executed. This is a separate regression, not an Ollama-under-fault benchmark or inference SLA.

Actual missing-model and one-second-timeout cases both passed: FAILED, exactly one ModelUnavailable quarantine/three attempts, zero receipt/snapshot/diagnosis rows, outbox published and offset committed after quarantine. The verifier restored provider none in finally. A subsequent real retrieval-only RAG replay check passed. [Sanitized regression observations](regressions.json) retain actual incident IDs, offset evidence and counts without raw incident/evidence/model payloads or credentials.

## Final health and publication review

At 2026-11-07T19:39:06Z, the restored browser suite again passed all 14 checks with no browser errors. Provider none was confirmed; optional Ollama stopped. API/frontend/worker/PostgreSQL/Kafka/Prometheus/Grafana/Alertmanager were healthy and publisher running. All four Prometheus targets were UP; all three alert rules health=ok/inactive; zero active alerts. No private fault containers remained running. The six tested harness source hashes matched the completed run.

PostgreSQL remains published at 55432. Original postgres_data/kafka_data creation timestamps remain 2026-11-06T00:00:34Z; prometheus_data/grafana_data 2026-11-06T01:22:39Z; alertmanager_data 2026-11-06T01:58:52Z; ollama_data 2026-11-06T16:26:37Z. A normal-database query found zero incidents bearing the completed private fault-run service suffix. All private volumes and stopped containers are retained; cleanup is explicit and never deletes volumes.

Final counts: 62 Java, 77 Python, 7 frontend, 19 helper/observer unit tests (8 new fault + 8 benchmark + 3 observer), 14 browser checks (also rerun after Ollama), eight actual fault cases, 12 HTTP checks, 16 Grafana panels, three actual automatic-alert flows and the separate actual-model positive/negative checks described above. No production reliability code, applied migration or normal Compose configuration changed.
