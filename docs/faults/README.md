# Step 7C: private distributed fault tests

The suite runs actual application images, PostgreSQL/pgvector, Kafka, local retrieval and durable transactions. It does not mock broker errors, database responses or diagnoses. **Delivery is at least once. No exactly-once Kafka delivery guarantee is claimed.** Event-ID receipts provide idempotent application effects for the tested cases.

```bash
# Existing application images should already be built; no normal service is stopped.
python3 -m unittest discover -s faults -p 'test_*.py' -v
python3 scripts/faults.py run
```

The runner requires at least 3 GB available RAM and permits one suite at a time. Each run creates a unique `incidentiq-fault-<run-id>` Docker project with a private network, its own PostgreSQL container/database, Kafka broker/topic/group, API on localhost:18081, publisher, worker, observer and temporarily a second worker. It never targets normal service names, the normal database/topic/group, or PostgreSQL host port 55432. LLM_PROVIDER=none is forced; diagnoses contain real retrieved evidence, not live generative inference.

The normal worker/API/publisher source is not modified by this suite. `/faults/worker_adapter.py` is a mounted **test-only** entrypoint around the real worker's main loop, process_event, handle_record, quarantine and Kafka consumer. It adds one-shot filesystem gates at transaction/offset boundaries and selects the isolated topic. Production containers never mount this adapter or receive fault flags.

The API's normal fixed-topic outbox constraint/default are preserved in normal migrations. Only the disposable fault database installs a routing trigger and changes that constraint to permit **only its own run-specific topic**. A separate test trigger/advisory lock gates publication after broker acknowledgement. No applied migration is edited. Every API incident still commits atomically with its real outbox row.

## Cases and evidence

1. **Crash before DB commit:** pause inside real processing after receipt/snapshot inserts but before commit. An external observation must see zero effects and an unadvanced offset. SIGKILL the worker container, explicitly start it again, and verify a single committed diagnosis/receipt/five snapshots plus offset advancement.
2. **Crash after DB commit:** pause after the actual transaction commits, before handle_record commits Kafka's offset. Kill/restart. Replay must preserve the existing diagnosis ID and snapshot hash, then commit the offset. External Docker kill/start is controlled recovery, not evidence that arbitrary orchestration will restart a manually killed container.
3. **Duplicates/rebalance:** a second real consumer joins the same group; one partition means one owner plus an idle group member. Send three byte-equivalent event copies with real producer acks, observe two Stable members, then stop the peer and observe one Stable member. Database effects must remain single and unchanged. The recorded interval includes peer startup/join, duplicates and leave, not just an interruption RTO.
4. **Broker outage:** stop only the private broker. Create three real API incidents while it is down; observe persisted outbox retry attempts. Restart the same broker/data volume and require all diagnoses and offsets to recover.
5. **PostgreSQL outage:** hold an event before processing, stop only private PostgreSQL and release the worker. Three processing attempts and the quarantine write fail against the unavailable server. The worker must exit/restart without advancing the offset. Restore PostgreSQL and require redelivery to produce one durable diagnosis; no valid event may silently disappear.
6. **Publisher crash after acknowledgement:** a test trigger blocks the outbox published_at update on an advisory lock. Wait until Kafka delivery has produced a committed diagnosis while published_at remains NULL and the publisher is blocked. Kill the publisher before its DB transaction commits; release the lock and restart it. The same outbox event must be sent again, yielding at least two Kafka records but a single unchanged diagnosis/receipt/evidence set.
7. **Stale membership / UnknownMemberIdError:** pause after DB commit and disable the real client's heartbeat thread through a pinned kafka-python 2.2.15 private test seam. Wait for the **real broker** to report no members; release the stale offset commit. Assert the broker's UnknownMemberIdError is wrapped in CommitFailedError, the real worker exits/restarts automatically, and replay deduplicates before committing a fresh-group offset.
8. **Poison record:** publish actual malformed bytes. Require one durable InvalidEvent quarantine with identical SHA-256 payload hash and an offset committed afterward. This negative record has no incident and is accounted separately from valid-event loss.

