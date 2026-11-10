"""Capture the actual React UI with one synthetic incident, without private list data.
Run in the existing optional Playwright image. No mocked routes, DOM replacement,
saved browser sessions or remediation execution. Synthetic UUID masked at capture.
"""
import hashlib
import json
from pathlib import Path
import uuid
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, expect

output = Path('/output')
service = 'portfolio-demo-' + uuid.uuid4().hex[:8]
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--no-sandbox'])
    context = browser.new_context(locale='en-US', timezone_id='UTC',
                                  viewport={'width': 1360, 'height': 1000}, device_scale_factor=1)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://frontend')
    expect(page.get_by_role('heading', name='Incident workspace')).to_be_visible()
    page.get_by_role('button', name='+ Report incident').click()
    page.get_by_label('Service', exact=True).fill(service)
    title = 'Database connection pool exhausted'
    page.get_by_label('Title', exact=True).fill(title)
    page.get_by_label('Description', exact=True).fill(
        'Synthetic portfolio demo: PostgreSQL rejects new connections with too many clients '
        'and SQLSTATE 08006. Requests time out while the application connection pool is exhausted. '
        'Investigate connection concurrency and recent configuration changes. No production data.')
    page.get_by_label('Severity', exact=True).select_option('HIGH')
    with page.expect_response(lambda response: response.request.method == 'POST'
                              and response.url.endswith('/api/incidents')) as created:
        page.get_by_role('button', name='Submit incident', exact=True).click()
    assert created.value.status == 201
    incident = created.value.json()
    expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
    expect(page.get_by_role('heading', name='Retrieved evidence only', exact=True)).to_be_visible(timeout=90000)
    expect(page.get_by_text('No language model was used.', exact=False)).to_be_visible()
    expect(page.get_by_text('RECEIVED', exact=True)).to_be_visible()
    response = context.request.get('http://frontend/api/incidents/' + incident['id'] + '/diagnosis')
    assert response.status == 200
    diagnosis = response.json()
    assert diagnosis['mode'] == 'RETRIEVAL_ONLY' and diagnosis['provider'] == 'none'
    assert len(diagnosis['retrievedEvidence']) == 5
    assert not diagnosis['likelyCauses'] and not diagnosis['suggestedRemediation']
    assert set(diagnosis['citedRunbooks']) <= {e['source'] for e in diagnosis['retrievedEvidence']}
    expect(page.locator('details')).to_have_count(5)
    expect(page.get_by_role('table')).to_have_count(0)
    page.locator('summary').first.click()
    expect(page.locator('pre').first).to_be_visible()
    assert not errors, errors
    output.mkdir(parents=True, exist_ok=True)
    image = output / 'dashboard.png'
    page.screenshot(path=str(image), full_page=True, mask=[page.locator('.id')],
                    mask_color='#dbe2ea', animations='disabled')
    report = {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
              'incident_id': incident['id'], 'service': service,
              'submission_status': 201, 'diagnosis_status': response.status,
              'mode': diagnosis['mode'], 'evidence_chunks': 5,
              'cited_runbooks': diagnosis['citedRunbooks'], 'browser_errors': errors,
              'mocked_responses': False, 'synthetic_input_only': True,
              'redaction': 'Synthetic incident UUID masked during browser screenshot; no other visual editing.',
              'screenshot_sha256': hashlib.sha256(image.read_bytes()).hexdigest()}
    (output / 'capture.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    browser.close()
