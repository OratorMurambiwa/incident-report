#!/usr/bin/env python3
"""Run in the optional Playwright browser container against real Compose services.
Retains synthetic incidents; UI-only response substitutions are explicitly reported.
"""
import json
import os
from pathlib import Path
import uuid
from playwright.sync_api import sync_playwright, expect

base = os.getenv('FRONTEND_URL', 'http://frontend')
output = Path('/evidence')
output.mkdir(parents=True, exist_ok=True)
class Checks(list):
    def append(self, item):
        super().append(item)
        print('PASS:', item, flush=True)
checks = Checks()
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--no-sandbox'])
    context = browser.new_context(locale='en-US', viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    held = []
    page.route('**/api/incidents?*', lambda route: held.append(route))
    page.goto(base)
    expect(page.get_by_text('Loading incidents…', exact=True)).to_be_visible()
    assert held
    held[0].continue_()
    page.unroute('**/api/incidents?*')
    checks.append('loading state while list response is held in browser test')
    expect(page.get_by_role('heading', name='Incident workspace')).to_be_visible()
    expect(page.get_by_role('table')).to_be_visible()
    checks.append('real incident list via nginx API proxy')
    for label in ['Grafana ↗', 'Prometheus ↗', 'Alertmanager ↗']:
        expect(page.get_by_role('link', name=label)).to_have_attribute('target', '_blank')
    checks.append('monitoring links')
    page.get_by_role('button', name='+ Report incident').click()
    page.get_by_role('button', name='Submit incident', exact=True).click()
    expect(page.get_by_text('This field is required.', exact=True)).to_have_count(3)
    expect(page.get_by_label('Service', exact=True)).to_be_focused()
    checks.append('required-field validation and keyboard focus')
    service = 'ui-e2e-' + str(uuid.uuid4())[:8]
    title = 'Database connection timeout <script>alert(1)</script>'
    page.get_by_label('Service', exact=True).fill(service)
    page.get_by_label('Title', exact=True).fill(title)
    page.get_by_label('Description', exact=True).fill('PostgreSQL connection pool exhausted. Database connections timeout and queries fail.')
    page.get_by_label('Severity', exact=True).select_option('CRITICAL')
    with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith('/api/incidents')) as response:
        page.get_by_role('button', name='Submit incident', exact=True).click()
    assert response.value.status == 201
    incident = response.value.json()
    expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
    checks.append('manual submission persisted, literal untrusted text rendered safely')
    expect(page.get_by_role('heading', name='Retrieved evidence only', exact=True)).to_be_visible(timeout=90000)
    expect(page.get_by_text('No language model was used.', exact=False)).to_be_visible()
    assert page.locator('details').count() == 5
    page.locator('summary').first.click()
    expect(page.locator('pre').first).to_be_visible()
    diagnosis_response = context.request.get(base + '/api/incidents/' + incident['id'] + '/diagnosis')
    diagnosis = diagnosis_response.json()
    assert diagnosis_response.status == 200 and diagnosis['mode'] == 'RETRIEVAL_ONLY'
    checks.append('real POST → outbox → Kafka → worker → five evidence chunks → GET diagnosis')
    page.screenshot(path=str(output / 'detail.png'), full_page=True)
    page.get_by_role('button', name='Back to incidents', exact=False).click()
    page.get_by_label('Service', exact=True).fill(service)
    page.get_by_role('button', name='Apply service', exact=True).click()
    page.get_by_label('Severity', exact=True).select_option('CRITICAL')
    page.get_by_label('Status', exact=True).select_option('RECEIVED')
    expect(page.locator('tbody tr')).to_have_count(1)
    expect(page.get_by_role('button', name=title, exact=True)).to_be_visible()
    checks.append('combined server-side severity, status, service filters')
    page.get_by_label('Service', exact=True).fill('nonexistent-' + str(uuid.uuid4()))
    page.get_by_role('button', name='Apply service', exact=True).click()
    expect(page.get_by_role('heading', name='No incidents found')).to_be_visible()
    checks.append('empty filtered result')
    page.get_by_role('button', name='Clear filters').click()
    expect(page.get_by_role('table')).to_be_visible()
    if page.get_by_role('button', name='Next', exact=True).is_enabled():
        page.get_by_role('button', name='Next', exact=True).click()
        expect(page.get_by_text('Page 2 of', exact=False)).to_be_visible()
        page.get_by_role('button', name='Previous', exact=True).click()
    checks.append('pagination')
    # Real creation outside the page must appear through its periodic refresh.
    fresh_title = 'Periodic refresh ' + str(uuid.uuid4())[:8]
    result = context.request.post(base + '/api/incidents', data={'service':service,'title':fresh_title,'description':'HTTP 500 errors from database timeout','severity':'HIGH'})
    assert result.status == 201
    expect(page.get_by_role('button', name=fresh_title, exact=True)).to_be_visible(timeout=20000)
    checks.append('periodic refresh discovers a real externally created incident')
    # Browser-only failure injection: no application or database changes.
    page.route('**/api/incidents?*', lambda route: route.fulfill(status=503, content_type='application/problem+json', body='{"detail":"UI test outage"}'))
    page.get_by_role('button', name='Refresh', exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('UI test outage')
    page.unroute('**/api/incidents?*')
    page.get_by_role('button', name='Retry', exact=True).click()
    expect(page.get_by_role('table')).to_be_visible()
    expect(page.get_by_role('alert')).to_have_count(0)
    checks.append('UI-only simulated API error and retry recovery')
    # Verify generated mode presentation without claiming a live Ollama model.
    generated = dict(diagnosis, mode='GENERATED', provider='ollama', model='ui-test-fixture', summary='UI-only generated diagnosis fixture', likelyCauses=[{'text':'Inspect the connection pool','sources':['database-failures.md']}])
    page.route('**/api/incidents/' + incident['id'] + '/diagnosis', lambda route: route.fulfill(json=generated))
    page.goto(base + '/?incident=' + incident['id'])
    expect(page.get_by_role('heading', name='AI-generated diagnosis', exact=True)).to_be_visible()
    expect(page.get_by_role('heading', name='Suggested remediation')).to_be_visible()
    expect(page.get_by_text('Inspect the connection pool', exact=True)).to_be_visible()
    checks.append('UI-only generated-mode fixture, citations and human-review notice')
    page.unroute('**/api/incidents/' + incident['id'] + '/diagnosis')
    page.goto(base + '/?incident=' + incident['id'])
    expect(page.get_by_role('heading', name='Retrieved evidence only', exact=True)).to_be_visible()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(output / 'mobile.png'), full_page=True)
    checks.append('mobile layout and direct incident URL')
    page.goto(base + '/?incident=' + str(uuid.uuid4()))
    expect(page.get_by_role('alert')).to_contain_text('Incident not found')
    checks.append('real missing-incident error state')
    assert not errors, errors
    browser.close()
report={'checks_passed':len(checks),'checks':checks,'incident_id':incident['id'],'actual_mode':diagnosis['mode'],'browser_errors':errors}
(output / 'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
