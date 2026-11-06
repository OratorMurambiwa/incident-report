#!/usr/bin/env python3
"""Real HTTP/Kafka/PostgreSQL checks. Retains synthetic incident and failure evidence."""
import json
import subprocess
import time
import urllib.request


def worker(code):
    completed = subprocess.run(["docker", "compose", "exec", "-T", "worker", "python", "-"],
                               input=code, text=True, capture_output=True, check=True)
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="")


payload = {"service": "event-flow-smoke", "title": "Synthetic PostgreSQL connection pool exhaustion",
           "description": "PostgreSQL rejects connections: too many clients, connection pool exhausted, SQLSTATE 08006. Local retrieval verification.", "severity": "HIGH"}
req = urllib.request.Request("http://127.0.0.1:8080/api/incidents",
                             data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=15) as response:
    incident = json.load(response)
    assert response.status == 201 and incident["status"] == "PENDING"
    print(f"POST: HTTP {response.status}, incidentId={incident['id']}, status=PENDING", flush=True)

for _ in range(60):
    with urllib.request.urlopen("http://127.0.0.1:8080/api/incidents/" + incident["id"], timeout=10) as response:
        received = json.load(response)
    if received["status"] == "RECEIVED":
        break
    time.sleep(1)
else:
    raise AssertionError("Worker did not set RECEIVED within 60 seconds")
print("GET: HTTP 200, status=RECEIVED", flush=True)

worker('''
import json, time
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from main import connect_db
incident_id = ''' + repr(incident["id"]) + '''
with connect_db() as db:
    row = db.execute("SELECT event_id, payload, attempts, published_at FROM incidentiq_api.outbox_events WHERE incident_id=%s", (incident_id,)).fetchone()
    event_id, event, attempts, published = row
    assert published is not None and attempts >= 1
    receipt = db.execute("SELECT count(*) FROM incidentiq_api.processed_events WHERE event_id=%s AND incident_id=%s", (event_id, incident_id)).fetchone()[0]
    assert receipt == 1
    contexts = db.execute("SELECT rank, chunk_id, source, similarity, content, retrieved_at FROM incidentiq_api.incident_retrievals WHERE event_id=%s ORDER BY rank", (event_id,)).fetchall()
    assert len(contexts) == 5
    assert "database-failures.md" in [r[2] for r in contexts[:3]]
    assert all(row[4] for row in contexts)
    before = db.execute("SELECT updated_at FROM incidentiq_api.incidents WHERE id=%s", (incident_id,)).fetchone()[0]
print("Persisted retrievals: " + json.dumps([{"rank": r[0], "source": r[2], "similarity": round(r[3], 6)} for r in contexts]))
print(f"Outbox published: eventId={event_id}, attempts={attempts}; durable receipts={receipt}")
# Observe the actual event on Kafka using an independent, non-committing consumer.
observer = KafkaConsumer(bootstrap_servers="kafka:29092", enable_auto_commit=False,
                         group_id=None, consumer_timeout_ms=10000)
partition = TopicPartition("incident.created", 0)
observer.assign([partition])
observer.seek_to_beginning(partition)
found = False
for record in observer:
    try:
        candidate = json.loads(record.value)
    except (ValueError, TypeError):
        continue
    if candidate.get("eventId") == str(event_id):
        assert candidate == event
        print(f"Kafka observed: topic={record.topic}, offset={record.offset}, matching JSON contract")
        found = True
        break
observer.close(autocommit=False)
assert found
producer = KafkaProducer(bootstrap_servers="kafka:29092", acks="all")
duplicate = producer.send("incident.created", key=incident_id.encode(), value=json.dumps(event).encode()).get(timeout=15)
broken = b"{incidentiq-synthetic-malformed"
malformed = producer.send("incident.created", value=broken).get(timeout=15)
producer.close()
# A group-offset query does not subscribe/join or take partitions from the real worker.
monitor = KafkaConsumer(bootstrap_servers="kafka:29092", group_id="incidentiq-worker-v1", enable_auto_commit=False)
for _ in range(60):
    offset = monitor.committed(partition)
    if offset is not None and offset >= malformed.offset + 1:
        break
    time.sleep(1)
else:
    raise AssertionError("Worker offsets did not advance after durable handling")
monitor.close(autocommit=False)
with connect_db() as db:
    assert db.execute("SELECT count(*) FROM incidentiq_api.processed_events WHERE event_id=%s", (event_id,)).fetchone()[0] == 1
    after = db.execute("SELECT updated_at FROM incidentiq_api.incidents WHERE id=%s", (incident_id,)).fetchone()[0]
    assert after == before
    replayed_contexts = db.execute("SELECT rank, chunk_id, source, similarity, content, retrieved_at FROM incidentiq_api.incident_retrievals WHERE event_id=%s ORDER BY rank", (event_id,)).fetchall()
    assert replayed_contexts == contexts
    failed = db.execute("SELECT payload, error_code FROM incidentiq_api.failed_events WHERE topic=%s AND partition_id=%s AND offset_id=%s", (malformed.topic, malformed.partition, malformed.offset)).fetchone()
    assert failed is not None and bytes(failed[0]) == broken and failed[1] == "InvalidEvent"
print(f"Duplicate offset={duplicate.offset}: one receipt, incident timestamp unchanged")
print(f"Malformed offset={malformed.offset}: original bytes durably quarantined; group offset={offset}")
print("Full event flow, five persisted retrievals, duplicate delivery and malformed-record checks passed")
''')
