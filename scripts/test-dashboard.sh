#!/usr/bin/env bash
# Runs a real browser against existing containers. Retains synthetic incidents.
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -t incidentiq-browser:local ./infra/browser
frontend_id=$(docker compose ps -q frontend)
project=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$frontend_id")
mkdir -p .incidentiq-backups/dashboard
docker run --rm --network "${project}_default" --ipc=host \
  -v "$PWD/scripts/verify-dashboard.py:/verify.py:ro" \
  -v "$PWD/.incidentiq-backups/dashboard:/evidence" \
  --entrypoint python incidentiq-browser:local /verify.py
