# Deployment failures, unhealthy releases and migration errors

## Symptoms and scope
A new image fails to start, enters a restart loop, never becomes healthy, or serves errors immediately after deployment. Build success does not guarantee runtime compatibility. Identify the exact image digest, configuration version, migration version and first failing health check. Separate image-pull/build failures from application startup, readiness and post-start functional failures.

## Inspect startup evidence
Check docker compose ps and targeted logs for the failing service. Confirm required environment variables, internal service addresses, readable mounts and non-root filesystem permissions. Review the earliest startup exception rather than only repeated shutdown messages. For Java, check Flyway migration output and Hibernate schema validation. For Python, verify imports, pinned dependencies and availability of local model files with offline loading enabled.

## Migration compatibility
Inspect Flyway schema history and the exact SQL failure. Do not edit an already applied migration or delete its history to silence validation. A deployment may require a new compatible migration before starting the application. Confirm the old release can still read the schema before choosing rollback. Preserve PostgreSQL and Kafka volumes; a clean database can hide the real upgrade failure while destroying working data.

## Safe recovery
Roll back to the last known compatible image and configuration if the schema supports it. Correct a missing environment value, mount path or service dependency through the smallest reviewed change. For a failed new migration, inspect transaction outcome and use a reviewed corrective migration; avoid speculative manual DDL. Restart only affected services after dependencies and readiness conditions are met. Keep the previously working broker/database configuration intact.

## Validate the release
Check health, then perform real representative HTTP reads/writes and asynchronous event processing. For IncidentIQ, verify POST returns an ID, the outbox publishes, and the worker persists RECEIVED plus retrieved runbook context. Confirm consumer lag and quarantine counts, not just container status. Compare error and latency metrics with the previous release.

## Prevention and escalation
Use pinned dependencies, immutable model revisions, multi-stage builds, database-backed tests and explicit readiness checks. Record the failed image, migration history, configuration differences and reproduction command. Escalate rollback incompatibility or suspected data corruption before destructive recovery. Maintain tested backups and a documented migration/rollback compatibility policy.
