# Authentication failures, expired tokens and invalid credentials

## Symptoms and scope
Clients receive HTTP 401, invalid token, expired JWT, signature verification failure or password authentication failed. HTTP 403 usually means an authenticated identity lacks authorization, which requires a different check. Determine whether all callers fail or only a specific user, service account, audience or recently rotated credential. Record safe identity metadata and timing, never passwords, access tokens or signing keys.

## Inspect identity and time
Check token expiration/not-before times, issuer and audience against the receiving service configuration. Compare the system clocks of issuing and validating components. Review the last secret rotation, configuration deployment and identity-provider change. For JWT validation, confirm the expected signing algorithm and current trusted key identifier; do not disable signature verification to restore access. Avoid copying raw bearer tokens into logs or incident descriptions.

## Dependency-specific diagnosis
For PostgreSQL password authentication failures, verify the application database username, database name and secret source. Changing POSTGRES_PASSWORD in Compose does not reset a password inside an already initialized data volume. Use the supported database credential-rotation procedure. Distinguish an unreachable identity provider from a correctly rejected credential. Check whether an old application replica still uses the previous secret after a rolling deployment.

## Safe mitigation
Refresh an expired credential through the normal authentication flow. Coordinate a secret/key rotation so callers and validators share the intended configuration, preserving a controlled overlap when supported. Roll back a confirmed incorrect issuer/audience configuration or redeploy stale replicas. Do not grant broad administrative privileges, disable authentication or expose credentials in command history as an incident workaround.

## Verification and rollback
Verify a valid identity succeeds, an expired token is rejected and an unauthorized identity remains denied. Test a database query with the intended service account when applicable. Monitor authentication failure rate and confirm that recovery did not weaken authorization. Roll back only the incorrect configuration, preserving audit records of the rotation and affected identities.

## Escalation and prevention
Escalate unexpected authentication bursts, suspicious credential use or unplanned key changes through the local security process. Preserve sanitized audit evidence. Add expiration/rotation reminders, clock monitoring and startup validation of required authentication settings. Document which service owns token issuance, secret delivery and permission changes.
