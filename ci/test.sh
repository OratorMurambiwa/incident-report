#!/usr/bin/env bash
# Local equivalents of the three test stages, isolated even on a developer machine.
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"
source ci/tool-versions.env
action="${1:?java, python or frontend}"
case "$action" in java|python|frontend) ;; *) exit 2;; esac
export DOCKER_CONFIG="$root/.incidentiq-backups/ci/docker"
export COMPOSE_FILE="$root/ci/compose.yaml"
export COMPOSE_DISABLE_ENV_FILE=1
export COMPOSE_PROJECT_NAME="incidentiq-ci-$(python3 -c 'import secrets;print(secrets.token_hex(6))')"
export CI_POSTGRES_PASSWORD
CI_POSTGRES_PASSWORD=$(python3 -c 'import secrets;print(secrets.token_hex(24))')
export TEST_REPORT_DIR="$root/.incidentiq-backups/ci/reports"
cache="${CI_CACHE_DIR:-/tmp/incidentiq-ci-cache-$(id -u)}"
mkdir -p "$TEST_REPORT_DIR/java" "$TEST_REPORT_DIR/python" "$TEST_REPORT_DIR/frontend" "$cache/maven" "$cache/npm"
chmod a+rwx "$TEST_REPORT_DIR/python"
cleanup() {
  # This shell's random private project only. No -v, prune, shared network or named data volume.
  docker compose down --timeout 10 || true
}
trap cleanup EXIT
if [[ "$action" == frontend ]]; then
  docker run --rm --memory 512m --cpus 1 -v "$root/frontend:/app" -v "$cache/npm:/root/.npm" \
    -v "$TEST_REPORT_DIR/frontend:/reports" -w /app "$NODE_IMAGE" sh -ec \
    'npm ci --cache /root/.npm && npx tsc -p tsconfig.test.json && node --test --test-reporter=junit --test-reporter-destination=/reports/react.xml .test-build/domain.test.js && npm run build'
else
  docker compose up -d --wait postgres
  args=(--rm --memory 1536m --cpus 2 -e "JAVA_TOOL_OPTIONS=-Xmx512m -XX:ActiveProcessorCount=2" --network "${COMPOSE_PROJECT_NAME}_default" -v "$root/api:/source:ro" -v "$cache/maven:/root/.m2" -v "$TEST_REPORT_DIR/java:/reports" -w /workspace
    -e RUN_DATABASE_TESTS=true -e SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/incidentiq_api_test
    -e SPRING_DATASOURCE_USERNAME=incidentiq_ci -e SPRING_DATASOURCE_PASSWORD="$CI_POSTGRES_PASSWORD")
  # Python's own fresh DB needs real Flyway migration. Reuse existing integration suite.
  test_args=()
  if [[ "$action" == python ]]; then test_args=(-Dtest=PostgresIntegrationTest); fi
  # A Linux working directory also lets HotSpot/Mockito verify attach-file ownership;
  # NTFS bind-mount ownership can prevent dynamic agent attachment on WSL.
  docker run "${args[@]}" "$MAVEN_IMAGE" bash -ec '
    set -euo pipefail
    cp /source/pom.xml /workspace/
    cp -R /source/src /workspace/
    status=0
    mvn --batch-mode --no-transfer-progress verify "$@" || status=$?
    shopt -s nullglob
    reports=(target/surefire-reports/TEST-*.xml)
    if (( ${#reports[@]} )); then cp "${reports[@]}" /reports/; fi
    exit "$status"
  ' -- "${test_args[@]}"
  if [[ "$action" == python ]]; then
    ./scripts/test-worker.sh
    docker run --rm --entrypoint python incidentiq-worker-tests:local -m pip check
  fi
fi
