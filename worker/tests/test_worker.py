import json
import threading
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from main import (EventConflict, InvalidEvent, Settings, handle_record, process_event,
                  quarantine, validate_event)


def event():
    return {"schemaVersion": 1, "eventId": str(uuid4()), "incidentId": str(uuid4()),
            "service": "billing", "title": "Timeout", "description": "Details",
            "severity": "HIGH", "timestamp": "2026-11-05T18:00:00Z"}


def record(raw=None):
    return SimpleNamespace(topic="incident.created", partition=0, offset=7,
                           value=raw if raw is not None else json.dumps(event()).encode())


def test_valid_event():
    payload = event()
    assert validate_event(json.dumps(payload).encode()) == payload


@pytest.mark.parametrize("raw", [None, b"{", b"null", b"[]", b'{}', b'\xff'])
def test_invalid_json_or_fields(raw):
    with pytest.raises(InvalidEvent):
        validate_event(raw)


@pytest.mark.parametrize("field,value", [("eventId", "bad"), ("severity", "URGENT"),
                                         ("timestamp", "2026-11-05"), ("schemaVersion", True),
                                         ("service", " "), ("title", "x" * 201)])
def test_invalid_contract(field, value):
    payload = event()
    payload[field] = value
    with pytest.raises(InvalidEvent):
        validate_event(json.dumps(payload).encode())


def test_commit_only_after_durable_process_and_only_current_offset():
    consumer, process, retain = Mock(), Mock(return_value=True), Mock()
    order = []
    process.side_effect = lambda _: order.append("durable") or True
    consumer.commit.side_effect = lambda _: order.append("commit")
    handle_record(record(), consumer, Settings(), threading.Event(), process, retain)
    assert order == ["durable", "commit"]
    offsets = consumer.commit.call_args.args[0]
    assert len(offsets) == 1
    assert next(iter(offsets.values())).offset == 8
    retain.assert_not_called()


def test_duplicate_is_committed_without_reprocessing_status():
    process, consumer = Mock(return_value=False), Mock()
    handle_record(record(), consumer, Settings(), threading.Event(), process, Mock())
    consumer.commit.assert_called_once()


def test_transient_database_failure_retries_before_commit():
    process = Mock(side_effect=[RuntimeError(), True])
    consumer, retain = Mock(), Mock()
    handle_record(record(), consumer, Settings(retry_seconds=0), threading.Event(), process, retain)
    assert process.call_count == 2
    consumer.commit.assert_called_once()
    retain.assert_not_called()


def test_exhausted_failures_retained_before_commit():
    process, consumer, retain = Mock(side_effect=RuntimeError()), Mock(), Mock()
    order = []
    retain.side_effect = lambda *_: order.append("durable_failure")
    consumer.commit.side_effect = lambda *_: order.append("commit")
    handle_record(record(), consumer, Settings(retry_seconds=0), threading.Event(), process, retain)
    assert process.call_count == 3
    assert order == ["durable_failure", "commit"]


def test_malformed_retained_before_commit():
    process, consumer, retain = Mock(), Mock(), Mock()
    handle_record(record(b"{"), consumer, Settings(), threading.Event(), process, retain)
    retain.assert_called_once()
    process.assert_not_called()
    consumer.commit.assert_called_once()


def test_quarantine_database_failure_does_not_commit():
    consumer = Mock()
    with pytest.raises(RuntimeError):
        handle_record(record(b"{"), consumer, Settings(), threading.Event(), Mock(),
                      Mock(side_effect=RuntimeError("db unavailable")))
    consumer.commit.assert_not_called()


def test_offset_commit_failure_propagates_for_safe_replay():
    consumer = Mock()
    consumer.commit.side_effect = RuntimeError("rebalance")
    with pytest.raises(RuntimeError):
        handle_record(record(), consumer, Settings(), threading.Event(), Mock(return_value=True), Mock())


def test_shutdown_during_retry_does_not_commit():
    stopped = threading.Event()
    stopped.set()
    consumer = Mock()
    handle_record(record(), consumer, Settings(), stopped, Mock(side_effect=RuntimeError()), Mock())
    consumer.commit.assert_not_called()


@contextmanager
def fake_connection(cursor):
    connection = Mock()
    connection.cursor.return_value.__enter__ = Mock(return_value=cursor)
    connection.cursor.return_value.__exit__ = Mock(return_value=False)
    yield connection


def test_duplicate_receipt_does_not_update_status():
    payload = event()
    import hashlib
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    cursor = Mock()
    cursor.fetchone.side_effect = [None, (payload["incidentId"], digest)]
    assert process_event(payload, lambda: fake_connection(cursor)) is False
    assert cursor.execute.call_count == 2


def test_conflicting_event_id_is_detected():
    payload = event()
    cursor = Mock()
    cursor.fetchone.side_effect = [None, (payload["incidentId"], "different")]
    with pytest.raises(EventConflict):
        process_event(payload, lambda: fake_connection(cursor))


def test_processing_exception_propagates_before_commit():
    cursor = Mock()
    cursor.execute.side_effect = RuntimeError("db unavailable")
    with pytest.raises(RuntimeError):
        process_event(event(), lambda: fake_connection(cursor))
