"""Atomic, content-addressed Markdown ingestion with real local embeddings."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from db import connect_db
from model import LocalEmbeddings, MODEL_NAME, MODEL_REVISION, get_model

CHUNKING_VERSION = "markdown-token180-overlap30-v1"


def chunks_for_file(path: Path) -> list[Document]:
    text = path.read_text(encoding="utf-8")
    headings = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "title"), ("##", "section")])
    sections = headings.split_text(text)
    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        get_model().tokenizer, chunk_size=180, chunk_overlap=30)
    chunks = splitter.split_documents(sections)
    for chunk in chunks:
        context = f"Runbook: {chunk.metadata.get('title', path.stem)}\nSection: {chunk.metadata.get('section', 'Overview')}\n"
        chunk.page_content = context + chunk.page_content
        chunk.metadata["source"] = path.name
        if len(get_model().tokenizer.encode(chunk.page_content)) > 256:
            raise ValueError("Chunk exceeds embedding model context window")
    return chunks


def ingest(directory: Path, connect=connect_db) -> dict[str, int]:
    paths = sorted(p for p in directory.glob("*.md") if p.name.lower() != "readme.md")
    if not paths:
        raise ValueError("No Markdown runbooks found")
    embeddings = LocalEmbeddings()
    stats = {"files": len(paths), "changed": 0, "skipped": 0, "chunks_written": 0}
    with connect() as connection:
        with connection.cursor() as cursor:
            # Serialize ingestion; readers see either the old or the new committed corpus.
            cursor.execute("SELECT pg_advisory_xact_lock(194757348)")
            for path in paths:
                text = path.read_text(encoding="utf-8")
                fingerprint = hashlib.sha256((text + MODEL_NAME + MODEL_REVISION + CHUNKING_VERSION).encode()).hexdigest()
                cursor.execute("""
                    SELECT d.fingerprint, d.chunk_count, count(c.id)
                    FROM incidentiq_api.runbook_documents d
                    LEFT JOIN incidentiq_api.runbook_chunks c ON c.document_id = d.id
                    WHERE d.source = %s GROUP BY d.id
                    """, (path.name,))
                existing = cursor.fetchone()
                if existing and existing[0] == fingerprint and existing[1] == existing[2]:
                    stats["skipped"] += 1
                    continue
                chunks = chunks_for_file(path)
                if not chunks:
                    raise ValueError(f"Empty runbook: {path.name}")
                vectors = embeddings.embed_documents([c.page_content for c in chunks])
                document_id = uuid5(NAMESPACE_URL, "incidentiq/runbooks/" + path.name)
                cursor.execute("""
                    INSERT INTO incidentiq_api.runbook_documents
                        (id, source, fingerprint, model_name, model_revision, chunk_count)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (source) DO UPDATE SET fingerprint=EXCLUDED.fingerprint,
                        model_name=EXCLUDED.model_name, model_revision=EXCLUDED.model_revision,
                        chunk_count=EXCLUDED.chunk_count, ingested_at=now()
                    """, (document_id, path.name, fingerprint, MODEL_NAME, MODEL_REVISION, len(chunks)))
                cursor.execute("DELETE FROM incidentiq_api.runbook_chunks WHERE document_id = %s", (document_id,))
                cursor.executemany("""
                    INSERT INTO incidentiq_api.runbook_chunks (id, document_id, chunk_index, content, embedding)
                    VALUES (%s,%s,%s,%s,%s::public.vector)
                    """, [(uuid5(document_id, fingerprint + ":" + str(index)), document_id, index,
                           chunk.page_content, json.dumps(vector))
                          for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))])
                stats["changed"] += 1
                stats["chunks_written"] += len(chunks)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("/runbooks"))
    args = parser.parse_args()
    print(json.dumps(ingest(args.directory), sort_keys=True))


if __name__ == "__main__":
    main()
