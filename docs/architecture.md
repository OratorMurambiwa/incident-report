# Architecture

Spring Boot creates incidents and outbox JSON atomically. The separate Java publisher delivers incident.created with broker acknowledgement. A Dockerized Python worker deduplicates event IDs, retrieves five runbook chunks with local CPU embeddings/pgvector and creates a structured diagnosis in the same PostgreSQL transaction as receipt, snapshot and status writes. Kafka offsets follow database durability.

Provider none stores RETRIEVAL_ONLY with original evidence and no generated analysis, leaving status RECEIVED. Optional local Ollama uses a LangChain prompt/runnable/parser, JSON-schema output and exact citation whitelists; successful generation sets DIAGNOSED. Retrieved/incident content is untrusted data; no tools or remediation execution exist. Failed model/evidence/output processing retries, then quarantines durably and marks pending incidents FAILED. Duplicate events never regenerate a diagnosis.

Flyway manages incidentiq_api. V1 incident/diagnosis tables; V2 outbox/receipts/failures; V3 Kafka tombstones; V4 runbook corpus/retrieval snapshots; V5 structured diagnosis/provenance and legacy labeling. public.runbook_chunks and prior data remain intact. GET diagnosis exposes both original fields and structured analysis/evidence/provenance. Snapshots survive corpus updates; historical receipts are not backfilled.

Future work: actual Ollama model validation in this environment, live React views, incidents.analyzed publication, additional operational alerts and richer frontend integration. Kafka remains one KRaft node, delivery at least once. See rag-verification.md for executed tests and mode-specific runtime evidence.

Observability is implemented with Actuator/Micrometer and prometheus_client. Prometheus scrapes Docker service addresses; Grafana provisions the incidentiq-overview dashboard. Metrics use bounded labels, database-backed incident gauges and committed/quarantined workflow outcomes. Monitoring volumes persist without replacing PostgreSQL/Kafka storage. See monitoring-verification.md.
