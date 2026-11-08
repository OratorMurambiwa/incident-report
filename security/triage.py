#!/usr/bin/env python3
"""Account for every CH occurrence without ignoring findings or mixing database snapshots."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMPORTANT = {'HIGH', 'CRITICAL'}
DIRECT_PYTHON = {'langchain', 'langchain-core', 'kafka-python', 'sentence-transformers',
                 'transformers', 'torch'}


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_database(cache: Path, expected: dict) -> None:
    for name, record in expected.items():
        path = cache / name
        if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
            raise ValueError(f'Frozen database changed: {name}')


def findings(report: dict, important_only: bool = False) -> list[dict]:
    return [dict(v, target=r['Target'], ecosystem=r['Type'])
            for r in report.get('Results', []) for v in r.get('Vulnerabilities', [])
            if not important_only or v['Severity'] in IMPORTANT]


def inventory(report: dict) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for section in report.get('Results', []):
        for package in section.get('Packages', []):
            result.setdefault(package['Name'], []).append(package)
    return result


def package_version(package: dict) -> str:
    # OS inventories split epoch/release; omitting them hides the security revision.
    return ((str(package['Epoch']) + ':') if package.get('Epoch') else '') + package['Version'] + (('-' + package['Release']) if package.get('Release') else '')


def classify(image: str, finding: dict) -> str:
    package = finding['PkgName']
    if finding['ecosystem'] in {'debian', 'ubuntu', 'alpine'}:
        return 'base-image OS package (source-level matching; see duplicate group)'
    if package == 'org.postgresql:postgresql':
        return 'direct runtime JDBC dependency'
    if image == 'api':
        return ('transitive: Spring Kafka → kafka-clients → compression codec' if 'lz4' in package or 'snappy' in package
                else 'transitive: Spring Boot starter-web → Tomcat / starter-json / Spring MVC')
    if package in {'jaraco.context', 'wheel'}:
        return 'vendored inside setuptools (path recorded below)'
    if package == 'setuptools':
        return 'before: Torch/base transitive requirement; after: explicit security pin (Torch requires it on Python 3.12)'
    return 'direct application requirement' if package in DIRECT_PYTHON else 'transitive Python dependency'


def advisory_url(finding: dict) -> str:
    vendors = {'debian': 'https://security-tracker.debian.org/tracker/',
               'ubuntu': 'https://ubuntu.com/security/',
               'alpine': 'https://security.alpinelinux.org/vuln/'}
    if finding['ecosystem'] in vendors:
        return vendors[finding['ecosystem']] + finding['VulnerabilityID']
    return next((url for url in finding.get('References', []) if '/security/advisories/' in url),
                'https://nvd.nist.gov/vuln/detail/' + finding['VulnerabilityID'])


def compare(image: str, before: dict, after: dict, policy: dict) -> dict:
    old, new = findings(before), findings(after)
    old_ch, new_ch = findings(before, True), findings(after, True)
    after_packages = inventory(after)
    old_packages = inventory(before)
    rows = []
    for v in old_ch:
        advisory = policy[v['VulnerabilityID']]  # Unreviewed findings must fail, never disappear silently.
        still = [n for n in new if (n['PkgName'], n['VulnerabilityID']) == (v['PkgName'], v['VulnerabilityID'])]
        packages = after_packages.get(v['PkgName'], [])
        old_meta = old_packages.get(v['PkgName'], [{}])[0]
        source = old_meta.get('SrcName') or v['PkgName']
        status = 'present' if still else ('package absent from inventory' if not packages else 'not detected in updated package')
        rows.append({'cve': v['VulnerabilityID'], 'severity': v['Severity'], 'package': v['PkgName'],
                     'source_package': source, 'dependency': classify(image, v),
                     'path': v.get('PkgPath') or v['target'], 'before_version': v['InstalledVersion'],
                     'scanner_fixed_versions': v.get('FixedVersion') or None,
                     'after_versions': sorted({package_version(p) for p in packages}),
                     'disposition': status, 'after_severities': sorted({s['Severity'] for s in still}),
                     'duplicate_group': image + '/' + source + '/' + v['VulnerabilityID'],
                     'scanner_title': v.get('Title'),
                     'scanner_primary_url': v.get('PrimaryURL'),
                     'advisory_reference': advisory_url(v),
                     **advisory})
    old_keys = {(v['PkgName'], v['VulnerabilityID']) for v in old_ch}
    added = [v for v in new_ch if (v['PkgName'], v['VulnerabilityID']) not in old_keys]
    for v in added:
        if v['VulnerabilityID'] not in policy:
            raise ValueError('New unreviewed CH finding: ' + v['VulnerabilityID'])
    return {'before_counts': dict(Counter(v['Severity'] for v in old)),
            'after_counts': dict(Counter(v['Severity'] for v in new)),
            'before_ch_occurrences': len(old_ch), 'after_ch_occurrences': len(new_ch),
            'before_unique_ch_cves': len({v['VulnerabilityID'] for v in old_ch}),
            'after_unique_ch_cves': len({v['VulnerabilityID'] for v in new_ch}),
            'duplicate_source_groups': dict(Counter(r['duplicate_group'] for r in rows)),
            'before_image_id': before['Metadata']['ImageID'], 'after_image_id': after['Metadata']['ImageID'],
            'before_created': before['CreatedAt'], 'after_created': after['CreatedAt'],
            'rows': rows, 'new_ch_findings': added}


def markdown(report: dict) -> str:
    lines = ['# Critical/high triage ledger', '',
             'Every baseline occurrence is retained below, including repeated binary/library rows. Counts are scanner occurrences, not independent exploitable defects. Fixed versions are the frozen scanner’s values; an empty value means none supplied, not that no upstream patch exists. Current exposure is configuration-specific, not proof of non-exploitability.', '',
             'Full structured conditions, current exposure, paths, source duplicate groups and reasons for deferral: [triage.json](triage.json). Public advisory links retain each scanner title even where metadata needs correction. No finding is suppressed.', '']
    for image, data in report['images'].items():
        lines += [f'## {image}', '',
                  f"CH occurrences: {data['before_ch_occurrences']} → {data['after_ch_occurrences']}; distinct CH CVEs: {data['before_unique_ch_cves']} → {data['after_unique_ch_cves']}.", '',
                  '| Advisory | Package (before → after) | Scanner fix | Upstream fix (when separately reviewed) | Disposition |', '|---|---|---|---|---|']
        for row in data['rows']:
            after = ', '.join(row['after_versions']) or 'absent'
            lines.append(f"| [{row['cve']}]({row['advisory_reference']}) ({row['severity']}) | {row['package']} {row['before_version']} → {after} | {row['scanner_fixed_versions'] or 'not supplied'} | {', '.join(row.get('upstream_fixed_versions', [])) or 'see scanner fix'} | {row['disposition']} |")
        lines += ['', '### Conditions and deferrals', '']
        seen = set()
        for row in data['rows']:
            if row['cve'] in seen:
                continue
            seen.add(row['cve'])
            lines += [f"- **{row['cve']}**: {row['exploit_conditions']} {row['application_exposure']}" + (' Deferred: '+row['deferred_reason'] if row['deferred_reason'] else '')]
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--reports', type=Path, default=ROOT / '.incidentiq-backups/security/8d')
    args = parser.parse_args()
    snapshot = json.loads((ROOT / 'docs/security/database-snapshot.json').read_text())
    verify_database(args.cache, snapshot)
    policy = json.loads((ROOT / 'security/policy.json').read_text())
    report = {'scanner': 'Trivy 0.69.3', 'same_database_verified': True,
              'database_files': snapshot, 'images': {}, 'suppression': False}
    for image in ('api', 'worker', 'frontend'):
        paths = {phase: args.reports / phase / f'{image}.json' for phase in ('before', 'after')}
        reports = {phase: json.loads(path.read_text()) for phase, path in paths.items()}
        for value in reports.values():
            if value['Trivy']['Version'] != '0.69.3':
                raise ValueError('Scanner version changed')
        result = compare(image, reports['before'], reports['after'], policy)
        result['raw_report_sha256'] = {phase: digest(path) for phase, path in paths.items()}
        report['images'][image] = result
    output = ROOT / 'docs/security'
    (output / 'triage.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'TRIAGE.md').write_text(markdown(report))
    print(json.dumps({image: {k: v for k, v in data.items() if k.endswith('counts') or k.endswith('occurrences')}
                      for image, data in report['images'].items()}, indent=2))


if __name__ == '__main__':
    main()
