# High application latency and slow responses

## Symptoms and scope
Users report slow pages or APIs; p95/p99 request duration rises while median latency may remain normal. Queue depth or database wait time increases. Separate server processing duration from client network delay and compare affected routes with baseline traffic. Record latency percentiles, request rate, concurrency and the start of degradation. Averages alone hide tail latency and can mislead diagnosis.

## Trace the critical path
Check application, reverse-proxy and dependency timings for the same request correlation ID. Compare database query duration, connection acquisition, downstream HTTP time and thread-pool queue time. A quick handler with a slow dependency needs a different mitigation from a CPU-bound handler. Review changes to query plans, payload sizes, cache hit ratios and deployment configuration.

## Resource and workload diagnosis
Inspect container CPU usage, CPU throttling, memory pressure, garbage collection pauses and disk I/O latency. Check whether worker threads are blocked waiting for sockets or database connections. Identify unbounded list endpoints, N+1 database queries and expensive serialization. Compare workload volume with capacity before adding concurrency: more parallel calls can overload the same constrained dependency. Investigate hot partitions or a small set of unusually large requests.

## Mitigation decision
Reduce expensive background work and apply bounded admission control where supported. Revert a confirmed slow query or recent deployment regression. Restore cache availability if misses caused excess backend calls. Add an index through a reviewed migration only after checking the query plan and write impact. Scale or increase limits only when the measured bottleneck supports that action. Do not increase all client timeouts as the first response; that can retain more queued requests.

## Recovery and rollback
Verify p95 and p99 duration together with throughput, errors and queue depth. Re-run the original slow request with a safe workload and confirm the slow span improved. Revert tuning that raises CPU, memory or database lock contention without improving completion time. Check that low latency is not simply the result of rejected requests or lost traffic.

## Escalation and prevention
Escalate with representative timings, saturation metrics, safe traces and recent changes. Add percentile latency objectives, bounded pagination, connection/thread limits, slow-query monitoring and realistic load tests. Document the measured bottleneck and capacity limits so future responders do not repeat speculative tuning.
