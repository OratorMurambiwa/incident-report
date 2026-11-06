import json
import os
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest

from main import EventConflict, connect_db, process_event, quarantine
from test_worker import event

pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "true", reason="requires isolated PostgreSQL test database")


@pytest.fixture
def incident():
    payload = event()
    with connect_db() as conn:
        conn.execute("INSERT INTO incidentiq_api.incidents (id, service, title, description, severity) VALUES (%s,%s,%s,%s,%s)",
                     (payload["incidentId"], "billing", "Timeout", "Details", "HIGH"))
    yield payload
    with connect_db() as conn:
        conn.execute("DELETE FROM incidentiq_api.diagnoses WHERE incident_id = %s", (payload["incidentId"],))
        conn.execute("DELETE FROM incidentiq_api.processed_events WHERE incident_id = %s", (payload["incidentId"],))
        conn.execute("DELETE FROM incidentiq_api.incidents WHERE id = %s", (payload["incidentId"],))


def test_atomic_receipt_and_duplicate_preserves_later_status(incident):
    assert process_event(incident) is True
    with connect_db() as conn:
        assert conn.execute("SELECT status FROM incidentiq_api.incidents WHERE id = %s", (incident["incidentId"],)).fetchone()[0] == "RECEIVED"
        conn.execute("UPDATE incidentiq_api.incidents SET status='RESOLVED' WHERE id = %s", (incident["incidentId"],))
    assert process_event(incident) is False
    with connect_db() as conn:
        assert conn.execute("SELECT status FROM incidentiq_api.incidents WHERE id = %s", (incident["incidentId"],)).fetchone()[0] == "RESOLVED"
        assert conn.execute("SELECT count(*) FROM incidentiq_api.processed_events WHERE event_id = %s", (incident["eventId"],)).fetchone()[0] == 1


def test_reused_id_different_payload_rejected(incident):
    process_event(incident)
    with pytest.raises(EventConflict):
        process_event(dict(incident, title="Different"))


def test_missing_incident_rolls_back_receipt():
    payload = event()
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        process_event(payload)
    with connect_db() as conn:
        assert conn.execute("SELECT count(*) FROM incidentiq_api.processed_events WHERE event_id=%s", (payload["eventId"],)).fetchone()[0] == 0


@pytest.mark.parametrize("raw", [b"{broken-json", None])
def test_malformed_record_retained_byte_for_byte(raw):
    record = SimpleNamespace(topic="pytest-" + str(uuid4()), partition=0, offset=1, value=raw)
    try:
        quarantine(record, "InvalidEvent", 1)
        with connect_db() as conn:
            stored = conn.execute("SELECT payload FROM incidentiq_api.failed_events WHERE topic=%s", (record.topic,)).fetchone()[0]
            assert (bytes(stored) if stored is not None else None) == record.value
    finally:
        with connect_db() as conn:
            conn.execute("DELETE FROM incidentiq_api.failed_events WHERE topic=%s", (record.topic,))


def test_persists_five_retrievals_with_receipt_and_preserves_on_duplicate(incident):
    process_event(incident)
    with connect_db() as conn:
        rows = conn.execute("SELECT rank, chunk_id, source, content, similarity, retrieved_at FROM incidentiq_api.incident_retrievals WHERE event_id=%s ORDER BY rank", (incident["eventId"],)).fetchall()
    assert [row[0] for row in rows] == [1, 2, 3, 4, 5]
    assert all(row[1] and row[2].endswith(".md") and row[3] and -1.000001 <= row[4] <= 1.000001 for row in rows)
    assert process_event(incident) is False
    with connect_db() as conn:
        replayed = conn.execute("SELECT rank, chunk_id, source, content, similarity, retrieved_at FROM incidentiq_api.incident_retrievals WHERE event_id=%s ORDER BY rank", (incident["eventId"],)).fetchall()
    assert rows == replayed


def test_retrieval_failure_rolls_back_receipt_and_status(incident):
    from unittest.mock import Mock
    with pytest.raises(RuntimeError):
        process_event(incident, retrieve=Mock(side_effect=RuntimeError("retrieval unavailable")))
    with connect_db() as conn:
        assert conn.execute("SELECT count(*) FROM incidentiq_api.processed_events WHERE event_id=%s", (incident["eventId"],)).fetchone()[0] == 0
        assert conn.execute("SELECT status FROM incidentiq_api.incidents WHERE id=%s", (incident["incidentId"],)).fetchone()[0] == "PENDING"
        assert conn.execute("SELECT count(*) FROM incidentiq_api.incident_retrievals WHERE event_id=%s", (incident["eventId"],)).fetchone()[0] == 0


def test_none_persists_labeled_diagnosis_with_no_generated_sections(incident):
    process_event(incident)
    with connect_db() as conn:
        row = conn.execute("SELECT mode, provider, model, likely_causes, investigation_steps, suggested_remediation, retrieved_evidence, event_id FROM incidentiq_api.diagnoses WHERE incident_id=%s", (incident["incidentId"],)).fetchone()
    assert row[:3] == ("RETRIEVAL_ONLY", "none", None)
    assert row[3:6] == ([], [], [])
    assert len(row[6]) == 5 and str(row[7]) == incident["eventId"]


