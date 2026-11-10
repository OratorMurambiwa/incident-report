"""Offline portfolio link/evidence checks; no application or database changes."""
import hashlib
import json
from pathlib import Path
import re
import struct
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parents[2]
readme = (root / 'README.md').read_text()
checked = []
documents = {'README.md', 'docs/architecture.md', 'docs/portfolio/VERIFICATION.md'}
documents.update(str(p.relative_to(root)) for p in (root / 'docs').rglob('*.md')
                 if 'verification' in p.name.lower() or p.name in {'RESULTS.md', 'environment.md'})
for name in sorted(documents):
    document = root / name
    content = document.read_text()
    # Portfolio documents use inline links without escaped parentheses/reference syntax.
    for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', content):
        url = urlsplit(target)
        if url.scheme:
            assert url.scheme in {'http', 'https'}, target
            continue
        path = (document.parent / unquote(url.path)).resolve() if url.path else document
        assert path.is_relative_to(root), target
        assert path.is_file(), f'{name}: missing {target}'
        current = root
        for part in path.relative_to(root).parts:
            assert part in {entry.name for entry in current.iterdir()}, f'{name}: wrong GitHub path case {target}'
            current = current / part
        if url.fragment:
            headings = re.findall(r'^#{1,6}\s+(.+)$', path.read_text(), re.M)
            anchors = {re.sub(r'[^\w\- ]', '', h.lower()).replace(' ', '-') for h in headings}
            assert unquote(url.fragment) in anchors, f'{name}: missing anchor {target}'
        checked.append({'document': name, 'target': target})

capture = json.loads((root / 'docs/images/capture.json').read_text())
png = (root / 'docs/images/dashboard.png').read_bytes()
assert png[:8] == b'\x89PNG\r\n\x1a\n'
width, height = struct.unpack('>II', png[16:24])
assert width == 1360 and height >= 1000
assert hashlib.sha256(png).hexdigest() == capture['screenshot_sha256']
assert capture['synthetic_input_only'] and not capture['mocked_responses']
assert capture['mode'] == 'RETRIEVAL_ONLY' and capture['evidence_chunks'] == 5
assert capture['submission_status'] == 201 and capture['diagnosis_status'] == 200
assert not capture['browser_errors']

benchmark_root = root / 'docs/benchmarks/runs/20261107t181836z_e97e5b4b'
benchmark = json.loads((benchmark_root / 'summary.json').read_text())
assert json.loads((benchmark_root / 'status.json').read_text())['complete']
assert benchmark['async']['expected'] == 60 and benchmark['async']['failures'] == 0
for category in ['read', 'write']:
    data = benchmark[category]
    for field in ['requests_per_second', 'avg_ms', 'p95_ms', 'p99_ms']:
        assert f"{data[field]:.2f}" in readme, (category, field)
for field in ['avg_ms', 'p95_ms', 'p99_ms']:
    assert f"{benchmark['async']['latency'][field]:,.2f}" in readme, field

security = json.loads((root / 'docs/security/triage.json').read_text())
rows = [r for image in security['images'].values() for r in image['rows'] if r['disposition'] == 'present']
assert len(rows) == 50 and len({r['cve'] for r in rows}) == 14
assert sum(i['before_ch_occurrences'] for i in security['images'].values()) == 144
assert sum(i['after_ch_occurrences'] for i in security['images'].values()) == 50
assert '50 critical/high occurrences remain' in readme
assert 'November 8, 2026 UTC' in readme and 'not a current-date rescan' in readme
faults = json.loads((root / 'docs/faults/runs/20261108t015220z_fde9792c/results.json').read_text())
assert faults['complete'] and len(faults['cases']) == 8
assert faults['committed_diagnoses'] == faults['valid_events'] == 10
assert faults['duplicate_handlings'] == 7 and faults['data_loss'] == 0
for case in faults['cases']:
    assert f"{case['recovery_seconds']:.3f} s" in readme, case['case']
assert 'No organization pipeline execution' in readme
assert 'No cluster created' in readme
assert 'AI recommendations require human review' in readme
assert 'incidents.raw' in readme and 'legacy/reserved' in readme
assert '55432' in readme
result = {'relative_links_checked': len(checked), 'links': checked,
          'screenshot_dimensions': [width, height], 'screenshot_hash_verified': True,
          'benchmarks_match_recorded_results': True, 'fault_results_match_recorded_run': True,
          'security_occurrences': 50, 'distinct_remaining_cves': 14,
          'limitation': 'Offline relative-link and evidence checks; live URLs and Mermaid rendering are checked separately.'}
print(json.dumps(result, indent=2))
