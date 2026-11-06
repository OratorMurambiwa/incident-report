"""Actual local model + pgvector tests. No fake vectors or keyword-based retrieval."""
import os
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest

from db import connect_db
from ingest import ingest
from model import LocalEmbeddings
from retrieval import PgRunbookRetriever

pytestmark = pytest.mark.skipif(os.getenv("RUN_RETRIEVAL_TESTS") != "true",
                               reason="requires indexed PostgreSQL corpus and local model")


@pytest.mark.parametrize("query,expected", [
    ("PostgreSQL rejects connections with too many clients; connection pool exhausted and SQLSTATE 08006.", "database-failures.md"),
    ("Kafka consumer lag is growing: committed offsets stopped advancing while log end offsets increase.", "kafka-lag.md"),
    ("Container was OOMKilled with exit code 137, rising RSS and Java OutOfMemoryError.", "memory-exhaustion.md"),
    ("API returns HTTP 401 because the bearer JWT expired or its signature verification failed.", "authentication-failures.md"),
])
def test_real_semantic_relevance(query, expected):
    with connect_db() as connection:
        docs = PgRunbookRetriever(connection=connection, embeddings=LocalEmbeddings()).invoke(query)
    assert len(docs) == 5
    assert expected in [doc.metadata["source"] for doc in docs[:3]]
    scores = [doc.metadata["similarity"] for doc in docs]
    assert scores == sorted(scores, reverse=True)
    assert max(d.metadata["similarity"] for d in docs if d.metadata["source"] == expected) > 0.3
    assert all(d.page_content and d.metadata["chunk_id"] for d in docs)


def test_rerunning_ingestion_preserves_chunk_ids_and_counts():
    with connect_db() as connection:
        before = connection.execute("SELECT id FROM incidentiq_api.runbook_chunks ORDER BY id").fetchall()
    first = ingest(Path("/runbooks"))
    second = ingest(Path("/runbooks"))
    assert first["changed"] == second["changed"] == 0
    assert first["skipped"] == second["skipped"] == 10
    with connect_db() as connection:
        after = connection.execute("SELECT id FROM incidentiq_api.runbook_chunks ORDER BY id").fetchall()
    assert before == after


def test_changed_file_replaces_its_chunks_without_duplication(tmp_path):
    filename = "pytest-" + str(uuid4()) + ".md"
    path = tmp_path / filename
    path.write_text("# Database failure\n\n## Symptoms\nPostgreSQL connection pool exhausted.")
    try:
        assert ingest(tmp_path)["changed"] == 1
        with connect_db() as connection:
            before = connection.execute("SELECT c.id FROM incidentiq_api.runbook_chunks c JOIN incidentiq_api.runbook_documents d ON d.id=c.document_id WHERE d.source=%s", (filename,)).fetchall()
        path.write_text("# Database failure\n\n## Symptoms\nPostgreSQL server refused database connections after a deployment.")
        assert ingest(tmp_path)["changed"] == 1
        with connect_db() as connection:
            after = connection.execute("SELECT c.id FROM incidentiq_api.runbook_chunks c JOIN incidentiq_api.runbook_documents d ON d.id=c.document_id WHERE d.source=%s", (filename,)).fetchall()
            assert connection.execute("SELECT count(*) FROM incidentiq_api.runbook_documents WHERE source=%s", (filename,)).fetchone()[0] == 1
        assert after and not set(before).intersection(after)
    finally:
        with connect_db() as connection:
            connection.execute("DELETE FROM incidentiq_api.runbook_documents WHERE source=%s", (filename,))
