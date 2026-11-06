#!/usr/bin/env python3
"""Verify live Prometheus/Grafana data. Creates synthetic success/failure fixtures by default."""
import argparse
import base64
import json
import math
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def request(url, body=None, auth=None, expected=200):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = "Basic " + base64.b64encode(auth.encode()).decode()
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        result = json.load(response)
        assert response.status in (expected if isinstance(expected, tuple) else (expected,)), f"{req.get_method()} {url}: HTTP {response.status}"
        return result


def worker(code):
    return subprocess.check_output(["docker", "compose", "exec", "-T", "worker", "python", "-"], input=code, text=True).strip()


def query(prometheus, expr):
    result = request(prometheus + "/api/v1/query?" + urllib.parse.urlencode({"query": expr}))
    assert result["status"] == "success", result
    return result["data"]["result"]


def scalar(prometheus, expr):
    result = query(prometheus, expr)
    return float(result[0]["value"][1]) if result else float("nan")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8080")
    parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
    parser.add_argument("--grafana", default="http://127.0.0.1:3001")
    parser.add_argument("--no-fixtures", action="store_true")
    args = parser.parse_args()
    for _ in range(36):
        targets = request(args.prometheus + "/api/v1/targets")["data"]["activeTargets"]
        apps = {t["labels"]["job"]: t for t in targets if t["labels"]["job"] in ("incidentiq-api", "incidentiq-worker")}
        if len(apps) == 2 and all(t["health"] == "up" for t in apps.values()):
            break
        time.sleep(2)
    else:
        raise AssertionError("Application scrape targets did not become UP")
    assert apps["incidentiq-api"]["scrapeUrl"] == "http://api:8080/actuator/prometheus"
    assert apps["incidentiq-worker"]["scrapeUrl"] == "http://worker:8001/metrics"
    print("Prometheus targets UP: api:8080/actuator/prometheus, worker:8001/metrics", flush=True)
    fixtures = {}
    if not args.no_fixtures:
        created = request(args.api + "/api/incidents", {"service": "monitoring-smoke", "title": "PostgreSQL pool exhaustion",
            "description": "Synthetic monitoring verification: too many clients, connection pool exhausted.", "severity": "HIGH"}, expected=201)
        fixtures["incident_id"] = created["id"]
        print("Created synthetic monitoring incident:", created["id"], flush=True)
        for _ in range(60):
            diagnosis = request(args.api + "/api/incidents/" + created["id"] + "/diagnosis", expected=(200, 404))
            if "mode" in diagnosis:
                break
            time.sleep(1)
        else:
            raise AssertionError("Synthetic incident did not receive a diagnosis")
        assert len(diagnosis["retrievedEvidence"]) == 5
        print("Actual HTTP/Kafka/RAG success fixture:", created["id"], diagnosis["mode"], flush=True)
        for i in range(24):
            request(args.api + "/api/incidents?size=1")
            if i % 3 == 0:
                request(args.api + "/api/incidents", {}, expected=400)
            if i % 4 == 0:
                request(args.api + "/api/incidents/00000000-0000-0000-0000-000000000000", expected=404)
            time.sleep(0.4)
        # A valid event referencing a nonexistent synthetic incident exercises durable failure handling.
        # It cannot alter an existing incident; it leaves one explicit quarantine evidence record.
        raw = worker('''
import json,time
from datetime import datetime,timezone
from uuid import uuid4
from kafka import KafkaProducer
from db import connect_db
payload={"schemaVersion":1,"eventId":str(uuid4()),"incidentId":str(uuid4()),"service":"monitoring-failure-fixture","title":"Synthetic missing incident","description":"Intentional observability failure fixture","severity":"LOW","timestamp":datetime.now(timezone.utc).isoformat()}
producer=KafkaProducer(bootstrap_servers="kafka:29092",acks="all")
metadata=producer.send("incident.created",value=json.dumps(payload).encode()).get(timeout=15)
producer.close()
for _ in range(45):
 with connect_db() as connection:
  row=connection.execute("SELECT error_code FROM incidentiq_api.failed_events WHERE topic=%s AND partition_id=%s AND offset_id=%s",(metadata.topic,metadata.partition,metadata.offset)).fetchone()
 if row:
  print(json.dumps({"event_id":payload["eventId"],"partition":metadata.partition,"offset":metadata.offset,"error_code":row[0]}))
  break
 time.sleep(1)
else: raise AssertionError("Synthetic failure was not durably quarantined")
''')
        fixtures["failure"] = json.loads(raw)
        print("Actual failed workflow quarantined:", fixtures["failure"], flush=True)
    checks = {
        "http_requests": 'sum(http_server_requests_seconds_count{job="incidentiq-api",uri!~"/actuator.*"})',
        "http_p95_seconds": 'histogram_quantile(0.95,sum by(le)(rate(http_server_requests_seconds_bucket{job="incidentiq-api",uri!~"/actuator.*"}[5m])))',
        "http_client_errors": 'sum(http_server_requests_seconds_count{job="incidentiq-api",status=~"4.."})',
        "jvm_memory_bytes": 'sum(jvm_memory_used_bytes{job="incidentiq-api"})',
        "incident_total": 'sum(incidentiq_incidents{job="incidentiq-api"})',
        "worker_success": 'sum(incidentiq_worker_diagnoses_total{job="incidentiq-worker",outcome="success"})',
        "worker_failure": 'sum(incidentiq_worker_diagnoses_total{job="incidentiq-worker",outcome="failure"})',
        "worker_processing_p95_seconds": 'histogram_quantile(0.95,sum by(le)(rate(incidentiq_worker_processing_duration_seconds_bucket{job="incidentiq-worker"}[5m])))',
        "rag_retrieval_p95_seconds": 'histogram_quantile(0.95,sum by(le)(rate(incidentiq_worker_rag_retrieval_duration_seconds_bucket{job="incidentiq-worker"}[5m])))',
    }
    for _ in range(36):
        values = {name: scalar(args.prometheus, expr) for name, expr in checks.items()}
        if all(math.isfinite(value) and value > 0 for value in values.values()):
            break
        time.sleep(2)
    else:
        raise AssertionError(f"Expected finite positive live samples: {values}")
    db_count = int(worker('from db import connect_db\nwith connect_db() as c: print(c.execute("SELECT count(*) FROM incidentiq_api.incidents").fetchone()[0])'))
    assert values["incident_total"] == db_count
    uri_labels = sorted({row["metric"]["uri"] for row in query(args.prometheus, 'count by(uri)(http_server_requests_seconds_count{job="incidentiq-api"})')})
    assert len(uri_labels) <= 32 and not any(re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", uri) for uri in uri_labels)
    for row in query(args.prometheus, 'incidentiq_worker_diagnoses_total{job="incidentiq-worker"}'):
        assert set(row["metric"]) <= {"__name__", "job", "instance", "outcome", "mode"}
        assert row["metric"]["mode"] in ("generated", "retrieval_only")
    password = subprocess.check_output(["docker", "compose", "exec", "-T", "grafana", "printenv", "GF_SECURITY_ADMIN_PASSWORD"], text=True).strip()
    username = subprocess.check_output(["docker", "compose", "exec", "-T", "grafana", "printenv", "GF_SECURITY_ADMIN_USER"], text=True).strip()
    auth = username + ":" + password
    assert request(args.grafana + "/api/health")["database"] == "ok"
    assert request(args.grafana + "/api/datasources/uid/prometheus/health", auth=auth)["status"] == "OK"
    dashboard = request(args.grafana + "/api/dashboards/uid/incidentiq-overview", auth=auth)["dashboard"]
    verified_panels = []
    for panel in dashboard["panels"]:
        queries = [{**target, "expr": target["expr"].replace("$__rate_interval", "1m"), "instant": True, "range": False,
                    "intervalMs": 5000, "maxDataPoints": 200} for target in panel["targets"]]
        now = int(time.time() * 1000)
        result = request(args.grafana + "/api/ds/query", {"from": str(now-600000), "to": str(now), "queries": queries}, auth=auth)
        numbers = []
        for data in result["results"].values():
            assert not data.get("error"), (panel["title"], data.get("error"))
            for frame in data.get("frames", []):
                for field, column in zip(frame["schema"]["fields"], frame["data"]["values"]):
                    if field["type"] == "number":
                        numbers.extend(v for v in column if isinstance(v, (int,float)) and math.isfinite(v))
        assert numbers, f"Grafana panel has no real numeric data: {panel['title']}"
        verified_panels.append(panel["title"])
    report = {"targets": {job: {"health": t["health"], "scrape_url": t["scrapeUrl"]} for job,t in apps.items()},
              "live_values": values, "database_incidents": db_count, "uri_labels": uri_labels,
              "grafana_panels_with_real_data": verified_panels, "fixtures": fixtures}
    evidence = Path(".incidentiq-backups/monitoring")
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    print(f"Verified {len(verified_panels)} Grafana panels through the real datasource query API.")


if __name__ == "__main__":
    main()
