> RAG commit d82d561 was published and verified on origin/main. Current monitoring/runtime regression results: [monitoring-verification.md](monitoring-verification.md).

# Structured RAG diagnosis verification — 2026-11-05 (America/Chicago)

## Implementation

Read AGENTS.md, worker retrieval/receipt/offset logic, existing diagnosis entity/DTO, migrations, tests and Compose first. Added worker/diagnosis.py with a LangChain LCEL prompt → local Ollama callable → PydanticOutputParser chain. No new dependencies were needed; existing pinned/locked LangChain and Pydantic were reused.

Provider none creates an explicit RETRIEVAL_ONLY diagnosis with no generated cause/investigation/remediation items. Five original excerpts are stored separately as retrievedEvidence. Provider ollama requests structured JSON through the local /api/chat endpoint, validates complete output against a strict schema, requires per-item exact source filenames from the retrieved snapshots and rejects invented filenames in prose. Incident/evidence are untrusted JSON data in the user message; the system policy is separate. No tools, shell execution, remediation executor, cloud provider or automatic model pull exists.

Flyway V5 adds provenance and structured fields to the existing diagnoses table and DIAGNOSED to incident statuses. Existing text rows receive LEGACY provenance. Previous migrations are unchanged. JPA maps JSONB fields to typed DTO records; the existing GET diagnosis endpoint exposes all structured fields plus the original summary/recommendations/timestamps.

Receipt, five snapshots, diagnosis and successful status update commit together. Generated → DIAGNOSED; retrieval-only → RECEIVED. Duplicates return before any retrieval/LLM call. Unavailable models, invalid output and missing evidence roll back the new transaction; after three attempts quarantine persists the raw record and marks pending incidents FAILED atomically. A successful unchanged replay after repair can recover FAILED incidents. Offset commit remains after durable processing/quarantine only; no silent fallback or partial diagnosis is persisted.

## Executed build and test commands

- `python3 -m py_compile worker/diagnosis.py worker/main.py` and verification-script syntax checks: passed.
- `docker compose config --quiet`: exit 0.
- `docker compose build api` and `docker compose build worker`: exit 0. Ordinary worker image build ran 51 unit cases and explicitly skipped 17 database/model integration cases; separate full run below executed those too. Java image build ran database-independent tests and explicitly skipped database cases.
- `./scripts/test-api.sh`: exit 0, real isolated PostgreSQL database:

