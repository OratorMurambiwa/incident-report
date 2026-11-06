#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null 2>&1 || { echo 'Docker is required. See README.md.' >&2; exit 1; }
docker compose version
docker info >/dev/null
if [ ! -f .env ]; then cp .env.example .env; fi
docker compose "$@" config --quiet
docker compose "$@" up -d --wait
docker compose "$@" ps -a
