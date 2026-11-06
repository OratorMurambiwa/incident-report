# Memory exhaustion, OOMKilled and heap pressure

## Symptoms and impact
A container is OOMKilled, exits with code 137, repeatedly restarts, or logs Java OutOfMemoryError or Python MemoryError. Resident memory approaches its cgroup limit; frequent garbage collection pauses may precede failure. Distinguish Java heap exhaustion, native/direct-buffer growth, Python object growth and host-wide memory pressure. A normal heap graph does not rule out a native-memory problem.

## Gather evidence
Inspect container termination reason, memory limit and restart history. Compare RSS, heap usage, allocation rate and process count before and after the incident. Review recent changes involving caches, batch sizes, image processing, embeddings or large API responses. Capture safe memory statistics before restarting when possible. Heap dumps can contain sensitive data and consume significant disk space; use an approved local location and bounded collection procedure.

## Diagnose growth patterns
A steadily increasing baseline after repeated requests suggests retention or a leak. Sharp peaks tied to scheduled jobs suggest oversized batches or multiple simultaneous jobs. For Java, compare live heap after garbage collection with maximum heap and native overhead. For Python, inspect batch size, model copies, retained lists and subprocesses. Ensure one cached embedding model is shared per worker process rather than loading a model per event. Check whether multiple workers were accidentally started inside one memory-limited container.

## Safe mitigation
Pause a confirmed memory-heavy job, reduce its batch size or roll back the triggering release. Bound cache size and request payload limits. Restart only the affected component when needed to restore service, preserving evidence and durable queues. Increasing the container limit is temporary relief only if the host has capacity. Do not configure the JVM heap to equal the entire container limit; native allocations and thread stacks still need memory.

## Recovery and rollback
Observe memory through multiple workload cycles; one low reading after restart is insufficient. Verify restart count stabilizes, garbage collection pauses normalize and queued work drains. Revert tuning that worsens throughput or host memory pressure. Confirm event offsets and durable receipts prevent duplicate side effects after worker restarts.

## Prevention and escalation
Add alerts on memory utilization, growth rate and restarts. Test representative maximum payloads and embedding batches. Record image version, container limits, workload shape and memory evidence. Escalate persistent native growth or host-wide OOM with safe process/container measurements rather than relying only on application heap metrics.