def test_mocked_ollama_persists_structured_diagnosis_and_diagnosed_status(incident):
    from diagnosis import generate_diagnosis, LlmSettings
    from test_diagnosis import response
    def diagnose(event, documents):
        return generate_diagnosis(event, documents, LlmSettings("ollama", "test-model"), lambda _: json.dumps(response()))
    # Ensure cited source occurs in the actual retrieved test evidence.
    incident.update(title="PostgreSQL connection pool exhausted", description="Too many clients SQLSTATE 08006")
    process_event(incident, diagnose=diagnose)
    with connect_db() as conn:
        row = conn.execute("SELECT mode, provider, model, cited_runbooks, likely_causes FROM incidentiq_api.diagnoses WHERE incident_id=%s", (incident["incidentId"],)).fetchone()
        assert conn.execute("SELECT status FROM incidentiq_api.incidents WHERE id=%s", (incident["incidentId"],)).fetchone()[0] == "DIAGNOSED"
    assert row[:4] == ("GENERATED", "ollama", "test-model", ["database-failures.md"])
    assert row[4][0]["sources"] == ["database-failures.md"]


def test_duplicate_does_not_regenerate_or_overwrite_diagnosis(incident):
    from prometheus_client import REGISTRY
    metric = "incidentiq_worker_diagnoses_total"
    labels = {"outcome": "success", "mode": "retrieval_only"}
    baseline = REGISTRY.get_sample_value(metric, labels)
    from unittest.mock import Mock
    process_event(incident)
    with connect_db() as conn:
        before = conn.execute("SELECT id, mode, retrieved_evidence, created_at FROM incidentiq_api.diagnoses WHERE incident_id=%s", (incident["incidentId"],)).fetchone()
    llm = Mock(side_effect=AssertionError("duplicate must not regenerate"))
    assert process_event(incident, diagnose=llm) is False
    llm.assert_not_called()
    with connect_db() as conn:
        after = conn.execute("SELECT id, mode, retrieved_evidence, created_at FROM incidentiq_api.diagnoses WHERE incident_id=%s", (incident["incidentId"],)).fetchone()
    assert before == after
    assert REGISTRY.get_sample_value(metric, labels) == baseline + 1


def test_unavailable_model_rolls_back_then_quarantines_and_marks_failed(incident):
    from unittest.mock import Mock
    import threading
    from main import handle_record, Settings
    from diagnosis import ModelUnavailable
    from prometheus_client import REGISTRY
    metric = "incidentiq_worker_diagnoses_total"
    labels = {"outcome": "failure", "mode": "retrieval_only"}
    baseline = REGISTRY.get_sample_value(metric, labels)
    generator = Mock(side_effect=ModelUnavailable("missing model"))
    process = lambda event: process_event(event, diagnose=generator)
    record = SimpleNamespace(topic="pytest-" + str(uuid4()), partition=0, offset=1, value=json.dumps(incident).encode())
    consumer = Mock()
    try:
        handle_record(record, consumer, Settings(retry_seconds=0), threading.Event(), process=process)
        assert generator.call_count == 3
        assert REGISTRY.get_sample_value(metric, labels) == baseline + 1
        consumer.commit.assert_called_once()
        with connect_db() as conn:
            assert conn.execute("SELECT count(*) FROM incidentiq_api.processed_events WHERE event_id=%s", (incident["eventId"],)).fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM incidentiq_api.incident_retrievals WHERE event_id=%s", (incident["eventId"],)).fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM incidentiq_api.diagnoses WHERE incident_id=%s", (incident["incidentId"],)).fetchone()[0] == 0
            assert conn.execute("SELECT status FROM incidentiq_api.incidents WHERE id=%s", (incident["incidentId"],)).fetchone()[0] == "FAILED"
            assert conn.execute("SELECT error_code FROM incidentiq_api.failed_events WHERE topic=%s", (record.topic,)).fetchone()[0] == "ModelUnavailable"
        # Once configuration is repaired, unchanged manual replay can process a FAILED incident.
        assert process_event(incident) is True
    finally:
        with connect_db() as conn:
            conn.execute("DELETE FROM incidentiq_api.failed_events WHERE topic=%s", (record.topic,))


def test_alert_resolved_before_worker_arrival_is_not_reopened(incident):
    with connect_db() as conn:
        conn.execute("UPDATE incidentiq_api.incidents SET status='RESOLVED' WHERE id=%s", (incident["incidentId"],))
    assert process_event(incident) is True
    with connect_db() as conn:
        assert conn.execute("SELECT status FROM incidentiq_api.incidents WHERE id=%s", (incident["incidentId"],)).fetchone()[0] == "RESOLVED"
        assert conn.execute("SELECT count(*) FROM incidentiq_api.diagnoses WHERE incident_id=%s", (incident["incidentId"],)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM incidentiq_api.incident_retrievals WHERE event_id=%s", (incident["eventId"],)).fetchone()[0] == 5
