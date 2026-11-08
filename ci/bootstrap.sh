#!/usr/bin/env bash
# Install public, version-pinned tools in ignored workspace storage. Never logs in.
set -euo pipefail
cd "$(dirname "$0")/.."
source ci/tool-versions.env
mode="${1:-basic}"
case "$mode" in basic|infra|security) ;; *) exit 2;; esac
root="$PWD"
mkdir -p .incidentiq-backups/ci/tools .incidentiq-backups/ci/docker/cli-plugins
export DOCKER_CONFIG="$root/.incidentiq-backups/ci/docker"
tools="$root/.incidentiq-backups/ci/tools"
# Download only if absent; each downloaded archive/binary must match upstream SHA256.
if [[ ! -x "$DOCKER_CONFIG/cli-plugins/docker-compose" ]]; then
  curl -fsSL --retry 3 --max-time 120 "https://github.com/docker/compose/releases/download/v$COMPOSE_VERSION/docker-compose-linux-x86_64" -o "$tools/compose"
  curl -fsSL --retry 3 --max-time 30 "https://github.com/docker/compose/releases/download/v$COMPOSE_VERSION/docker-compose-linux-x86_64.sha256" -o "$tools/compose.sha256"
  expected=$(awk '{print $1}' "$tools/compose.sha256")
  echo "$expected  $tools/compose" | sha256sum -c -
  install -m 755 "$tools/compose" "$DOCKER_CONFIG/cli-plugins/docker-compose"
fi
docker compose version
if [[ "$mode" == infra ]]; then
  mkdir -p .incidentiq-backups/terraform/tools .incidentiq-backups/terraform/python-tools .incidentiq-backups/kubernetes/tools
  tf="$root/.incidentiq-backups/terraform/tools/terraform"
  if [[ ! -x "$tf" ]]; then
    curl -fsSL --retry 3 --max-time 120 "https://releases.hashicorp.com/terraform/$TERRAFORM_VERSION/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" -o "$tools/terraform.zip"
    curl -fsSL --retry 3 --max-time 30 "https://releases.hashicorp.com/terraform/$TERRAFORM_VERSION/terraform_${TERRAFORM_VERSION}_SHA256SUMS" -o "$tools/terraform.sums"
    expected=$(awk -v f="terraform_${TERRAFORM_VERSION}_linux_amd64.zip" '$2==f {print $1}' "$tools/terraform.sums")
    test -n "$expected"; echo "$expected  $tools/terraform.zip" | sha256sum -c -
    python3 - "$tools/terraform.zip" "$root/.incidentiq-backups/terraform/tools" <<'PY'
import sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:z.extract('terraform',sys.argv[2])
PY
    chmod +x "$tf"
  fi
  if [[ ! -x "$tools/kubectl" ]]; then
    curl -fsSL --retry 3 --max-time 120 "https://dl.k8s.io/release/v$KUBECTL_VERSION/bin/linux/amd64/kubectl" -o "$tools/kubectl"
    curl -fsSL --retry 3 --max-time 30 "https://dl.k8s.io/release/v$KUBECTL_VERSION/bin/linux/amd64/kubectl.sha256" -o "$tools/kubectl.sha256"
    echo "$(cat "$tools/kubectl.sha256")  $tools/kubectl" | sha256sum -c -
    chmod +x "$tools/kubectl"
  fi
  kcf="$root/.incidentiq-backups/kubernetes/tools/kubeconform"
  if [[ ! -x "$kcf" ]]; then
    curl -fsSL --retry 3 --max-time 120 "https://github.com/yannh/kubeconform/releases/download/v$KUBECONFORM_VERSION/kubeconform-linux-amd64.tar.gz" -o "$tools/kubeconform.tar.gz"
    curl -fsSL --retry 3 --max-time 30 "https://github.com/yannh/kubeconform/releases/download/v$KUBECONFORM_VERSION/CHECKSUMS" -o "$tools/kubeconform.sums"
    expected=$(awk '$2=="kubeconform-linux-amd64.tar.gz" {print $1}' "$tools/kubeconform.sums")
    test -n "$expected";echo "$expected  $tools/kubeconform.tar.gz" | sha256sum -c -
    tar -xzf "$tools/kubeconform.tar.gz" -C "$(dirname "$kcf")" kubeconform
  fi
  docker run --rm --user 0 -v "$root/.incidentiq-backups/terraform/python-tools:/tools" \
    -v "$root:/repo:ro" \
    --entrypoint python "$PYTHON_TOOLS_IMAGE" -m pip install --no-cache-dir --upgrade --target /tools -r /repo/ci/requirements.txt
  curl -fsSL --retry 3 --max-time 30 "https://raw.githubusercontent.com/microsoft/azure-pipelines-vscode/$AZURE_PIPELINE_SCHEMA_COMMIT/service-schema.json" -o "$tools/azure-pipelines-schema.json"
  echo "$AZURE_PIPELINE_SCHEMA_SHA256  $tools/azure-pipelines-schema.json" | sha256sum -c -
elif [[ "$mode" == security ]]; then
  if [[ ! -x "$tools/trivy" ]]; then
    curl -fsSL --retry 3 --max-time 120 "https://github.com/aquasecurity/trivy/releases/download/v$TRIVY_VERSION/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" -o "$tools/trivy.tar.gz"
    curl -fsSL --retry 3 --max-time 30 "https://github.com/aquasecurity/trivy/releases/download/v$TRIVY_VERSION/trivy_${TRIVY_VERSION}_checksums.txt" -o "$tools/trivy.sums"
    expected=$(awk -v f="trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" '$2==f {print $1}' "$tools/trivy.sums")
    test "$expected" = "$TRIVY_SHA256"
    echo "$TRIVY_SHA256  $tools/trivy.tar.gz" | sha256sum -c -
    tar -xzf "$tools/trivy.tar.gz" -C "$tools" trivy
  fi
fi
