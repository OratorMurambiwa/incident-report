#!/usr/bin/env bash
# Render and validate without contacting a Kubernetes API or changing Compose.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .incidentiq-backups/kubernetes/schemas
tools="$PWD/.incidentiq-backups/kubernetes/tools"
if [[ ! -x "$tools/kubeconform" ]]; then
  echo 'Install checksum-verified kubeconform v0.6.7 as documented in docs/kubernetes/README.md' >&2
  exit 1
fi
kubectl kustomize infra/kubernetes/overlays/local > .incidentiq-backups/kubernetes/rendered.yaml
"$tools/kubeconform" -strict -summary -kubernetes-version 1.35.0 \
  -cache .incidentiq-backups/kubernetes/schemas .incidentiq-backups/kubernetes/rendered.yaml
# PyYAML is already pinned in the existing worker image; no new host dependency.
docker run --rm --network none -v "$PWD:/repo:ro" --entrypoint python incidentiq-worker:local \
  /repo/scripts/validate-kubernetes.py /repo/.incidentiq-backups/kubernetes/rendered.yaml
for image in incidentiq-api:local incidentiq-worker:local incidentiq-frontend:local \
  pgvector/pgvector:0.8.7-pg16-trixie apache/kafka:3.9.1; do
  docker image inspect "$image" --format '{{.RepoTags}} {{.Id}}'
done
