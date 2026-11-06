#!/usr/bin/env bash
# Runs all JUnit tests, including PostgreSQL integration tests, using Docker only.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --wait postgres
# Reuse an isolated test database; test transactions roll back. Never touch application rows.
docker compose exec -T postgres sh -ec '
  exists=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1 FROM pg_database WHERE datname = '\''incidentiq_api_test'\''")
  if [ "$exists" != 1 ]; then
    createdb -U "$POSTGRES_USER" incidentiq_api_test
  fi
'
docker build --target build -t incidentiq-api-tests:local ./api
postgres_id=$(docker compose ps -q postgres)
project=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$postgres_id")
export SPRING_DATASOURCE_USERNAME
export SPRING_DATASOURCE_PASSWORD
SPRING_DATASOURCE_USERNAME=$(docker compose exec -T postgres printenv POSTGRES_USER)
SPRING_DATASOURCE_PASSWORD=$(docker compose exec -T postgres printenv POSTGRES_PASSWORD)
docker run --rm --network "${project}_default" \
  -e RUN_DATABASE_TESTS=true \
  -e SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/incidentiq_api_test \
  -e SPRING_DATASOURCE_USERNAME -e SPRING_DATASOURCE_PASSWORD \
  --entrypoint mvn incidentiq-api-tests:local --batch-mode --no-transfer-progress test
