# Downstream timeouts and connection deadlines

## Symptoms and scope
Requests fail with socket timeout, connection timeout, read timeout, deadline exceeded or HTTP 504. Record whether the deadline expires while connecting, waiting for the first response byte, reading a response body or acquiring a connection from a pool. Compare caller and downstream timing for the same safe correlation ID. A timeout is an observation, not proof that the downstream operation did not commit.

## Diagnose the boundary
Verify DNS resolution, service address and internal Docker network routing from the caller's environment. Check downstream health and latency independently. Inspect connection pool wait time and concurrency before increasing network timeouts. Compare recent payload growth, retry settings and deployment changes. For PostgreSQL, separate statement timeout from connection acquisition and authentication failures. For Kafka, distinguish producer metadata availability, delivery timeout and consumer processing deadlines.

## Budget and retry analysis
Map the end-to-end deadline across gateway, API and downstream clients. The caller's total deadline should leave time to return an error and must include all retries. Multiple nested retry layers can multiply requests and saturate an already slow dependency. Look for synchronized retry spikes and unbounded work queues. Identify operations with side effects before allowing automatic retries; POST requests require an application-specific idempotency mechanism.

## Mitigation
Restore the slow or unreachable dependency and reduce competing work. Apply bounded concurrency and supported circuit-breaking behavior when a dependency remains unavailable. Retry only appropriate idempotent operations with bounded exponential backoff. Adjust a proven unrealistic timeout only after measuring normal and tail latency; longer deadlines alone can retain more memory and threads. Roll back routing or client changes that introduced the timeout.

## Recovery and rollback
Run the original safe request and inspect both caller and downstream completion. Confirm successful operations are not duplicated after retries. Check queue depth, resource utilization and timeout rate over normal traffic intervals. Restore previous timeout values if the adjustment increases saturation without improving useful completions.

## Prevention and escalation
Document timeout budgets, retry owners and idempotency guarantees. Add separate metrics for connect, pool-wait and read timeouts. Escalate with timestamps, dependency address, deadline settings, measured downstream duration and sanitized error classes. Preserve outbox and failed-event evidence during recovery; never acknowledge undurable work simply to bypass a timeout.
