#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml ps -a
docker compose -f compose.yaml exec -T postgres sh -ec '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
    -c "SELECT current_database(), current_user;" \
    -c "SELECT extname, extversion FROM pg_extension WHERE extname = '\''vector'\'';" \
    -c "SELECT '\''[1,2,3]'\''::vector <-> '\''[1,2,4]'\''::vector AS vector_distance;"
'
docker compose -f compose.yaml exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:29092 --describe --topic incidents.raw
docker compose -f compose.yaml exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:29092 --describe --topic incidents.analyzed
docker compose -f compose.yaml exec -T kafka /bin/bash -ec '
  topic="incidentiq-smoke-$(cat /proc/sys/kernel/random/uuid)"
  kafka=/opt/kafka/bin
  "$kafka/kafka-topics.sh" --bootstrap-server kafka:29092 --create --topic "$topic" --partitions 1 --replication-factor 1
  trap '\''"$kafka/kafka-topics.sh" --bootstrap-server kafka:29092 --delete --topic "$topic"'\'' EXIT
  printf "%s\n" "incidentiq-smoke-ok" | "$kafka/kafka-console-producer.sh" --bootstrap-server kafka:29092 --topic "$topic" --producer-property acks=all
  received=$("$kafka/kafka-console-consumer.sh" --bootstrap-server kafka:29092 --topic "$topic" --from-beginning --max-messages 1 --timeout-ms 20000)
  printf "Consumed: %s\n" "$received"
  test "$received" = "incidentiq-smoke-ok"
'
