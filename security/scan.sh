#!/usr/bin/env bash
# Compare with one frozen public database. Never update or suppress findings.
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
phase="${1:?before or after}"
case "$phase" in before|after) ;; *) exit 2;; esac
cache="${SECURITY_DB_CACHE:?Set the frozen Trivy cache directory (db and java-db)}"
output="$root/.incidentiq-backups/security/8d/$phase"
mkdir -p "$output"
export DOCKER_CONFIG="$root/.incidentiq-backups/ci/docker"
cd /tmp
for component in api worker frontend; do
  "$root/.incidentiq-backups/ci/tools/trivy" image --cache-dir "$cache" --timeout 15m --parallel 1 \
    --skip-db-update --skip-java-db-update --offline-scan --skip-version-check --image-src docker --scanners vuln --list-all-pkgs \
    --format json --output "$output/$component.json" --exit-code 0 "incidentiq-security-$component:$phase"
done
