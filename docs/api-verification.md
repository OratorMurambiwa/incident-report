> Historical API milestone. Current delivery/worker results are in [event-verification.md](event-verification.md).

# REST API verification — 2026-11-05 (America/Chicago)

## Implemented

Spring Web + Data JPA + Jakarta Validation + Flyway. DTO/controller/service/repository layers and centralized Problem Detail errors. UUID incidents and one-to-one diagnoses in the incidentiq_api schema. POST incident creation, paginated listing, incident lookup and diagnosis lookup. API is available at http://localhost:8080.

PostgreSQL and Kafka container configurations/volumes were preserved; PostgreSQL remains published at 55432. Compose gained the API service with internal postgres:5432/kafka:29092 addresses, dependency readiness and HTTP health check. Compose/.env.example now default to host port 55432 too. No Java/Maven installation was used on the host.

## Commands and actual results

- `docker compose config --quiet`: exit 0.
- `docker compose build api`: exit 0 after correcting malformed escaping in two test JSON strings found by the first compile attempt. Build-time JUnit result: 26 discovered, 21 executed successfully, 5 PostgreSQL tests explicitly skipped (no database inside Docker build). Java 21 compilation and executable JAR packaging succeeded.
- `./scripts/test-api.sh`: exit 0. All 26 JUnit tests executed against the test configuration, including five real PostgreSQL integration tests. Output:

```text
Tests run: 17, Failures: 0, Errors: 0, Skipped: 0 -- IncidentControllerTest
Tests run: 4, Failures: 0, Errors: 0, Skipped: 0 -- IncidentServiceTest
Tests run: 5, Failures: 0, Errors: 0, Skipped: 0 -- PostgresIntegrationTest
Tests run: 26, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

Database tests use the isolated incidentiq_api_test database; transactions roll back. They test persisted incidents, successful diagnosis lookup through MockMvc/JPA, orphan rejection, severity constraints and duplicate diagnosis rejection.

- `docker compose up -d --wait api`: exit 0. Startup log: `Successfully applied 1 migration to schema "incidentiq_api", now at version v1`. Hibernate schema validation succeeded; HTTP server started on 8080.
- `python3 scripts/verify-api.py`: exit 0. Twelve actual network HTTP requests passed (not mocked):

```text
GET /actuator/health: HTTP 200
POST /api/incidents: HTTP 201
Created incident 71b88560-3f88-4811-8531-49e0c1692300, status=PENDING
GET /api/incidents/71b88560-3f88-4811-8531-49e0c1692300: HTTP 200
GET /api/incidents?page=0&size=20: HTTP 200
GET /api/incidents/71b88560-3f88-4811-8531-49e0c1692300/diagnosis: HTTP 404
GET /api/incidents/06d6ddeb-2484-418e-ae16-3f8cfb16022a: HTTP 404
GET /api/incidents/31aff8a0-d7de-492c-8aba-51af2c4253dd/diagnosis: HTTP 404
POST /api/incidents: HTTP 400
POST /api/incidents: HTTP 400
POST /api/incidents: HTTP 400
GET /api/incidents/not-a-uuid: HTTP 400
GET /api/incidents?size=101: HTTP 400
All 12 HTTP checks passed; synthetic incident retained.
```

To verify the successful diagnosis response over real HTTP, inserted one explicitly synthetic diagnosis for the above synthetic incident via container psql, then made an additional HTTP request and asserted IDs/summary:

```text
GET /api/incidents/71b88560-3f88-4811-8531-49e0c1692300/diagnosis: HTTP 200
{
  "id": "14cbca3b-e7a5-4298-8c03-5ebd7072ddcb",
  "incidentId": "71b88560-3f88-4811-8531-49e0c1692300",
  "summary": "Synthetic verification fixture; not AI-generated",
  "recommendations": "No operational action: this record verifies the diagnosis HTTP response.",
  "createdAt": "2026-11-06T00:10:37.336753Z",
  "updatedAt": "2026-11-06T00:10:37.336753Z"
}
```

One synthetic incident and its synthetic diagnosis remain in the application database as verification fixtures. No generated diagnosis or AI capability is implied. Database constraint/missing-record tests use rollback or nonexistent UUIDs.

- `./scripts/verify-infra.sh`: exit 0. PostgreSQL TCP/password authentication inside the container succeeded, pgvector 0.8.7 and vector distance 1 returned, incidents.raw and incidents.analyzed had leader/replica/ISR 1, and the temporary Kafka round trip returned `Consumed: incidentiq-smoke-ok`. Temporary topic cleanup completed.
- `docker compose ps -a`: API, PostgreSQL and Kafka healthy; kafka-init exited 0. Published ports: 8080, 55432 and 9092, respectively, all bound to 127.0.0.1.
- Container psql confirmed Flyway version 1 success and pgvector extension 0.8.7 still installed. No persistent volumes were deleted.

## Remaining work

No blocker remains for the implemented API. Kafka event publication, analysis workers, AI inference and live frontend integration are not implemented. No diagnosis write endpoint exists. Monitoring profile, worker builds and frontend builds were not tested in this continuation. Dependency resolution/build and runtime execution stayed local apart from downloading open-source images/artifacts. No cloud resources, remote repository or paid services were used.
