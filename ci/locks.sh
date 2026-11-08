#!/usr/bin/env bash
# Static JS bundles omit dependency manifests; scan the source lockfile separately.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cache="${CI_CACHE_DIR:-$root/.incidentiq-backups/ci/cache}"
reports="$root/.incidentiq-backups/ci/reports/security"
mkdir -p "$reports"
cd /tmp
"$root/.incidentiq-backups/ci/tools/trivy" fs --cache-dir "$cache/trivy" --timeout 10m --parallel 1 \
  --scanners vuln --include-dev-deps --skip-dirs node_modules --skip-dirs dist --skip-dirs .test-build \
  --format json --output "$reports/frontend-lockfile.json" --exit-code 0 "$root/frontend"
