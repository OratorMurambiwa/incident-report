import threading
from unittest.mock import Mock

import pytest
from prometheus_client import REGISTRY

from main import Settings, handle_record, process_event
from metrics import DIAGNOSES, diagnosis_committed
from test_worker import event, record, fake_connection


@pytest.mark.parametrize("fails", [False, True])
def test_processing_duration_observes_success_and_exhausted_failure(fails):
    metric = "incidentiq_worker_processing_duration_seconds_count"
    before = REGISTRY.get_sample_value(metric)
    process = Mock(side_effect=RuntimeError()) if fails else Mock(return_value=True)
    handle_record(record(), Mock(), Settings(retry_seconds=0), threading.Event(), process, Mock())
    assert REGISTRY.get_sample_value(metric) == before + 1


def test_retrieval_failure_records_latency_without_successful_diagnosis():
    metric = "incidentiq_worker_rag_retrieval_duration_seconds_count"
    before = REGISTRY.get_sample_value(metric)
    success = REGISTRY.get_sample_value("incidentiq_worker_diagnoses_total", {"outcome": "success", "mode": "retrieval_only"})
    payload = event()
    cursor = Mock()
    cursor.fetchone.return_value = (payload["eventId"],)
    with pytest.raises(RuntimeError):
        process_event(payload, lambda: fake_connection(cursor), retrieve=Mock(side_effect=RuntimeError("unavailable")))
    assert REGISTRY.get_sample_value(metric) == before + 1
    assert REGISTRY.get_sample_value("incidentiq_worker_diagnoses_total", {"outcome": "success", "mode": "retrieval_only"}) == success


def test_outcome_labels_are_bounded_even_for_unexpected_mode_strings():
    diagnosis_committed("untrusted-model-or-incident-id")
    for sample in DIAGNOSES.collect()[0].samples:
        assert set(sample.labels) == {"outcome", "mode"}
        assert sample.labels["outcome"] in {"success", "failure"}
        assert sample.labels["mode"] in {"retrieval_only", "generated"}
