#!/usr/bin/env bash
# Build locally and scan. Never tag for ACR, log in, push or deploy.
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"
export DOCKER_CONFIG="$root/.incidentiq-backups/ci/docker"
source "$root/ci/tool-versions.env"
tools="$root/.incidentiq-backups/ci/tools"
reports="$root/.incidentiq-backups/ci/reports/security"
cache="${CI_CACHE_DIR:-$root/.incidentiq-backups/ci/cache}"
mkdir -p "$reports" "$cache/trivy"
cd /tmp
images=()
for component in api worker frontend; do
  image="incidentiq-ci-$component:verification"
  docker build --progress=plain -t "$image" "$root/$component"
  images+=("$image")
done
python3 "$root/ci/security.py" "${images[@]}" > "$reports/config-checks.json"
# Baseline CVEs are reported, not silently suppressed. Scanner/DB errors still fail.
# No ignore file, continueOnError or ignored vulnerability severities.
for image in "${images[@]}"; do
  name="${image%%:*}"
  "$tools/trivy" image --cache-dir "$cache/trivy" --timeout 15m --parallel 1 \
    --scanners vuln --format json --output "$reports/$name.json" --exit-code 0 "$image"
done
python3 - "$reports" <<'PY'
import json,sys
from pathlib import Path
report={}
for path in Path(sys.argv[1]).glob('incidentiq-ci-*.json'):
 d=json.loads(path.read_text());counts={}
 for result in d.get('Results',[]):
  for v in result.get('Vulnerabilities',[]):counts[v['Severity']]=counts.get(v['Severity'],0)+1
 report[path.stem]=counts
print(json.dumps({'vulnerability_inventory':report,'policy':'Advisory baseline; release remains hard blocked pending triage and an approved enforcement policy.'},indent=2))
Path(sys.argv[1],'summary.json').write_text(json.dumps(report,indent=2)+'\n')
PY
