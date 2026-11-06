#!/usr/bin/env bash
set -u
missing=0
for tool in docker java python3 mvn node npm; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "$tool: $(command -v "$tool")"
    case "$tool" in
      java) java -version || missing=1 ;;
      mvn) mvn -version || missing=1 ;;
      *) "$tool" --version || missing=1 ;;
    esac
  else
    echo "$tool: missing"
    missing=1
  fi
done
if command -v docker >/dev/null 2>&1; then
  docker compose version || missing=1
  docker info >/dev/null 2>&1 || { echo 'Docker daemon unavailable'; missing=1; }
fi
exit "$missing"
