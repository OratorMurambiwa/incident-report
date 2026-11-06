"""LangChain retriever backed by exact pgvector cosine search."""
from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from model import LocalEmbeddings, MODEL_NAME, MODEL_REVISION


class PgRunbookRetriever(BaseRetriever):
    connection: Any
    embeddings: Embeddings
    k: int = 5
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        vector = json.dumps(self.embeddings.embed_query(query))
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.id, d.source, c.content,
                       1 - (c.embedding OPERATOR(public.<=>) %s::public.vector) AS similarity
                FROM incidentiq_api.runbook_chunks c
                JOIN incidentiq_api.runbook_documents d ON d.id = c.document_id
                WHERE d.model_name = %s AND d.model_revision = %s
                ORDER BY c.embedding OPERATOR(public.<=>) %s::public.vector, c.id
                LIMIT %s
                """, (vector, MODEL_NAME, MODEL_REVISION, vector, self.k))
            return [Document(page_content=row[2], metadata={
                "chunk_id": str(row[0]), "source": row[1], "similarity": float(row[3]),
                "model_name": MODEL_NAME, "model_revision": MODEL_REVISION
            }) for row in cursor.fetchall()]


def retrieve_incident(event: dict[str, Any], connection: Any) -> list[Document]:
    # Avoid cutting off the title when a long incident description exceeds the model window.
    query = f"Service: {event['service']}\n{event['title']}\n{event['description']}"
    return PgRunbookRetriever(connection=connection, embeddings=LocalEmbeddings()).invoke(query)


def persist_retrievals(cursor: Any, event: dict[str, Any], documents: list[Document]) -> None:
    for rank, doc in enumerate(documents, start=1):
        cursor.execute("""
            INSERT INTO incidentiq_api.incident_retrievals
                (event_id, incident_id, rank, chunk_id, source, content, similarity, model_name, model_revision)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (event["eventId"], event["incidentId"], rank, doc.metadata["chunk_id"],
                  doc.metadata["source"], doc.page_content, doc.metadata["similarity"], MODEL_NAME, MODEL_REVISION))


def main() -> None:
    import argparse
    from db import connect_db
    parser = argparse.ArgumentParser(description="Query local runbooks with cosine similarity")
    parser.add_argument("query")
    args = parser.parse_args()
    with connect_db() as connection:
        docs = PgRunbookRetriever(connection=connection, embeddings=LocalEmbeddings()).invoke(args.query)
    print(json.dumps([{"rank": rank, "source": doc.metadata["source"],
                       "similarity": round(doc.metadata["similarity"], 6),
                       "chunk_id": doc.metadata["chunk_id"], "content": doc.page_content}
                      for rank, doc in enumerate(docs, 1)], indent=2))


if __name__ == "__main__":
    main()