```text
Tests run: 34, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

All prior 32 Java cases remain; two new cases cover structured generated JSON/provenance through JPA/HTTP mapping and invalid generated provenance constraints. Existing legacy-diagnosis lookup also asserts LEGACY mode.

- `./scripts/test-worker.sh`: exit 0:

```text
68 passed in 6.56s
```

This includes 51 unit and 17 PostgreSQL/model integration cases. Prior 37 cases remain. New coverage includes none-mode labeling/no model invocation, structured mocked Ollama success, schema violations, unknown/prose citations, prompt injection separation, missing/repeated evidence, unavailable model handling, local-only endpoint configuration, actual client JSON-schema request shape with mocked transport, real database diagnosis persistence, DIAGNOSED status with mocked generation, duplicates never regenerating, and unavailable-model retry/quarantine/FAILED state followed by safe replay. Test database fixtures are cleaned; no mocked generated result was inserted into the application database.

- `docker compose up -d --wait api publisher worker`: exit 0. API/worker/PostgreSQL/Kafka healthy, publisher running, topic and runbook initializers exited 0. Worker uses LLM_PROVIDER=none. PostgreSQL remains on host port 55432; no volume was deleted/recreated.

## Actual retrieval-only end-to-end runtime

`python3 scripts/verify-rag-flow.py`: exit 0. Actual output:

```text
POST /api/incidents: HTTP 201, incidentId=9b59df94-6d6c-4537-b6cc-4111fd94bc8c, status=PENDING
GET diagnosis: HTTP 200, mode=RETRIEVAL_ONLY, provider=none, incident status=RECEIVED
Diagnosis id=73f84147-5c19-4232-9bbb-952fd76a7943, eventId=2de6197d-f607-43a0-8f03-97ea23006022, evidence=5, citations=['database-failures.md']
Outbox acknowledged; one receipt, five snapshots, one diagnosis; duplicate offset=8, committed=9
Diagnosis and evidence unchanged on duplicate; real end-to-end verification passed.
```

This exercised real HTTP creation, actual transactional outbox/Kafka, real local embedding retrieval, Python diagnosis storage and GET /api/incidents/{id}/diagnosis through JPA. The script checked nonempty cited evidence, empty generated sections, provider none/model null, explicit RETRIEVAL_ONLY labeling and one receipt/five snapshots/one diagnosis. It replayed the actual Kafka payload and confirmed unchanged snapshots and an identical API diagnosis response afterward.

The synthetic incident/diagnosis and evidence remain as verification data. Database inspection confirmed mode RETRIEVAL_ONLY, generated_causes count 0 and evidence count 5.

## Ollama generation: mocked tests versus actual service

**Actual Ollama generation was not tested.** The provider/client path and structured outputs were tested using mocked responses, including HTTP 404/model-unavailable simulation, and persisted through real PostgreSQL in integration tests. No actual language model was invoked.

A read-only probe from the final worker container returned:

```text
Configured provider: none
Configured Ollama model: (not set)
Ollama availability probe failed: URLError [Errno 101] Network is unreachable
Actual Ollama generation was not performed by this probe.
```

No model was configured and the local endpoint could not be reached from this environment. This is the remaining blocker for real GENERATED-mode inference verification, not a successful Ollama test. To exercise it, configure an already-installed local model and reachable local endpoint in .env, recreate only the worker, then run `python3 scripts/verify-rag-flow.py --expect-mode GENERATED`. Do not interpret retrieval-only excerpts or mocked test fixtures as AI-generated runtime analysis.

## API regression and data preservation

`python3 scripts/verify-api.py`: exit 0, actual output:

```text
GET /actuator/health: HTTP 200
POST /api/incidents: HTTP 201
Created incident 3a69890d-cf82-48be-8c96-ef7e84251d2a, status=PENDING
GET /api/incidents/3a69890d-cf82-48be-8c96-ef7e84251d2a: HTTP 200
GET /api/incidents?page=0&size=20: HTTP 200
GET /api/incidents/3a69890d-cf82-48be-8c96-ef7e84251d2a/diagnosis: HTTP 404
GET /api/incidents/61365510-0334-4e45-94e9-85407e4de4fa: HTTP 404
GET /api/incidents/4969ec71-a755-40b0-8be9-9e5974b22183/diagnosis: HTTP 404
POST /api/incidents: HTTP 400
POST /api/incidents: HTTP 400
POST /api/incidents: HTTP 400
GET /api/incidents/not-a-uuid: HTTP 400
GET /api/incidents?size=101: HTTP 400
All 12 HTTP checks passed; synthetic incident retained.
```

The newly created incident's diagnosis may return 404 before async processing and 200 afterward; the smoke check accepts that race and validates mode when available.

Container psql confirmed all five Flyway versions succeeded, original legacy diagnosis 14cbca3b-e7a5-4298-8c03-5ebd7072ddcb retained summary “Synthetic verification fixture; not AI-generated” with mode LEGACY, prior retrieval milestone snapshots remained at five rows, and the corpus remained at 60 chunks. Existing data, PostgreSQL/Kafka settings and named volumes were preserved. No historical receipts were reprocessed/backfilled. No Git commit or push was performed for this continuation.

## Limits

Citation validation proves filenames belong to supplied evidence; it does not prove a model's hypothesis is semantically correct. Generated suggestions require human review and are never executed. DIAGNOSED does not imply RESOLVED. Previously processed receipts without diagnoses are not automatically regenerated. Quarantined events require explicit investigation/replay; old failure rows remain as evidence after recovery. The monitoring profile and frontend were not tested here.

Protocol references: [Ollama structured-output format](https://github.com/ollama/ollama/blob/main/docs/api.md), [LangChain output parsers](https://reference.langchain.com/python/langchain-core/output_parsers).

## Additional pipeline regression check

`python3 scripts/verify-event-flow.py`: exit 0 after the diagnosis extension. It again verified real publication/retrieval, duplicate snapshot preservation and malformed-event quarantine:

```text
POST: HTTP 201, incidentId=c4caf7b0-1a8e-47b7-8080-55cd1514914e, status=PENDING
GET: HTTP 200, status=RECEIVED
Persisted retrievals: [{"rank": 1, "source": "database-failures.md", "similarity": 0.626293}, {"rank": 2, "source": "database-failures.md", "similarity": 0.623596}, {"rank": 3, "source": "database-failures.md", "similarity": 0.620694}, {"rank": 4, "source": "database-failures.md", "similarity": 0.602883}, {"rank": 5, "source": "database-failures.md", "similarity": 0.593764}]
Outbox published: eventId=da868bea-5a26-4be9-8379-6e3ec0afd145, attempts=1; durable receipts=1
Kafka observed: topic=incident.created, offset=10, matching JSON contract
Duplicate offset=11: one receipt, incident timestamp unchanged
Malformed offset=12: original bytes durably quarantined; group offset=13
Full event flow, five persisted retrievals, duplicate delivery and malformed-record checks passed
```

Three new synthetic incidents from the RAG/API/pipeline checks remain: 9b59df94-6d6c-4537-b6cc-4111fd94bc8c, 3a69890d-cf82-48be-8c96-ef7e84251d2a and c4caf7b0-1a8e-47b7-8080-55cd1514914e. A new deliberately malformed pipeline record remains at partition 0 offset 12 as durable verification evidence. Final `docker compose config --quiet` and `git diff --check` both passed.
