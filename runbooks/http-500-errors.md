# HTTP 500 internal server errors

## Symptoms and scope
A service returns HTTP 500 or another unexpected 5xx response, often with an exception, failed request handler or generic Internal Server Error body. Compare the error ratio by route, service version and dependency. Separate application-generated 500 from reverse-proxy 502/503 responses and from intentional client validation errors. Record a request correlation ID and a redacted example; never copy credentials or whole incident payloads into shared logs.

## Establish the failure boundary
Check application readiness and the earliest exception class around the first failed request. Determine whether all requests fail or a specific payload, endpoint or tenant triggers the issue. Reproduce with a safe test request using the same content type. Compare successful and failing routes to identify common middleware or database access. Review the last deployment, feature flag and configuration changes before assuming a host failure.

## Diagnose common causes
Inspect stack traces locally for null dereferences, serialization failures, incompatible DTO fields, unavailable downstream calls and database constraint errors. A database timeout followed by an HTTP 500 is a dependency symptom; correlate it with pool waits and query latency. A migration/schema mismatch can make only write endpoints fail. Check the Flyway migration result and deployed image digest. Verify error handlers preserve useful status codes without leaking stack traces to clients.

## Mitigation
Roll back a confirmed application regression using the previous compatible image. Disable a recently introduced feature when that is the supported recovery path. Restore dependency availability if the handler fails because a required system is down. Rate-limit or pause a narrowly identified pathological workload instead of restarting every service. Avoid retrying non-idempotent POST requests blindly: the original request may already have committed.

## Verify recovery
Repeat the exact safe reproducer, then a representative read and write. Confirm 2xx responses, expected response fields and absence of new exception bursts. Observe the error ratio and throughput over several normal traffic intervals; a falling request count alone can make the ratio look better. Ensure rollback did not leave a migration incompatibility or lost background jobs.

## Follow-up
Add a regression test for the triggering request, centralized sanitized errors and correlation IDs. Alert on error ratio with a minimum request volume. Document the root exception, route, dependency state and exact deployment change that resolved the issue. Escalate if data consistency or partially committed requests remain uncertain.
