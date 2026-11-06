"""Bounded-label metrics. No event IDs, sources, model names, services or exception text."""
import os

from prometheus_client import Counter, Histogram

PROCESSING_DURATION = Histogram(
    "incidentiq_worker_processing_duration_seconds",
    "Consumed-record wall time including retries, durable handling and offset commit",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)
RETRIEVAL_DURATION = Histogram(
    "incidentiq_worker_rag_retrieval_duration_seconds",
    "Local query embedding plus pgvector retrieval time per attempt, including failures",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
DIAGNOSES = Counter(
    "incidentiq_worker_diagnoses_total",
    "Committed diagnoses or valid incident workflows durably quarantined after failure",
    ["outcome", "mode"],
)
for _outcome in ("success", "failure"):
    for _mode in ("retrieval_only", "generated"):
        DIAGNOSES.labels(outcome=_outcome, mode=_mode)  # expose explicit zeros before first event


def diagnosis_committed(mode: str) -> None:
    label = "generated" if mode == "GENERATED" else "retrieval_only"
    DIAGNOSES.labels(outcome="success", mode=label).inc()


def diagnosis_quarantined() -> None:
    label = "generated" if os.getenv("LLM_PROVIDER", "none") == "ollama" else "retrieval_only"
    DIAGNOSES.labels(outcome="failure", mode=label).inc()