The installed Kafka client implementation was inspected. It sends its stable member/generation in OffsetCommit; after the coordinator expires that member, Kafka can reject the request. Disabling heartbeats in the adapter is deliberate fault injection, not a thrown/canned exception. Test-only session/heartbeat values are 6000/1000ms; normal consumer timeouts are unchanged. See [Kafka heartbeat/session configuration](https://kafka.apache.org/39/generated/consumer_config.html). The historical overnight/idle UnknownMemberIdError is consistent with stale membership, but this controlled reproduction does not prove which host/network/heartbeat event caused that old occurrence.

## Accounting and measurements

Authoritative outcomes are PostgreSQL rows plus independent Kafka record/offset/group observations. Every valid incident must have one receipt, one diagnosis, five snapshots, RECEIVED status and a published outbox. Diagnosis UUID and a hash including evidence content/ranks/retrieved_at must survive duplicate/replay cases. Independent consumers never commit the worker's offsets.

Final accounting compares all valid event IDs against all Kafka records, counts producer duplicates separately from replay/duplicate handling logs, and requires the committed offset to equal the topic end. Poison bytes must match the retained quarantine. Processing/log counters can reset across crashes; they are not substituted for durable row counts.

Recovery intervals use the host monotonic clock and end after the required DB effects, offsets and case-specific verification observations are collected. Worker/publisher crash intervals start before kill/restart; outage intervals start before service restoration; stale-member recovery starts when the expired commit gate is released. They include container/model startup, polling, Docker/SQL/admin round trips, history audits and retries. Fault dwell time before restoration is not included in those recovery intervals. Each gate has a 90s cap, polling assertions generally have a 120s cap, and subprocesses have finite timeouts. These are single-run observed upper bounds, not production RTO guarantees or percentile estimates.

## Resource bounds and isolation

| Service | CPU quota | Memory cap |
| --- | ---: | ---: |
| Private PostgreSQL | 0.5 | 384 MiB, shared_buffers 32 MiB, max_connections 30 |
| Private Kafka | 1 | 640 MiB, heap 128–256 MiB |
| API | 1.5 | 512 MiB, heap 128–256 MiB |
| Publisher | 0.5 | 384 MiB, heap 64–128 MiB |
| Each worker | 1 | 1024 MiB |
| Driver | 0.5 | 128 MiB |

The API/publisher stop during the two-worker case to preserve memory headroom on the 7.2 GiB WSL host. Model startup uses the existing local MiniLM weights and ten runbooks; no hosted model, paid service or model download is needed. Broker readiness is a low-overhead TCP check; real topic/producer/consumer tests establish functionality.

Run conditions/source hashes and sanitized case observations are tracked under `docs/faults/runs/<run-id>/`. Raw service logs and gate files live under ignored `.incidentiq-backups/faults/<run-id>/`. Passwords are random per run, passed only in process/container environments; never save resolved Compose config or container environment dumps in results.

## Retention and cleanup

The finally block releases gates, unpauses only private containers and **stops** the test project. It retains all stopped test containers, their private DB/broker data volumes and diagnostic evidence. Existing normal containers/data/volumes are not stopped or removed. No volume deletion is performed. The Kafka image may create ancillary anonymous mounts; these are retained too.

After reviewing a run, stopped containers can be removed using its exact project label from results (no -v/--volumes):

```bash
docker ps -aq --filter label=com.docker.compose.project=EXACT_PRIVATE_PROJECT_FROM_RESULTS | xargs -r docker rm
```

`docker rm` without force refuses running containers. This does not delete named or anonymous volumes. Do not run volume prune or remove normal-project resources. Retain the conditions/results even after container cleanup. A stale `.incidentiq-backups/faults/active.lock` should be removed only after verifying no suite process is active.

## Limits

Single host, one broker, one partition, small synthetic workload, retrieval-only processing and short injected outages. No claims cover multi-broker quorum loss, multi-partition ordering, permanent disk/WAL loss, cross-region partitions, arbitrary long outages or slow generative inference during a fault. Three processing attempts followed by durable quarantine are still the normal policy when quarantine storage is available; valid quarantined events require explicit operator replay after remediation. Database/quarantine unavailability instead leaves the Kafka offset uncommitted and triggers restart. No remediation commands are executed by model output.
