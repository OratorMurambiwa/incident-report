# Step 8B: future Azure infrastructure, static verification only

**Nothing has been provisioned or authenticated to Azure.** No account was created; no Azure credentials, Azure CLI, Terraform plan/apply/destroy, Kubernetes apply or image push was used. The files describe a future billable development environment, not a deployed system. [Actual verification](VERIFICATION.md).

## Architecture and modules

Terraform root: `infra/terraform/azure`. Terraform **1.12.2** and AzureRM **4.30.0** are deliberately pinned; the real provider dependency lock is committed. No dependency upgrade is implied by this scaffold. Future operators must review provider security fixes, supported AKS versions/SKUs and regional availability before authorizing any cloud operation.

| Component | Design |
| --- | --- |
| Root | Dedicated resource group, scoped role assignments and OIDC federation; no Kubernetes/Helm provider |
| network | 10.42.0.0/16 VNet; AKS subnet 10.42.0.0/22; private endpoints 10.42.4.0/24; node NSG with Azure default rules |
| identities | Separate user-assigned control-plane, kubelet and Key Vault workload identities; no client secrets |
| registry | ACR Basic, admin/anonymous access disabled; authenticated public HTTPS endpoint |
| aks | Private API, public API FQDN disabled, Entra/Azure RBAC, local accounts disabled, OIDC/workload identity, Key Vault CSI add-on and Azure Policy |
| vault | RBAC, public access disabled, private endpoint and private DNS/VNet link, purge protection and 90-day soft delete; no secret values in Terraform |

The control-plane identity gets Network Contributor only on the node subnet and Managed Identity Operator only on the kubelet identity. Kubelet gets AcrPull only on this registry. The workload identity gets Key Vault Secrets User only on this dedicated vault; do not put unrelated secrets in it. Federation subject is `system:serviceaccount:<namespace>:incidentiq-keyvault`, audience `api://AzureADTokenExchange`, issuer from AKS. Role propagation and identity bootstrap ordering remain cloud-runtime checks.

AKS uses Azure CNI overlay/Calico, pod CIDR 10.244.0.0/16 and service CIDR 10.43.0.0/16. Ranges do not overlap but are fixed in these modules; review them against any future peering/VPN. NSG default VNet access is not application microsegmentation. Outbound standard Load Balancer connectivity supports registry, Entra and platform updates; it is not restricted-egress networking. A private-network runner or separately approved connectivity is needed to access the private API and seed Key Vault; this repository does not create a VPN, bastion or runner.

## Variables and outputs

Every variable has an inline description; names, node bounds and identifiers have local validations. Required inputs: subscription_id, tenant_id, unique_suffix (4–10 lowercase alphanumerics), and at least one existing admin_group_object_ids UUID. They identify future resources; they are not credentials. `terraform.tfvars.example` contains all-zero documentation UUIDs, not working account identifiers.

Defaults: name_prefix incidentiq (3–10 lowercase alphanumerics starting with a letter), location eastus, Kubernetes 1.35, Standard_D4s_v5, one fixed node, namespace incidentiq-azure. Node count is limited to 1–3; no autoscaler can silently expand it. A single node has no HA, and upgrades may temporarily add a surge node. The VM size/node count do not guarantee workload fit; requests, system overhead and rollout capacity need a future plan/runtime review. Namespace and service-account federation must match the overlay.

Outputs expose only resource-group/cluster names, registry hostname, vault URI and a nonsecret `kustomize_config` object (namespace, tenant ID, workload client ID, vault name, registry). There are no kubeconfig, passwords, tokens or registry-admin outputs. Provider state must still be treated as sensitive even without such outputs. No cloud data sources or Key Vault secret resources read values into state.

## Static setup and reproduction

All downloads are public software/schema endpoints, not Azure management/data APIs. Tools live under ignored .incidentiq-backups. No host Java/Maven or global Python packages are installed. Existing Docker supplies Python/pip for the static parser tooling; existing kubectl/Kustomize and kubeconform are from Step 8A.

