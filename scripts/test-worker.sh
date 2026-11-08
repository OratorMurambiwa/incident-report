#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Run test-api.sh first: it creates/migrates the isolated database using the actual Flyway migrations.
docker compose exec -T postgres sh -ec '
  psql -U "$POSTGRES_USER" -d incidentiq_api_test -v ON_ERROR_STOP=1 -c "SELECT event_id FROM incidentiq_api.processed_events LIMIT 0" >/dev/null
'
docker build --target test -t incidentiq-worker-tests:local ./worker
postgres_id=$(docker compose ps -q postgres)
project=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$postgres_id")
export POSTGRES_USER POSTGRES_PASSWORD
POSTGRES_USER=$(docker compose exec -T postgres printenv POSTGRES_USER)
POSTGRES_PASSWORD=$(docker compose exec -T postgres printenv POSTGRES_PASSWORD)
worker_test_args=(--rm --network "${project}_default"
  -e POSTGRES_HOST=postgres -e POSTGRES_PORT=5432
  -e POSTGRES_DB=incidentiq_api_test -e POSTGRES_USER -e POSTGRES_PASSWORD
  -v "$PWD/runbooks:/runbooks:ro")
docker run "${worker_test_args[@]}" incidentiq-worker-tests:local python ingest.py /runbooks
pytest_args=(-q)
if [[ -n "${TEST_REPORT_DIR:-}" ]]; then
  mkdir -p "$TEST_REPORT_DIR/python"
  chmod a+rwx "$TEST_REPORT_DIR/python"
  worker_test_args+=(-v "$TEST_REPORT_DIR/python:/reports")
  pytest_args+=(--junitxml=/reports/pytest.xml)
fi
docker run "${worker_test_args[@]}" -e LLM_PROVIDER=none -e RUN_DATABASE_TESTS=true -e RUN_RETRIEVAL_TESTS=true \
  incidentiq-worker-tests:local python -m pytest "${pytest_args[@]}"
