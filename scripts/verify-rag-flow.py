#!/usr/bin/env python3
"""Real HTTP/Kafka/database diagnosis verification; retains one synthetic incident."""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--expect-mode", choices=["RETRIEVAL_ONLY", "GENERATED"], default="RETRIEVAL_ONLY")
parser.add_argument("--base-url", default="http://127.0.0.1:8080")
args = parser.parse_args()
payload = {"service": "rag-smoke", "title": "Synthetic PostgreSQL connection pool exhaustion",
           "description": "PostgreSQL reports too many clients, connection pool exhausted, SQLSTATE 08006.",
           "severity": "HIGH"}
request = urllib.request.Request(args.base_url + "/api/incidents", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=15) as response:
    incident = json.load(response)
    assert response.status == 201 and incident["status"] == "PENDING"
incident_id = str(uuid.UUID(incident["id"]))
print(f"POST /api/incidents: HTTP 201, incidentId={incident_id}, status=PENDING", flush=True)
path = args.base_url + "/api/incidents/" + incident_id
for _ in range(120):
    try:
        with urllib.request.urlopen(path + "/diagnosis", timeout=10) as response:
            diagnosis = json.load(response)
            assert response.status == 200
            break
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    with urllib.request.urlopen(path, timeout=10) as response:
        if json.load(response)["status"] == "FAILED":
            raise AssertionError("Worker marked incident FAILED; inspect durable failed_events and provider configuration")
    time.sleep(1)
else:
    raise AssertionError("Diagnosis did not become available within 120 seconds")
assert diagnosis["incidentId"] == incident_id
assert diagnosis["mode"] == args.expect_mode
assert len(diagnosis["retrievedEvidence"]) == 5
sources = {entry["source"] for entry in diagnosis["retrievedEvidence"]}
assert diagnosis["citedRunbooks"] and set(diagnosis["citedRunbooks"]) <= sources
assert all(item["excerpt"] and item["chunkId"] for item in diagnosis["retrievedEvidence"])
if args.expect_mode == "RETRIEVAL_ONLY":
    assert diagnosis["provider"] == "none" and diagnosis["model"] is None
    assert diagnosis["summary"].startswith("RETRIEVAL_ONLY:")
    assert diagnosis["likelyCauses"] == diagnosis["investigationSteps"] == diagnosis["suggestedRemediation"] == []
    expected_status = "RECEIVED"
else:
    assert diagnosis["provider"] == "ollama" and diagnosis["model"]
    for name in ("likelyCauses", "investigationSteps", "suggestedRemediation"):
        assert diagnosis[name]
        assert all(item["text"] and item["sources"] and set(item["sources"]) <= sources for item in diagnosis[name])
    expected_status = "DIAGNOSED"
with urllib.request.urlopen(path, timeout=10) as response:
    assert json.load(response)["status"] == expected_status
print(f"GET diagnosis: HTTP 200, mode={diagnosis['mode']}, provider={diagnosis['provider']}, incident status={expected_status}", flush=True)
print(f"Diagnosis id={diagnosis['id']}, eventId={diagnosis['eventId']}, evidence=5, citations={diagnosis['citedRunbooks']}", flush=True)

code = '''
import json, time
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from db import connect_db
incident_id = ''' + repr(incident_id) + '''
with connect_db() as connection:
    row = connection.execute("SELECT o.event_id,o.payload,o.published_at FROM incidentiq_api.outbox_events o WHERE incident_id=%s", (incident_id,)).fetchone()
    event_id, event, published = row
    assert published is not None
    assert connection.execute("SELECT count(*) FROM incidentiq_api.processed_events WHERE event_id=%s", (event_id,)).fetchone()[0] == 1
    assert connection.execute("SELECT count(*) FROM incidentiq_api.incident_retrievals WHERE event_id=%s", (event_id,)).fetchone()[0] == 5
    assert connection.execute("SELECT count(*) FROM incidentiq_api.diagnoses WHERE event_id=%s", (event_id,)).fetchone()[0] == 1
    before = connection.execute("SELECT rank, chunk_id, content, source, similarity, retrieved_at FROM incidentiq_api.incident_retrievals WHERE event_id=%s ORDER BY rank", (event_id,)).fetchall()
producer = KafkaProducer(bootstrap_servers="kafka:29092", acks="all")
record = producer.send("incident.created", key=incident_id.encode(), value=json.dumps(event).encode()).get(timeout=15)
producer.close()
monitor = KafkaConsumer(bootstrap_servers="kafka:29092", group_id="incidentiq-worker-v1", enable_auto_commit=False)
partition = TopicPartition("incident.created", record.partition)
for _ in range(60):
    committed = monitor.committed(partition)
    if committed is not None and committed >= record.offset + 1:
        break
    time.sleep(1)
else:
    raise AssertionError("Duplicate Kafka offset was not durably handled")
monitor.close(autocommit=False)
with connect_db() as connection:
    after = connection.execute("SELECT rank, chunk_id, content, source, similarity, retrieved_at FROM incidentiq_api.incident_retrievals WHERE event_id=%s ORDER BY rank", (event_id,)).fetchall()
    assert before == after
    assert connection.execute("SELECT count(*) FROM incidentiq_api.diagnoses WHERE event_id=%s", (event_id,)).fetchone()[0] == 1
print(f"Outbox acknowledged; one receipt, five snapshots, one diagnosis; duplicate offset={record.offset}, committed={committed}")
'''
completed = subprocess.run(["docker", "compose", "exec", "-T", "worker", "python", "-"],
                           input=code, text=True, capture_output=True, check=True)
print(completed.stdout, end="")
with urllib.request.urlopen(path + "/diagnosis", timeout=10) as response:
    assert json.load(response) == diagnosis
print("Diagnosis and evidence unchanged on duplicate; real end-to-end verification passed.")
