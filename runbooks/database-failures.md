# PostgreSQL database failures and connection exhaustion

## Symptoms and impact
Applications cannot connect to PostgreSQL, report connection refused, too many clients, connection pool exhausted, SQLSTATE 08006, or sustained database errors. Readiness may fail while the process remains alive. Distinguish an unavailable server from a healthy database blocked by expensive queries or connection leaks. Record affected services, first failure time, database name and whether both reads and writes fail.

## Initial diagnosis
Check `docker compose ps postgres` and recent PostgreSQL logs. Run `pg_isready` inside the database container, then a password-authenticated `SELECT 1` against the same host and database used by the application. Verify the application uses postgres:5432 inside Docker, not the published host port 55432. A successful socket connection alone does not establish authentication or query availability.

## Connection pool and lock investigation
Inspect `pg_stat_activity` grouped by state and application_name. Compare active and idle connections with max_connections and configured pool sizes across all replicas. Long idle-in-transaction sessions retain locks and prevent cleanup. Query `pg_blocking_pids(pid)` for stalled sessions; inspect transaction age before selecting a mitigation. Use existing query statistics to identify slow SQL, missing indexes and workload changes. Do not log passwords or full sensitive SQL parameter values.

## Safe mitigation
If the server is unreachable, restore its container/network/storage availability before changing connection limits. If a deployment leaked connections, roll back the application or reduce its connection pool concurrency. Stop admission of new heavy jobs to allow existing transactions to finish. Cancel a confirmed runaway query using its verified PID only after assessing transaction impact. Raising max_connections without memory planning can worsen an outage. Never delete the PostgreSQL volume or reinitialize the database to repair connectivity.

## Recovery and rollback
Revert the specific application or pool configuration change if it increased failures. Verify a read and a small application-approved write, readiness, pool wait time and transaction latency. Confirm connection counts settle and blocked transactions drain. Check the outbox backlog and worker failures after database recovery; durable events may require explicit replay if previously quarantined.

## Escalation and prevention
Escalate suspected corruption, repeated database crashes or storage errors with timestamps, safe log excerpts, active session counts and recent changes. Retain evidence before any recovery procedure. Add pool utilization alerts, bounded connection timeouts, query timeouts, slow-query review and tested backup/restore procedures.
