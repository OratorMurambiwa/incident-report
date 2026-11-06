# Kafka consumer lag and stalled event processing

## Symptoms and scope
Kafka consumer lag grows, committed offsets stop advancing, or incidents remain PENDING while outbox rows are already published. Distinguish producer backlog from consumer backlog: unpublished outbox rows indicate publisher trouble, while increasing log-end offsets with stable consumer offsets indicate worker trouble. A lag of zero does not mean all incidents succeeded if failed records were durably quarantined.

## Inspect broker and group state
Check Kafka container health and the relevant topic's partition leader, replicas and ISR. Describe group incidentiq-worker-v1 with kafka-consumer-groups.sh and record current offsets, log-end offsets and lag per partition. Confirm the group has an active member assigned to incident.created. Review worker logs for database failures, contract validation errors, repeated rebalance messages and exhausted retries.

## Diagnose producer versus consumer
Inspect outbox_events for unsent rows, attempts, next_attempt_at and safe last_error values. Ensure the publisher uses kafka:29092 internally and acks=all. For consumers, compare processing time with max_poll_interval_ms and check database latency and local model loading. The worker commits offsets only after a receipt/status/retrieval transaction or durable quarantine. Check failed_events and the quarantine counter even when consumer lag has drained.

## Mitigation
Restore the failed database, broker, worker or network path first. Reduce expensive per-event work or batch sizes if processing cannot keep up. Restart a failed worker only after preserving logs; receipt deduplication permits replay safely. Add consumers only up to available partitions and only when ordering requirements allow it. Do not reset offsets forward, delete topics or delete volumes to make a lag graph look healthy; those actions can hide unprocessed work.

## Recovery and replay
Verify committed offsets resume, lag trends down under normal traffic and new HTTP incidents reach RECEIVED. Confirm outbox rows receive published_at and each event has one processed receipt. Investigate retained failed_events explicitly; fix the cause before republishing preserved events. Reuse the same eventId only for unchanged data so deduplication can prevent duplicate side effects.

## Prevention and escalation
Alert separately on outbox age, consumer lag and quarantine count. Record topic, partition, offsets, consumer group, broker health and affected event IDs. Plan partition count and per-event capacity before adding concurrency. Escalate repeated broker failures or data-loss concerns with retained evidence and avoid speculative offset changes.
