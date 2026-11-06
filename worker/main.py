"""Durable, idempotent incident.created consumer. Retrieval-only or local Ollama RAG diagnoses are persisted atomically."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import signal
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from db import connect_db
from metrics import PROCESSING_DURATION, RETRIEVAL_DURATION, diagnosis_committed, diagnosis_quarantined
from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from prometheus_client import Counter, start_http_server

LOG = logging.getLogger("incidentiq.worker")
PROCESSED = Counter("incidentiq_worker_processed_total", "Durably processed records")
QUARANTINED = Counter("incidentiq_worker_quarantined_total", "Durably quarantined records")


class InvalidEvent(ValueError):
    """Invalid wire contract; retain original bytes for review."""


class EventConflict(ValueError):
    """The same event ID was reused for a different payload."""


@dataclass(frozen=True)
class Settings:
    bootstrap_servers: str = "localhost:9092"
    group_id: str = "incidentiq-worker-v1"
    topic: str = "incident.created"
    max_attempts: int = 3
    retry_seconds: float = 1.0

    @classmethod
    def from_env(cls) -> Settings:
        return cls(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                   group_id=os.getenv("KAFKA_GROUP_ID", "incidentiq-worker-v1"))




def validate_event(raw: bytes) -> dict[str, Any]:
    try:
        event = json.loads(raw)
        fields = {"schemaVersion", "eventId", "incidentId", "service", "title",
                  "description", "severity", "timestamp"}
        if not isinstance(event, dict) or set(event) != fields:
            raise InvalidEvent("fields")
        if type(event["schemaVersion"]) is not int or event["schemaVersion"] != 1:
            raise InvalidEvent("schema_version")
        for name in ("eventId", "incidentId"):
            if not isinstance(event[name], str):
                raise InvalidEvent("uuid")
            event[name] = str(UUID(event[name]))
        for name, limit in (("service", 100), ("title", 200), ("description", 10000)):
            if not isinstance(event[name], str) or not event[name].strip() or len(event[name]) > limit:
                raise InvalidEvent(name)
        if event["severity"] not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise InvalidEvent("severity")
        timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise InvalidEvent("timestamp_timezone")
        return event
    except (ValueError, TypeError, AttributeError, UnicodeError) as error:
        # Never propagate payload-bearing JSON parser errors into logs or failure metadata.
        raise InvalidEvent("invalid_event") from error


def process_event(event: dict[str, Any], connect: Callable = connect_db, retrieve: Callable | None = None,
                  diagnose: Callable | None = None) -> bool:
    """Receipt, retrievals, diagnosis and status commit together. Return False for replay."""
    digest = hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO incidentiq_api.processed_events (event_id, incident_id, payload_hash)
                VALUES (%s, %s, %s) ON CONFLICT (event_id) DO NOTHING RETURNING event_id
                """, (event["eventId"], event["incidentId"], digest))
            if cursor.fetchone() is None:
                cursor.execute("SELECT incident_id, payload_hash FROM incidentiq_api.processed_events WHERE event_id = %s",
                               (event["eventId"],))
                previous = cursor.fetchone()
                if previous is None or str(previous[0]) != event["incidentId"] or previous[1] != digest:
                    raise EventConflict("event_id_conflict")
                return False
            from retrieval import retrieve_incident, persist_retrievals
            with RETRIEVAL_DURATION.time():
                documents = (retrieve or retrieve_incident)(event, connection)
            from diagnosis import generate_diagnosis, persist_diagnosis, MissingEvidence
            if len(documents) != 5:
                raise MissingEvidence("Runbook corpus must supply five retrieval results")
            persist_retrievals(cursor, event, documents)
            result = (diagnose or generate_diagnosis)(event, documents)
            persist_diagnosis(cursor, event, result)
            target_status = "DIAGNOSED" if result["mode"] == "GENERATED" else "RECEIVED"
            # Do not regress externally advanced/resolved incidents. Failed RAG events may be replayed.
            cursor.execute("""
                UPDATE incidentiq_api.incidents SET status = %s, updated_at = GREATEST(now(), updated_at)
                WHERE id = %s AND status IN ('PENDING', 'FAILED')
                """, (target_status, event["incidentId"]))
    diagnosis_committed(result["mode"])  # after PostgreSQL context exit/commit; replay returns above
    return True


