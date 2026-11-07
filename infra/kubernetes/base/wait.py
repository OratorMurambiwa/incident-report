"""Bounded Kubernetes init gate; no payload logging or Kubernetes API permissions."""
import ast
import hashlib
from pathlib import Path
import os
import sys
import time
from db import connect_db
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

mode = sys.argv[1]
deadline = time.monotonic() + 300
while time.monotonic() < deadline:
    try:
        if mode == 'topic':
            client = KafkaAdminClient(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                     request_timeout_ms=10000, api_version_auto_timeout_ms=5000)
            try:
                try:
                    client.create_topics([NewTopic('incident.created', 1, 1)])
                except TopicAlreadyExistsError:
                    pass
                assert 'incident.created' in client.list_topics()
            finally:
                client.close()
        else:
            with connect_db() as connection:
                if mode in ('schema', 'evidence'):
                    rows = connection.execute('SELECT version, success FROM incidentiq_api.flyway_schema_history WHERE version IS NOT NULL').fetchall()
                    assert {str(n) for n, ok in rows if ok} >= {'1','2','3','4','5','6'}
                    assert all(ok for _, ok in rows)
                if mode == 'evidence':
                    from model import MODEL_NAME, MODEL_REVISION
                    tree = ast.parse(Path('/app/ingest.py').read_text())
                    version = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                                   and any(isinstance(t, ast.Name) and t.id == 'CHUNKING_VERSION' for t in n.targets))
                    paths = [p for p in Path('/runbooks').glob('*.md') if p.name != 'README.md']
                    assert paths
                    for path in paths:
                        fingerprint = hashlib.sha256((path.read_text() + MODEL_NAME + MODEL_REVISION + version).encode()).hexdigest()
                        row = connection.execute('SELECT fingerprint, chunk_count FROM incidentiq_api.runbook_documents WHERE source=%s', (path.name,)).fetchone()
                        assert row and row[0] == fingerprint and row[1] > 0
                    assert connection.execute('SELECT count(*) FROM incidentiq_api.runbook_chunks').fetchone()[0] >= 5
        print('Dependency gate ready:', mode, flush=True)
        break
    except Exception as error:
        print('Waiting for', mode, type(error).__name__, flush=True)
        time.sleep(3)
else:
    raise SystemExit('Dependency gate timed out: ' + mode)
