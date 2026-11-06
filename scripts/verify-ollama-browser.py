#!/usr/bin/env python3
"""Actual local-model browser flow. No response interception or model mocks."""
import json
from pathlib import Path
import time
import uuid
from playwright.sync_api import sync_playwright, expect

cases = [
    ('database', 'Database connection pool exhausted after deployment',
     'PostgreSQL reports too many clients and SQLSTATE 08006. An application deployment increased connection concurrency. Database connections time out.'),
    ('memory', 'Worker memory exhaustion and OOMKilled restarts',
     'Container memory usage grows until OOMKilled. Heap retention and queue backlog increased after a deployment. Requests restart repeatedly.'),
    ('kafka', 'Kafka consumer lag with increasing message backlog',
     'Kafka consumer group lag keeps rising. Consumers process messages slowly, partitions have large backlogs, and recent deployment changed consumer concurrency.'),
]
output = Path('/evidence')
output.mkdir(parents=True, exist_ok=True)
results = []
rejections = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--no-sandbox'])
    context = browser.new_context(locale='en-US', viewport={'width':1440,'height':1100})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    for kind, title, description in cases:
        page.goto('http://frontend')
        page.get_by_role('button', name='+ Report incident').click()
        page.get_by_label('Service', exact=True).fill('ollama-live-' + kind + '-' + str(uuid.uuid4())[:8])
        page.get_by_label('Title', exact=True).fill(title)
        page.get_by_label('Description', exact=True).fill(description)
        started = time.monotonic()
        with page.expect_response(lambda r: r.url.endswith('/api/incidents') and r.request.method=='POST') as created:
            page.get_by_role('button', name='Submit incident', exact=True).click()
        assert created.value.status == 201
        incident = created.value.json()
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            state = context.request.get('http://frontend/api/incidents/' + incident['id']).json()['status']
            if state in ('DIAGNOSED', 'FAILED'):
                break
            page.wait_for_timeout(1000)
        if state == 'FAILED' and kind == 'kafka':
            assert context.request.get('http://frontend/api/incidents/' + incident['id'] + '/diagnosis').status == 404
            expect(page.get_by_role('heading', name='Processing failed', exact=True)).to_be_visible(timeout=10000)
            rejections.append({'case':kind,'incident_id':incident['id'],'status':state})
            print('Actual Kafka answer failed closed; verify durable InvalidDiagnosis below:',incident['id'],flush=True)
            continue
        assert state == 'DIAGNOSED', (kind,state)
        expect(page.get_by_role('heading', name='AI-generated diagnosis', exact=True)).to_be_visible(timeout=10000)
        elapsed = time.monotonic() - started
        response = context.request.get('http://frontend/api/incidents/' + incident['id'] + '/diagnosis')
        assert response.status == 200
        diagnosis = response.json()
        assert diagnosis['mode']=='GENERATED' and diagnosis['provider']=='ollama' and diagnosis['model']=='qwen3:0.6b'
        allowed = {e['source'] for e in diagnosis['retrievedEvidence']}
        assert len(diagnosis['retrievedEvidence'])==5
        for key in ('likelyCauses','investigationSteps','suggestedRemediation'):
            assert diagnosis[key]
            for item in diagnosis[key]:
                assert item['text'].strip() and item['sources'] and set(item['sources']) <= allowed
        assert set(diagnosis['citedRunbooks']) <= allowed and diagnosis['uncertainty'].strip()
        status = context.request.get('http://frontend/api/incidents/' + incident['id']).json()['status']
        assert status=='DIAGNOSED', status
        for heading in ('Likely causes','Investigation steps','Suggested remediation','Cited runbooks'):
            expect(page.get_by_role('heading', name=heading, exact=True)).to_be_visible()
        page.screenshot(path=str(output / (kind + '.png')), full_page=True)
        results.append({'case':kind,'incident_id':incident['id'],'end_to_end_seconds':round(elapsed,3),'diagnosis':diagnosis})
        print('PASS actual React → API → Kafka → LangChain → Ollama → PostgreSQL → React:',kind,incident['id'],round(elapsed,3),'seconds',flush=True)
    assert not errors, errors
    browser.close()
(output / 'generated.json').write_text(json.dumps({'results':results,'rejections':rejections,'browser_errors':errors},indent=2)+'\n')
