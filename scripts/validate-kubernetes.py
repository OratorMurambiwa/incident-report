#!/usr/bin/env python3
"""Cross-resource static checks in addition to kubeconform's Kubernetes schemas."""
import json
from pathlib import Path
import sys
import yaml


def validate(documents: list[dict]) -> dict:
    objects = {(d['kind'], d['metadata']['name']): d for d in documents}
    assert len(objects) == len(documents), 'Duplicate resource identities'
    workloads = [d for d in documents if d['kind'] in ('Deployment', 'StatefulSet', 'Job')]
    maps = {d['metadata']['name']: d.get('data', {}) for d in documents if d['kind'] == 'ConfigMap'}
    assert not any(d['kind'] == 'Secret' for d in documents), 'Credentials must be provisioned out of band'
    assert {d['metadata'].get('namespace') for d in documents if d['kind'] != 'Namespace'} == {'incidentiq-local'}
    assert {d['metadata']['name'] for d in documents if d['kind'] == 'Namespace'} == {'incidentiq-local'}
    config = next(v for k, v in maps.items() if k.startswith('incidentiq-config-'))
    assert config['POSTGRES_HOST'] == 'postgres' and config['POSTGRES_PORT'] == '5432'
    assert config['POSTGRES_DB'] == 'incidentiq_k8s_local'
    assert config['KAFKA_BOOTSTRAP_SERVERS'] == 'kafka:29092' and config['LLM_PROVIDER'] == 'none'
    services = [d for d in documents if d['kind'] == 'Service']
    images = set()
    for d in workloads:
        pod = d['spec']['template']['spec']
        assert not pod.get('hostNetwork') and not pod.get('hostPID')
        assert pod['automountServiceAccountToken'] is False
        for volume in pod.get('volumes', []):
            assert 'hostPath' not in volume, 'Never mount Compose/host data'
            if 'configMap' in volume:
                assert volume['configMap']['name'] in maps
        for c in pod['containers'] + pod.get('initContainers', []):
            images.add(c['image'])
            assert ':latest' not in c['image'] and ':' in c['image']
            assert c['imagePullPolicy'] == 'IfNotPresent'
            assert set(c['resources']) == {'requests', 'limits'}
            assert all({'cpu', 'memory'} <= v.keys() for v in c['resources'].values())
            for ref in c.get('envFrom', []):
                if 'configMapRef' in ref: assert ref['configMapRef']['name'] in maps
                if 'secretRef' in ref: assert ref['secretRef']['name'] == 'database-credentials'
            assert not any(e['name'] == 'POSTGRES_PASSWORD' and 'value' in e for e in c.get('env', []))
        if d['kind'] != 'Job':
            for c in pod['containers']:
                assert all(p in c for p in ('startupProbe', 'livenessProbe', 'readinessProbe'))
        else:
            assert d['spec']['backoffLimit'] == 3 and d['spec']['activeDeadlineSeconds'] == 600
        if d['kind'] == 'StatefulSet':
            assert d['spec']['persistentVolumeClaimRetentionPolicy'] == {'whenDeleted': 'Retain', 'whenScaled': 'Retain'}
            assert d['spec']['volumeClaimTemplates'][0]['spec']['accessModes'] == ['ReadWriteOnce']
    for s in services:
        assert s['spec'].get('type', 'ClusterIP') == 'ClusterIP'
        assert not s['spec'].get('externalIPs')
        matches = [d for d in workloads if all(d['spec']['template'].get('metadata', {}).get('labels', {}).get(k) == v for k,v in s['spec']['selector'].items())]
        assert len(matches) == 1, s['metadata']['name']
        ports = matches[0]['spec']['template']['spec']['containers'][0].get('ports', [])
        for port in s['spec']['ports']:
            assert any(port['targetPort'] in (p['containerPort'], p.get('name')) for p in ports), s['metadata']['name']
    assert images == {'apache/kafka:3.9.1', 'pgvector/pgvector:0.8.7-pg16-trixie', 'incidentiq-api:local', 'incidentiq-worker:local', 'incidentiq-frontend:local'}
    assert objects['Service', 'kafka']['spec']['publishNotReadyAddresses'] is True
    for name in ('worker', 'publisher'):
        gates = [c['command'][-1] for c in objects['Deployment', name]['spec']['template']['spec']['initContainers']]
        assert gates == (['evidence', 'topic'] if name == 'worker' else ['schema', 'topic'])
    publisher = objects['Deployment', 'publisher']['spec']['template']['spec']['containers'][0]
    assert {'name': 'SPRING_FLYWAY_ENABLED', 'value': 'false'} in publisher['env']
    nginx = next(v['default.conf'] for v in maps.values() if 'default.conf' in v)
    assert '127.0.0.11' not in nginx and 'proxy_pass http://api:8080;' in nginx
    runbooks = next(v for k,v in maps.items() if k.startswith('runbooks-'))
    assert len(runbooks) == 10 and all(k.endswith('.md') for k in runbooks)
    return {'resources': len(documents), 'workloads': len(workloads), 'services': len(services),
            'runbooks': len(runbooks), 'images': sorted(images), 'cross_resource_checks': 'passed'}


if __name__ == '__main__':
    print(json.dumps(validate(list(yaml.safe_load_all(Path(sys.argv[1]).read_text()))), indent=2))
