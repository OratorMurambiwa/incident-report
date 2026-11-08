#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
source "$root/ci/tool-versions.env"
export DOCKER_CONFIG="$root/.incidentiq-backups/ci/docker"
export PATH="$root/.incidentiq-backups/ci/tools:$PATH"
export PYTHONPATH="$root/.incidentiq-backups/terraform/python-tools"
# Stable CWD and absolute source paths avoid stale Windows-mount Python import paths.
cd /tmp
python3 "$root/scripts/verify-terraform-azure.py"
"$root/scripts/verify-azure-kustomize.sh"
mkdir -p "$root/.incidentiq-backups/kubernetes/schemas"
kubectl kustomize "$root/infra/kubernetes/overlays/local" > "$root/.incidentiq-backups/kubernetes/rendered.yaml"
"$root/.incidentiq-backups/kubernetes/tools/kubeconform" -strict -summary -kubernetes-version 1.35.0 \
  -cache "$root/.incidentiq-backups/kubernetes/schemas" "$root/.incidentiq-backups/kubernetes/rendered.yaml"
python3 "$root/scripts/validate-kubernetes.py" "$root/.incidentiq-backups/kubernetes/rendered.yaml"
docker run --rm --network none -v "$root:/repo:ro" \
  -e PYTHONPATH=/repo/.incidentiq-backups/terraform/python-tools --entrypoint python "$PYTHON_TOOLS_IMAGE" \
  -m unittest discover -s /repo/infra/kubernetes/tests -v
python3 "$root/ci/validate-pipeline.py"
python3 -m unittest discover -s "$root/ci/tests" -v
python3 -m unittest discover -s "$root/faults" -p 'test_*.py' -v
python3 -m unittest discover -s "$root/benchmarks" -p 'test_*.py' -v
python3 -m unittest discover -s "$root/scripts" -p 'test_alert_smoke.py' -v
