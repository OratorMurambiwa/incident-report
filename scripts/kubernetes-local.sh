#!/usr/bin/env bash
# Explicitly targets only the dedicated local kind cluster. Never touches Compose.
set -euo pipefail
cd "$(dirname "$0")/.."
action="${1:-status}"
case "$action" in deploy|status|smoke) ;; *) echo 'Usage: scripts/kubernetes-local.sh deploy|status|smoke' >&2; exit 2;; esac
context=kind-incidentiq-dev
namespace=incidentiq-local
if [[ "$action" == deploy ]]; then
  python3 scripts/kubernetes-preflight.py
  python3 - <<'PY'
import importlib.util
s=importlib.util.spec_from_file_location('gate','scripts/kubernetes-preflight.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
if not m.inspect()['cluster_attempt_allowed']:
    raise SystemExit('Insufficient headroom: validation only. Do not stop Compose or delete data to bypass this gate.')
PY
fi
command -v kind >/dev/null || { echo 'Dedicated kind cluster/tool is unavailable' >&2; exit 1; }
kind get clusters | grep -Fx incidentiq-dev >/dev/null
server=$(kubectl --context "$context" config view --minify -o jsonpath='{.clusters[0].cluster.server}')
[[ "$server" == https://127.0.0.1:* ]] || { echo 'Refusing a non-loopback Kubernetes API' >&2; exit 1; }
k=(kubectl --context "$context" -n "$namespace")
if [[ "$action" == deploy ]]; then
  ./scripts/validate-kubernetes.sh
  for image in incidentiq-api:local incidentiq-worker:local incidentiq-frontend:local \
    pgvector/pgvector:0.8.7-pg16-trixie apache/kafka:3.9.1; do
    kind load docker-image --name incidentiq-dev "$image"
  done
  kubectl --context "$context" apply -f infra/kubernetes/overlays/local/namespace.yaml
  # Preserve an existing credential: changing it cannot rotate an initialized PG volume.
  if ! "${k[@]}" get secret database-credentials >/dev/null 2>&1; then
    python3 - <<'PY' | "${k[@]}" create -f -
import json,secrets
print(json.dumps({'apiVersion':'v1','kind':'Secret','metadata':{'name':'database-credentials','namespace':'incidentiq-local'},'type':'Opaque','stringData':{'POSTGRES_USER':'incidentiq_k8s','POSTGRES_PASSWORD':secrets.token_urlsafe(32)}}))
PY
  fi
  "${k[@]}" apply -k infra/kubernetes/overlays/local
  "${k[@]}" rollout status statefulset/postgres --timeout=600s
  "${k[@]}" rollout status statefulset/kafka --timeout=600s
  "${k[@]}" rollout status deployment/api --timeout=600s
  "${k[@]}" wait --for=condition=complete job/runbook-ingest --timeout=600s
  for name in publisher worker frontend; do "${k[@]}" rollout status "deployment/$name" --timeout=600s; done
elif [[ "$action" == smoke ]]; then
  "${k[@]}" port-forward --address 127.0.0.1 svc/frontend 18082:80 > /tmp/incidentiq-k8s-port-forward.log 2>&1 &
  forward_pid=$!
  trap 'kill "$forward_pid" 2>/dev/null || true' EXIT
  python3 scripts/smoke-kubernetes.py
else
  "${k[@]}" get pods,services,pvc,jobs
fi
