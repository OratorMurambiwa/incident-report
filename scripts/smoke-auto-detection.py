#!/usr/bin/env python3
"""Real automatic detection smoke test. Enables dev simulation temporarily and restores defaults."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


def compose(*args, dev=False):
    command = ["docker", "compose"]
    if dev:
        command += ["-f", "compose.yaml", "-f", "compose.dev.yaml"]
    return subprocess.check_output(command + list(args), text=True, stderr=subprocess.STDOUT)


def http(url, expected=200):
    try:
        response = urllib.request.urlopen(url, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        data = json.load(response)
        assert response.status == expected, (url, response.status, data)
        return data


def db(query, **variables):
    args = ["docker", "compose", "exec", "-T", "postgres", "sh", "-ec",
            'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -v ON_ERROR_STOP=1 "$@"', "--"]
    for key, value in variables.items():
        assert re.fullmatch(r"[a-z_]+", key)
        args += ["-v", f"{key}={value}"]
    value = subprocess.check_output(args, input=query, text=True).strip()
    return json.loads(value) if value else None


def wait(check, message, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(1)
    raise AssertionError(message)


def observation(fingerprint, starts_at=None):
    row = db("""
        SELECT json_build_object('incident_id', a.incident_id, 'resolved_at', a.resolved_at, 'starts_at', a.starts_at,
          'status', i.status, 'event_id', o.event_id, 'published', o.published_at IS NOT NULL,
          'diagnosis_id', d.id, 'mode', d.mode,
          'snapshots', (SELECT count(*) FROM incidentiq_api.incident_retrievals r WHERE r.incident_id=i.id),
          'receipts', (SELECT count(*) FROM incidentiq_api.processed_events p WHERE p.incident_id=i.id),
          'outbox_count', (SELECT count(*) FROM incidentiq_api.outbox_events x WHERE x.incident_id=i.id),
          'last_notification', s.updated_at,
          'occurrences', (SELECT count(*) FROM incidentiq_api.alert_incidents x WHERE x.fingerprint=a.fingerprint))
        FROM incidentiq_api.alert_incidents a JOIN incidentiq_api.alert_states s ON s.fingerprint=a.fingerprint
        JOIN incidentiq_api.incidents i ON i.id=a.incident_id
        LEFT JOIN incidentiq_api.outbox_events o ON o.incident_id=i.id
        LEFT JOIN incidentiq_api.diagnoses d ON d.incident_id=i.id
        WHERE a.fingerprint=:'fingerprint' ORDER BY a.created_at DESC LIMIT 1;
        """, fingerprint=fingerprint)
    # A fingerprint recurs after resolution. Never accept an older occurrence
    # while waiting for the current firing webhook to arrive.
    if starts_at is not None and row is not None:
        if datetime.fromisoformat(row["starts_at"]) != datetime.fromisoformat(starts_at):
            return None
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--api", default="http://127.0.0.1:8080")
    parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
    parser.add_argument("--alertmanager", default="http://127.0.0.1:9093")
    args = parser.parse_args()
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "phases": []}
    stop = threading.Event()
    thread = None
    traffic_errors = []
    worker_stopped = False

    def active(name, uri=None, job=None):
        alerts = http(args.prometheus + "/api/v1/alerts")["data"]["alerts"]
        found = [a for a in alerts if a["state"] == "firing" and a["labels"]["alertname"] == name
                 and (uri is None or a["labels"].get("uri") == uri) and (job is None or a["labels"].get("job") == job)]
        if not found:
            return None
        received = http(args.alertmanager + "/api/v2/alerts")
        return next((a for a in received if a["labels"].get("alertname") == name
                     and (uri is None or a["labels"].get("uri") == uri)
                     and (job is None or a["labels"].get("job") == job)), None)

    def diagnosed(fp, starts_at):
        row = observation(fp, starts_at)
        return row if row and row["diagnosis_id"] and row["published"] and row["snapshots"] == 5 else None

    def webhook_count():
        with urllib.request.urlopen(args.api + "/actuator/prometheus", timeout=10) as response:
            lines = response.read().decode().splitlines()
        return sum(float(line.rsplit(" ", 1)[1]) for line in lines
                   if line.startswith("http_server_requests_seconds_count{") and 'uri="/api/alerts/alertmanager"' in line and 'status="200"' in line)

    def start_traffic(path, expected):
        nonlocal thread
        stop.clear()
        def run():
            while not stop.is_set():
                try:
                    http(args.api + path, expected)
                except Exception as error:
                    traffic_errors.append(str(error))
                    return
                stop.wait(0.1)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def stop_traffic():
        stop.set()
        if thread:
            thread.join(timeout=5)
        assert not traffic_errors, traffic_errors

    try:
        http(args.api + "/api/dev/simulate/failure", 404)
        http(args.api + "/api/dev/simulate/latency", 404)
        print("Default configuration: both simulation endpoints return 404", flush=True)
        options = ["up", "-d", "--wait"] + ([] if args.skip_build else ["--build"])
        compose(*options, "api", "publisher", "worker", dev=True)
        compose("--profile", "observability", "up", "-d", "--wait", "alertmanager", "prometheus", "grafana", dev=True)
        http(args.api + "/api/dev/simulate/failure", 500)
        print("Development opt-in ready; real containers and alert rules running", flush=True)
        for name, path, expected in [
            ("IncidentIQHighHttp500Rate", "/api/dev/simulate/failure", 500),
            ("IncidentIQHighP95Latency", "/api/dev/simulate/latency?delayMs=750", 200),
        ]:
            uri = path.split("?")[0]
            print("Triggering", name, flush=True)
            start_traffic(path, expected)
            alert = wait(lambda: active(name, uri=uri), f"{name} never reached Prometheus and Alertmanager")
            fp = alert["fingerprint"]
            row = wait(lambda: diagnosed(fp, alert["startsAt"]), "Alert webhook did not produce a stored diagnosis")
            assert row["receipts"] == row["outbox_count"] == 1
            diagnosis = http(args.api + "/api/incidents/" + row["incident_id"] + "/diagnosis")
            assert len(diagnosis["retrievedEvidence"]) == 5
            wait(lambda: webhook_count() or None, "No successful real webhook calls observed")
            baseline = observation(fp, alert["startsAt"])["last_notification"]
            wait(lambda: observation(fp, alert["startsAt"])["last_notification"] != baseline, "Alertmanager repeat notification for this fingerprint was not delivered", timeout=45)
            repeated = observation(fp, alert["startsAt"])
            assert repeated["incident_id"] == row["incident_id"] and repeated["occurrences"] == row["occurrences"]
            assert repeated["outbox_count"] == repeated["receipts"] == 1
            assert http(args.api + "/api/incidents/" + row["incident_id"] + "/diagnosis") == diagnosis
            print(name, "firing -> one incident/outbox/receipt/diagnosis; repeat deduplicated:", row["incident_id"], flush=True)
            stop_traffic()
            resolved = wait(lambda: (r if (r := observation(fp, alert["startsAt"])) and r["status"] == "RESOLVED" and r["resolved_at"] else None), "Resolved notification did not close incident")
            report["phases"].append({"alertname": name, "fingerprint": fp, **resolved})
            print(name, "resolved notification -> RESOLVED", flush=True)
        print("Triggering actual worker unavailability", flush=True)
        compose("stop", "worker")
        worker_stopped = True
        alert = wait(lambda: active("IncidentIQServiceUnavailable", job="incidentiq-worker"), "Worker outage did not alert")
        fp = alert["fingerprint"]
        pending = wait(lambda: observation(fp, alert["startsAt"]), "Service alert did not create an incident")
        assert pending["outbox_count"] == 1
        compose("start", "worker")
        worker_stopped = False
        row = wait(lambda: diagnosed(fp, alert["startsAt"]), "Queued worker-outage alert did not receive a diagnosis after recovery")
        resolved = wait(lambda: (r if (r := observation(fp, alert["startsAt"])) and r["status"] == "RESOLVED" else None), "Worker recovery did not resolve incident")
        assert row["receipts"] == row["outbox_count"] == 1
        assert http(args.api + "/api/incidents/" + row["incident_id"] + "/diagnosis")["id"] == row["diagnosis_id"]
        report["phases"].append({"alertname": "IncidentIQServiceUnavailable", "fingerprint": fp, **resolved})
        print("Actual worker outage -> webhook -> queued Kafka event -> stored diagnosis -> RESOLVED", flush=True)
        event_ids = [p["event_id"] for p in report["phases"]]
        code = '''
import json
from kafka import KafkaConsumer,TopicPartition
expected=set(''' + repr(event_ids) + ''')
consumer=KafkaConsumer(bootstrap_servers="kafka:29092",enable_auto_commit=False,group_id=None,consumer_timeout_ms=10000)
partition=TopicPartition("incident.created",0)
consumer.assign([partition]); consumer.seek_to_beginning(partition)
seen=set()
for record in consumer:
 try: event=json.loads(record.value)
 except (ValueError,TypeError): continue
 if event.get("eventId") in expected: seen.add(event["eventId"])
 if seen==expected: break
consumer.close(autocommit=False)
assert seen==expected,(seen,expected)
print("Independent Kafka observer matched all three outbox event IDs")
'''
        print(subprocess.check_output(["docker", "compose", "exec", "-T", "worker", "python", "-"], input=code, text=True).strip(), flush=True)
        internal = db("SELECT count(*) FROM incidentiq_api.alert_incidents WHERE labels->>'uri' ~ '^(/actuator|/api/incidents|/api/alerts)';")
        assert internal == 0, "Unexpected recursive alert incidents"
        report["internal_recursive_incidents"] = internal
    finally:
        stop.set()
        if thread:
            thread.join(timeout=5)
        if worker_stopped:
            compose("start", "worker")
        compose("up", "-d", "--no-deps", "--wait", "api")
        http(args.api + "/api/dev/simulate/failure", 404)
        http(args.api + "/api/dev/simulate/latency", 404)
        print("Restored default configuration: simulation endpoints return 404", flush=True)
    report["default_simulation_disabled"] = True
    directory = Path(".incidentiq-backups/automatic-detection")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print("Full automatic detection smoke test passed; prior data and volumes retained.")


if __name__ == "__main__":
    main()
