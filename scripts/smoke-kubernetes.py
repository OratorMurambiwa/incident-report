#!/usr/bin/env python3
"""Opt-in real local Kubernetes HTTP/DB smoke check, retaining its synthetic incident."""
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid

BASE = 'http://127.0.0.1:18082'

def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=10) as response:
        return json.load(response)


def main() -> None:
    deadline = time.monotonic() + 30
    while True:
        try:
            get('/api/incidents?size=1')
            break
        except (OSError, urllib.error.URLError):
            if time.monotonic() > deadline:
                raise
            time.sleep(1)
    payload = {'service': 'k8s-smoke-' + uuid.uuid4().hex[:8], 'title': 'Kubernetes database connection pool failure',
               'description': 'PostgreSQL too many clients, connection pool exhausted, SQLSTATE 08006.', 'severity': 'HIGH'}
    request = urllib.request.Request(BASE + '/api/incidents', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.status == 201
        incident = json.load(response)
    while time.monotonic() - start < 120:
        try:
            diagnosis = get('/api/incidents/' + incident['id'] + '/diagnosis')
            break
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
            time.sleep(1)
    else:
        raise AssertionError('Diagnosis did not become available')
    assert diagnosis['mode'] == 'RETRIEVAL_ONLY' and len(diagnosis['retrievedEvidence']) == 5
    assert get('/api/incidents/' + incident['id'])['status'] == 'RECEIVED'
    code = '''
import json,sys
from db import connect_db
with connect_db() as c:
 row=c.execute("""SELECT
 (SELECT count(*) FROM incidentiq_api.outbox_events WHERE incident_id=%s AND published_at IS NOT NULL),
 (SELECT count(*) FROM incidentiq_api.processed_events WHERE incident_id=%s),
 (SELECT count(*) FROM incidentiq_api.diagnoses WHERE incident_id=%s),
 (SELECT count(*) FROM incidentiq_api.incident_retrievals WHERE incident_id=%s)""", (sys.argv[1],)*4).fetchone()
 assert tuple(row)==(1,1,1,5),row
 print(json.dumps(dict(zip(('published_outbox','receipts','diagnoses','snapshots'),row))))
'''
    raw = subprocess.check_output(['kubectl', '--context', 'kind-incidentiq-dev', '-n', 'incidentiq-local',
                                   'exec', 'deployment/worker', '-c', 'worker', '--', 'python', '-c', code, incident['id']], text=True)
    print(json.dumps({'incident_id': incident['id'], 'mode': diagnosis['mode'],
                      'seconds': round(time.monotonic()-start, 3), 'durable': json.loads(raw)}, indent=2))


if __name__ == '__main__':
    main()
