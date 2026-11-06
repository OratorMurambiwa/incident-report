# Local operational runbooks

Ten original Markdown guides cover PostgreSQL failures, HTTP 500s, high latency, memory exhaustion, CPU saturation, Kafka lag, disk exhaustion, downstream timeouts, authentication and deployment failures. Each includes symptoms, diagnostics, mitigation, verification and follow-up. Adapt commands to the specific service; retrieved content is context, not an automated remediation instruction.

README.md is excluded from indexing. Real ingestion is implemented in worker/ingest.py using LangChain Markdown/token-aware splitters and pinned local all-MiniLM-L6-v2 embeddings. The ten current files produce 60 chunks. The Docker image contains the model; runtime is offline. Source files are mounted read-only.

```bash
docker compose exec worker python ingest.py /runbooks
docker compose exec worker python retrieval.py "PostgreSQL connection pool exhausted"
```

Unchanged files are skipped, changed files replace their own chunks atomically, and filenames are unique. Removing a file does not automatically delete an indexed source; remove obsolete sources deliberately after reviewing retention needs. Previously retrieved incident snapshots survive source updates.