```bash
mkdir -p .incidentiq-backups/terraform/tools .incidentiq-backups/terraform/python-tools
tf_tool_tmp=$(mktemp -d)
curl -fsSL https://releases.hashicorp.com/terraform/1.12.2/terraform_1.12.2_linux_amd64.zip -o "$tf_tool_tmp/terraform_1.12.2_linux_amd64.zip"
curl -fsSL https://releases.hashicorp.com/terraform/1.12.2/terraform_1.12.2_SHA256SUMS -o "$tf_tool_tmp/SHA256SUMS"
(cd "$tf_tool_tmp" && rg ' terraform_1.12.2_linux_amd64.zip$' SHA256SUMS | sha256sum -c -)
python3 - "$tf_tool_tmp/terraform_1.12.2_linux_amd64.zip" <<'PY'
import sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    archive.extract('terraform','.incidentiq-backups/terraform/tools')
PY
chmod +x .incidentiq-backups/terraform/tools/terraform
docker run --rm --user 0 -v "$PWD/.incidentiq-backups/terraform/python-tools:/tools" \
  -v "$PWD/infra/terraform/azure/tests/requirements.txt:/requirements.txt:ro" \
  --entrypoint python incidentiq-worker:local -m pip install --no-cache-dir --target /tools -r /requirements.txt
python3 scripts/verify-terraform-azure.py
./scripts/verify-azure-kustomize.sh
```

The Terraform helper runs **fmt -check -recursive, init -backend=false -input=false -lockfile=readonly, validate** with a temporary HOME/CLI configuration and a filtered environment, discarding inherited ARM/AZURE credentials, CLI caches and plugin overrides. It never executes plan/apply/destroy. Initial provider initialization generated the real lock file; repeat checks refuse lock changes. Init downloads signed provider software and module metadata but does not configure a backend, authenticate a subscription or create state/resources. Static tests parse HCL and Kustomize; they are not mocked successful Azure operations.

The Azure schema helper renders both the committed template and a nonsecret example-generated overlay, then validates all resources against Kubernetes 1.35 schemas plus the upstream Secrets Store CSI Driver v1.4.8 SecretProviderClass CRD. It contacts public schema sources only. The local overlay is tested separately and unchanged.

## Kustomize integration and future-only setup

`infra/kubernetes/overlays/azure` reuses the Step 8A base but has a separate namespace, database/group, ACR references, workload-identity ServiceAccount, SecretProviderClass and CSI mounts on **all secret-consuming main/init containers**. The existing envFrom reference database-credentials is synchronized from CSI-mounted Key Vault objects. It references external secrets named **incidentiq-postgres-user** and **incidentiq-postgres-password**, with aliases mapped to POSTGRES_USER/POSTGRES_PASSWORD. Terraform deliberately does not create, read or output their values.

Only a future authorized operator with private-vault network access and narrowly scoped secret-write permission may seed those values. CSI mounting must succeed before a database-consuming container starts. This bootstrap/rotation behavior has not been exercised on AKS. All five consumers share one read identity scoped to this dedicated vault; stronger per-workload/per-secret isolation is a future hardening task. CSI copies credentials into a Kubernetes Secret because the existing apps use environment variables; those copies require cluster RBAC protection. Updating Key Vault/CSI does not refresh process environment variables or rotate an initialized PostgreSQL user's password: coordinate DB credential rotation and pod restarts explicitly.

The overlay sets PostgreSQL/Kafka claims to 8 GiB using AKS managed-csi. Base singleton storage/migration safety remains: API alone runs Flyway, publisher disables it, worker waits for schema/current corpus/topic, claims retained. PostgreSQL/Kafka stay self-hosted; there is no Azure PostgreSQL/Event Hubs substitution, data migration, backup service or import of Compose records. Frontend/API remain internal ClusterIP Services; no public ingress/TLS endpoint is created.

Before any future cloud work, obtain explicit authorization and a budget, review the design/provider versions, establish federated Terraform deployment identity with scoped resource/RBAC permissions, register necessary resource providers, and prepare secure remote state. Provider config disables Azure CLI/MSI credential discovery and expects OIDC for future automation. No future credential setup has been performed here. `resource_provider_registrations = "none"` prevents automatic provider registration; missing registrations will need separate authorized administration. Existing Entra groups and release/push permissions are prerequisites, not created accounts.

