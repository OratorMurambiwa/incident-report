# CPU saturation and throttled containers

## Symptoms and scope
CPU usage remains near the configured limit, requests slow down, background work falls behind, and runnable threads accumulate. A container may show CPU throttling even when the host has idle cores. Distinguish CPU saturation from high load caused by blocked disk I/O. Record service throughput, container CPU quota, host utilization and the start of degradation.

## Identify expensive work
Inspect per-process and per-thread CPU usage using available container or host tools. Correlate hot threads with request routes, serialization, regular expressions, garbage collection, compression or model inference. Compare the current request rate and input size with normal operation. Check whether a retry loop is spinning without backoff or whether a scheduled task overlaps its previous execution.

## Runtime-specific investigation
For Java, sample thread stacks and garbage collection metrics using approved tools before making tuning changes. For Python, inspect worker process count and numerical-library thread settings. Local embedding inference may create many CPU threads by default; keep an explicit thread budget to avoid contention with PostgreSQL and Kafka on the same machine. Compare CPU throttled time with wall-clock latency. A pegged single core can indicate a serial bottleneck even if aggregate host CPU is modest.

## Mitigation
Pause nonessential batch work and reduce concurrency for the proven hot workload. Revert a release that introduced an expensive algorithm or runaway loop. Apply rate limiting when arrival rate exceeds sustainable processing capacity. Increase CPU quota or add replicas only after confirming the host and shared dependencies have spare capacity. Avoid increasing every worker pool simultaneously; additional contention can lower useful throughput.

## Recovery and rollback
Check completed requests or events per second, not just CPU percentage. Confirm queues drain, throttling falls and latency improves without raising errors. Roll back thread-count changes that oversubscribe the host. Re-run a representative workload and compare CPU per completed operation with the baseline.

## Prevention and escalation
Add capacity tests for worst-case payloads and local model inference. Bound retries and scheduled task overlap. Record hot-stack samples, image digest, process count and quota configuration for escalation. Investigate unexpected CPU with low application traffic as a possible loop, background task or resource-sharing problem before changing database settings.