def quarantine(record: Any, error_code: str, attempts: int, connect: Callable = connect_db) -> None:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO incidentiq_api.failed_events (topic, partition_id, offset_id, payload, error_code, attempts)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (topic, partition_id, offset_id) DO UPDATE
                SET attempts = failed_events.attempts + EXCLUDED.attempts, error_code = EXCLUDED.error_code
                """, (record.topic, record.partition, record.offset, record.value, error_code, attempts))
            if error_code in {"ModelUnavailable", "InvalidDiagnosis", "MissingEvidence"}:
                try:
                    event = validate_event(record.value)
                except InvalidEvent:
                    pass
                else:
                    cursor.execute("""
                        UPDATE incidentiq_api.incidents SET status = 'FAILED', updated_at = GREATEST(now(), updated_at)
                        WHERE id = %s AND status IN ('PENDING', 'ANALYZING')
                        AND NOT EXISTS (SELECT 1 FROM incidentiq_api.processed_events WHERE event_id = %s)
                        """, (event["incidentId"], event["eventId"]))
    # A durable workflow failure is counted once per handling; malformed/conflicting records are separate.
    try:
        validate_event(record.value)
    except InvalidEvent:
        pass
    else:
        if error_code != "EventConflict":
            diagnosis_quarantined()
    QUARANTINED.inc()
    LOG.error(json.dumps({"action": "quarantined", "topic": record.topic, "partition": record.partition,
                          "offset": record.offset, "error": error_code, "attempts": attempts}))


@PROCESSING_DURATION.time()
def handle_record(record: Any, consumer: Any, settings: Settings, stopped: threading.Event,
                  process: Callable = process_event, retain: Callable = quarantine) -> None:
    try:
        event = validate_event(record.value)
    except InvalidEvent:
        retain(record, "InvalidEvent", 1)
    else:
        for attempt in range(1, settings.max_attempts + 1):
            try:
                changed = process(event)
                PROCESSED.inc()
                LOG.info(json.dumps({"action": "processed" if changed else "duplicate",
                                     "eventId": event["eventId"], "incidentId": event["incidentId"]}))
                break
            except Exception as error:
                code = type(error).__name__
                LOG.warning(json.dumps({"action": "retry", "eventId": event["eventId"],
                                        "attempt": attempt, "error": code}))
                if isinstance(error, EventConflict) or attempt == settings.max_attempts:
                    retain(record, code, attempt)
                    break
                if stopped.wait(settings.retry_seconds * attempt):
                    return  # Interrupted before durable handling: leave offset uncommitted.
    # Explicitly commit only this record's partition/offset, never a poll batch.
    # On commit failure, abort the process; replay is safe through processed_events.
    consumer.commit({TopicPartition(record.topic, record.partition): OffsetAndMetadata(record.offset + 1, "", -1)})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from diagnosis import LlmSettings
    LlmSettings.from_env()  # Reject unsupported providers/configuration before consuming offsets.
    from model import LocalEmbeddings
    LocalEmbeddings().embed_query("worker startup")
    settings = Settings.from_env()
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    consumer = KafkaConsumer(settings.topic, bootstrap_servers=settings.bootstrap_servers.split(","),
                             group_id=settings.group_id, enable_auto_commit=False,
                             auto_offset_reset="earliest", max_poll_records=1,
                             max_poll_interval_ms=300000, consumer_timeout_ms=1000)
    start_http_server(8001, addr="0.0.0.0")
    try:
        while not stopped.is_set():
            for record in consumer:
                if stopped.is_set():
                    break
                handle_record(record, consumer, settings, stopped)
    finally:
        consumer.close(autocommit=False)


if __name__ == "__main__":
    main()
