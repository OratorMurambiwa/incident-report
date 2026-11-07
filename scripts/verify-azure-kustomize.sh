#!/usr/bin/env bash
# Public schema downloads only. Never reads kube credentials or applies manifests.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/.incidentiq-backups/terraform/python-tools"
mkdir -p .incidentiq-backups/azure/schemas
crd=.incidentiq-backups/azure/secretproviderclass-crd.yaml
curl -fsSL --max-time 30 https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/v1.4.8/config/crd/bases/secrets-store.csi.x-k8s.io_secretproviderclasses.yaml -o "$crd"
python3 - <<'PY'
from pathlib import Path
import hashlib,json,yaml
p=Path('.incidentiq-backups/azure/secretproviderclass-crd.yaml')
print('Upstream CRD SHA256:',hashlib.sha256(p.read_bytes()).hexdigest())
d=yaml.safe_load(p.read_text())
s=next(v['schema']['openAPIV3Schema'] for v in d['spec']['versions'] if v['name']=='v1')
Path('.incidentiq-backups/azure/schemas/secretproviderclass.json').write_text(json.dumps(s))
PY
python3 scripts/render-azure-overlay.py --config docs/azure/kustomize-config.example.json \
  --release-tag static-verification --output .incidentiq-backups/azure/rendered --example
for source in infra/kubernetes/overlays/azure .incidentiq-backups/azure/rendered; do
  kubectl kustomize "$source" > .incidentiq-backups/azure/validation.yaml
  .incidentiq-backups/kubernetes/tools/kubeconform -strict -summary -kubernetes-version 1.35.0 \
    -schema-location default -schema-location '.incidentiq-backups/azure/schemas/{{.ResourceKind}}.json' \
    .incidentiq-backups/azure/validation.yaml
done
