"""Shared PostgreSQL connection settings for worker, ingestion and retrieval."""
import os
import psycopg


def connect_db() -> psycopg.Connection:
    return psycopg.connect(host=os.getenv("POSTGRES_HOST", "localhost"),
                          port=int(os.getenv("POSTGRES_PORT", "55432")),
                          dbname=os.getenv("POSTGRES_DB", "incidentiq"),
                          user=os.getenv("POSTGRES_USER", "incidentiq"),
                          password=os.getenv("POSTGRES_PASSWORD", "incidentiq_local_only"),
                          connect_timeout=5, options="-c statement_timeout=10000")