No active backend is configured. `backend.tf.example` is an **unloaded** remote-state design using Entra/OIDC, never account keys/SAS. A private encrypted state account/container, access control, locking and recovery must be independently reviewed/bootstrap-authorized before deployment. Do not use an unprotected local state file for a shared cloud environment. State, plans, private tfvars and CLI configs are gitignored; the real .terraform.lock.hcl is tracked. Never export secrets/state/kubeconfig to tracked docs or put them in Terraform variables.

After a future authorized infrastructure rollout (not part of this task), use its nonsecret kustomize_config output and a specific release tag with the renderer. For static examples only:

```bash
PYTHONPATH=.incidentiq-backups/terraform/python-tools python3 scripts/render-azure-overlay.py \
  --config docs/azure/kustomize-config.example.json --release-tag static-verification \
  --output .incidentiq-backups/azure/rendered --example
kubectl kustomize .incidentiq-backups/azure/rendered
```

For real output, omit --example; the renderer rejects zero/example references, local/system namespaces and latest/local tags. It writes only under ignored .incidentiq-backups/azure and performs no login, build/push or apply. Future release automation must publish all five image repositories (including mirrored pgvector/Kafka) to ACR using separately scoped push identity, verify digests and replace placeholder tags before rollout. The current overlay uses version/release tags, not enforced immutable digests. ACR/kubelet pulls and image architecture compatibility remain untested.

Do not use the local kind deployment helper against Azure. No Azure apply helper is provided. Workload rollout, CSI installation/rotation, private DNS, scoped RBAC, storage provisioning/persistence and a real incident smoke test require separately authorized Azure verification. Local monitoring/Ollama are not deployed by this overlay; frontend localhost monitoring links are not Azure monitoring endpoints. Existing Docker Compose configuration, databases, volumes and port 55432 remain unchanged.

## Expected billing and limits

This is **not free infrastructure**, despite the AKS Free control-plane tier. No price estimate or spending guarantee is claimed; region, currency, offer, usage and future pricing must be checked at approval time.

| Expected item | Billable dimensions / limitations |
| --- | --- |
| AKS system node(s) | Default one Standard_D4s_v5 VM, managed 64 GiB OS disk; up to three configured nodes and temporary upgrade surge costs |
| Kubernetes persistent storage | Two 8 GiB requested managed disks for PostgreSQL/Kafka; billed disk tiers/rounding and retained disks can outlive pods |
| ACR Basic | Registry tier, image storage/transfer/egress; no private endpoint support at Basic; public HTTPS requires Entra auth |
| Key Vault | Secret reads/rotation polling; private endpoint hours/data and private DNS zone/queries |
| AKS networking | Standard outbound Load Balancer/public IP, processed/outbound data; AKS-managed private networking/DNS resources may add charges |
| Optional future additions | Remote-state storage, private runners/VPN, monitoring/log ingestion, backups, TLS/Ingress, HA/more nodes all add costs and are not provisioned here |

ACR Premium plus private endpoints is a higher-cost future change if private registry networking is required. Private API/Key Vault reduce exposure but require operator connectivity not included here. AKS Free lacks the paid-tier uptime SLA; one VM and singleton DB/broker are unsuitable for production HA. Stopping application pods does not stop VM/disk/registry/network billing. Budgets/alerts, log retention, backups, disk expansion, restricted NetworkPolicies, admission enforcement and disaster recovery are not implemented. Key Vault purge protection means deletion cannot immediately erase retained contents or release its name; do not disable retention simply to simplify cleanup. No destroy/data-deletion command is executed or automated.

Official references: [AKS tiers/pricing](https://azure.microsoft.com/en-us/pricing/details/kubernetes-service/), [ACR SKU capabilities](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus), [Key Vault pricing](https://azure.microsoft.com/en-us/pricing/details/key-vault/), [Private Link pricing](https://azure.microsoft.com/en-us/pricing/details/private-link/), [Key Vault CSI/workload identity](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-identity-access), [pinned provider](https://github.com/hashicorp/terraform-provider-azurerm/tree/v4.30.0/website/docs/r), [Terraform state security](https://developer.hashicorp.com/terraform/language/state/sensitive-data).
