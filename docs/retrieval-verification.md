> Historical milestone snapshot: capability/version statements and counts below describe that run. See the [current overview](../README.md) and [latest application/security regression](security/VERIFICATION.md) for subsequent implementation and verification.

# Local retrieval verification — 2026-11-05 (America/Chicago)

## Implemented and preserved

Read AGENTS.md, worker processing/deduplication/offset code, migrations and Compose before implementation. Added ten original detailed runbooks (3,763 words), LangChain Markdown/token-aware splitting, normalized CPU embeddings, a LangChain BaseRetriever using pgvector exact cosine search, and atomic worker retrieval snapshots. Added Flyway V4; V1–V3 remain unchanged. Existing API endpoints, outbox/publisher, Kafka topics/settings and named Docker volumes were preserved. PostgreSQL remains on host port 55432.

The model is sentence-transformers/all-MiniLM-L6-v2 revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf. CPU torch 2.6.0+cpu, sentence-transformers 3.4.1, transformers 4.48.3, LangChain 0.3.27/core 0.3.86 and other direct dependencies are pinned. requirements.lock was generated using pip freeze from the resolved Docker environment and is used as pip constraints. pip check passed in the build and running worker. The model was downloaded into the image, not called through a hosted inference service.

## Actual commands and results

- `docker compose config --quiet`: exit 0, including final validation.
- `docker build --target dependencies -t incidentiq-worker-dependencies:local ./worker`: exit 0; installed CPU dependencies, downloaded pinned public model and encoded a real 384-dimensional vector in offline mode.
- `docker compose build api` and `docker compose build worker`: exit 0. Final worker ordinary image build ran 24 unit cases successfully and explicitly skipped 13 database/model integration cases; those cases ran separately below. A non-root Hugging Face cache-directory warning in the first runtime image was fixed by creating the worker home directory. No warning remains in the final model smoke check.
- `docker compose up -d --wait api publisher worker`: exit 0. Flyway V4 applied; runbook-ingest completed before worker startup. API, PostgreSQL, Kafka and worker healthy; publisher running; kafka-init and runbook-ingest exited 0.

Initial runbook-ingest output:

```json
{"changed": 10, "chunks_written": 60, "files": 10, "skipped": 0}
```

`docker compose exec -T worker python ingest.py /runbooks` repeated safely, exit 0:

```json
{"changed": 0, "chunks_written": 0, "files": 10, "skipped": 10}
```

Container psql confirmed 10 documents, total declared chunk_count 60, 60 stored chunks and 60 distinct chunk UUIDs. Each runbook produced six section chunks. Tests also checked identical IDs/counts after repeated ingestion and changed-file replacement without duplicate sources.

- `./scripts/test-api.sh`: exit 0; original API/outbox regression suite using PostgreSQL:

```text
Tests run: 32, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

- `./scripts/test-worker.sh`: exit 0. Script indexed the isolated incidentiq_api_test database before running all tests:

```text
37 passed in 3.71s
```

This comprises 24 unit and 13 database/model integration cases. Original worker coverage remains, including validation, duplicates, event conflicts, retry/quarantine and offset ordering. New cases use the actual local model and PostgreSQL, covering four incident-type relevance queries, idempotent ingestion, changed-file replacement, five persisted source/content/score snapshots, unchanged snapshots on duplicate delivery and rollback of receipt/status/context on retrieval failure. Relevance asserts expected source among top three, descending scores and similarity above 0.3; the separate real queries below actually ranked each expected source first.

## Actual retrieval queries

Executed inside the running worker using PgRunbookRetriever.invoke, the actual local model, and PostgreSQL (no mock embeddings):

| Incident type | Top source | Cosine similarity |
|---|---|---|
| database | database-failures.md | 0.665092 |
| kafka | kafka-lag.md | 0.782005 |
| memory | memory-exhaustion.md | 0.480460 |
| authentication | authentication-failures.md | 0.483740 |

Queries:

1. PostgreSQL rejects connections with too many clients; connection pool exhausted and SQLSTATE 08006.
2. Kafka consumer lag is growing: committed offsets stopped advancing while log end offsets increase.
3. Container was OOMKilled with exit code 137, rising RSS and Java OutOfMemoryError.
4. API returns HTTP 401 because the bearer JWT expired or its signature verification failed.

All queries returned five chunks. Cosine similarity is not a confidence probability. Database and Kafka examples returned five different sections of their respective expected runbook; memory/authentication examples also included lower-ranking neighboring topics.

## Real HTTP → Kafka → retrieval persistence

`python3 scripts/verify-event-flow.py`: exit 0. Actual output:

```text
POST: HTTP 201, incidentId=ed1ed38e-9379-47c4-abd8-1813ae521e26, status=PENDING
GET: HTTP 200, status=RECEIVED
Persisted retrievals: [{"rank": 1, "source": "database-failures.md", "similarity": 0.626293}, {"rank": 2, "source": "database-failures.md", "similarity": 0.623596}, {"rank": 3, "source": "database-failures.md", "similarity": 0.620694}, {"rank": 4, "source": "database-failures.md", "similarity": 0.602883}, {"rank": 5, "source": "database-failures.md", "similarity": 0.593764}]
Outbox published: eventId=9480a174-1cad-4099-acda-4e51147c92f4, attempts=1; durable receipts=1
Kafka observed: topic=incident.created, offset=4, matching JSON contract
Duplicate offset=5: one receipt, incident timestamp unchanged
Malformed offset=6: original bytes durably quarantined; group offset=7
Full event flow, five persisted retrievals, duplicate delivery and malformed-record checks passed
```

The script asserted five persisted source/content/score records, found the matching event on Kafka, then replayed it and checked the entire retrieval snapshot set stayed unchanged. One new synthetic incident and its five snapshot records remain. A synthetic malformed message at incident.created partition 0 offset 6 remains in durable quarantine as verification evidence.

Container psql additionally confirmed V1/V2/V3/V4 success, five snapshot rows for the new incident, 60 corpus chunks and preservation of two prior milestone incident IDs. No volumes or existing application rows were deleted. The legacy public.runbook_chunks table was not modified.

- `docker compose exec -T worker python -m pip check`: `No broken requirements found.`
- `docker run --rm --network none --entrypoint python incidentiq-worker:local -c ...`: exit 0 and `Offline CPU embedding dimensions: 384`. This proves embedding inference works without any network access.

## Practical limits

Runtime embedding inference is offline; downloading open-source packages/model weights requires internet during image build. The corpus is small, so vector search is exact rather than approximate. Five chunks need not come from five different files. Long incident queries are subject to the model context window. Removed runbook files are not automatically deleted from the index; updates to present files are handled atomically. Retrieved snapshots survive later re-ingestion.

Prior processed event receipts are not backfilled or implicitly reprocessed. New events retrieve before committing their receipt/status. Retrieval failures follow the existing bounded retry/durable-quarantine path. Diagnosis generation, LLM calls, a retrieved-context REST endpoint and frontend integration were not added. Monitoring profile was not started/tested in this continuation. No cloud resources, remote repository, paid services or host package installations were used.

References: [official model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [SentenceTransformer local loading/encode](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html), [LangChain retriever interface](https://reference.langchain.com/python/langchain-core/retrievers/BaseRetriever).
