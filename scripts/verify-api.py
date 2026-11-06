#!/usr/bin/env python3
"""Real HTTP smoke checks; creates one synthetic incident and preserves it."""
import json
import sys
import urllib.error
import urllib.request
import uuid

base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"


def request(method, path, expected, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        result = json.load(response)
        assert response.status == expected, (method, path, response.status, result)
        print(f"{method} {path}: HTTP {response.status}")
        return result, response.headers


health, _ = request("GET", "/actuator/health", 200)
assert health["status"] == "UP"
payload = {"service": "http-smoke", "title": "Synthetic timeout",
           "description": "Created by the local HTTP verification script", "severity": "HIGH"}
created, headers = request("POST", "/api/incidents", 201, payload)
incident_id = str(uuid.UUID(created["id"]))
assert created["status"] == "PENDING"
assert headers["Location"].endswith("/api/incidents/" + incident_id)
assert created["createdAt"] and created["updatedAt"]
print(f"Created incident {incident_id}, status={created['status']}")
stored, _ = request("GET", "/api/incidents/" + incident_id, 200)
assert stored["status"] in ("PENDING", "RECEIVED")
assert {k: v for k, v in stored.items() if k not in ("status", "updatedAt")} == {
    k: v for k, v in created.items() if k not in ("status", "updatedAt")}
page, _ = request("GET", "/api/incidents?page=0&size=20", 200)
assert any(row["id"] == incident_id for row in page["content"])
request("GET", "/api/incidents/" + incident_id + "/diagnosis", 404)
request("GET", "/api/incidents/" + str(uuid.uuid4()), 404)
request("GET", "/api/incidents/" + str(uuid.uuid4()) + "/diagnosis", 404)
invalid = dict(payload, service=" ")
problem, _ = request("POST", "/api/incidents", 400, invalid)
assert "service" in problem["errors"]
request("POST", "/api/incidents", 400, dict(payload, severity="URGENT"))
request("POST", "/api/incidents", 400, dict(payload, status="RESOLVED"))
request("GET", "/api/incidents/not-a-uuid", 400)
request("GET", "/api/incidents?size=101", 400)
print("All 12 HTTP checks passed; synthetic incident retained.")
