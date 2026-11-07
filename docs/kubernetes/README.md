# Step 8A: isolated local Kubernetes with Kustomize

**Manifest validation passed. Kubernetes deployment and its incident smoke test remain unverified.** The current 7.2 GiB WSL host has about 3.75 GiB available with Compose running, below the conservative 6 GiB available-memory gate. No cluster was created, workload applied, model downloaded or Compose service stopped for Kubernetes. See [actual checks](VERIFICATION.md) and [recorded preflight](preflight.json).

## Layout and isolation

`infra/kubernetes/base` defines six singleton workloads (API, publisher, worker, frontend, PostgreSQL/pgvector, Kafka), five internal Services and a runbook-ingestion Job. `overlays/local` adds namespace **incidentiq-local**. `runbooks/kustomization.yaml` generates a hashed ConfigMap from the existing ten Markdown files without duplicating them. Other hashed ConfigMaps contain runtime settings, dependency checks and Kubernetes-specific nginx configuration. No changes are made to normal Compose or applied Flyway migrations.

PostgreSQL and Kafka are separate single-replica StatefulSets, each with a new 2 GiB ReadWriteOnce claim and explicit Retain policies. Claims require a working default dynamic StorageClass. There are no hostPath mounts, external databases, ExternalName/LoadBalancer/NodePort Services, host ports or Compose networks. Kubernetes DNS names `postgres:5432`, `kafka:29092` and `api:8080` resolve inside this namespace. Kubernetes uses database incidentiq_k8s_local, a separate consumer group and its own Kafka incident.created topic. Existing Compose PostgreSQL remains at localhost:55432.

The Secret **database-credentials** is an external reference, not committed YAML. The helper creates a random password in memory and passes it to kubectl on stdin; it preserves an existing Secret. Never import Compose's .env or credentials. The fresh PostgreSQL image initializes its own database/user; Flyway V4 creates pgvector. No pre-existing database or public.runbook_chunks data is reused. Changing a Secret alone does not rotate the password of an initialized PostgreSQL volume.

## Dependencies, migrations and probes

API is the sole migration owner: one replica, Recreate rollout, Flyway defaults enabled and Hibernate validate. It waits for its own PostgreSQL before startup. Publisher explicitly disables Flyway and waits for successful V1–V6 migration history plus a functioning Kafka topic. Worker waits for that history, committed corpus fingerprints matching every mounted runbook, at least five chunks, and topic creation/availability. The pinned image's chunking-version constant is inspected without importing the heavy embedding stack. Real ingestion is idempotent and commits the full corpus atomically; the Job runs after schema readiness. Topic setup is idempotent even when two init containers race.

Startup probes allow up to five minutes before liveness/readiness begin. API liveness uses /actuator/health/liveness; readiness uses aggregate /actuator/health including PostgreSQL. Worker probes reach its existing metrics server, started after model/consumer initialization. They do not prove Kafka progress or diagnosis quality. Non-web publisher probes only test PID 1 existence: startup dependencies and outbox monitoring, not that probe, establish delivery readiness. PostgreSQL uses local TCP pg_isready. Kafka uses local TCP startup/liveness and a real Kafka CLI readiness check; its headless Service publishes unready addresses to avoid controller-DNS bootstrap deadlock. fsGroup 1000 matches the inspected Kafka image user. Frontend uses /healthz and proxies to the API Service; Docker's 127.0.0.11 resolver is removed only in this mounted nginx configuration.

Every application/init container has CPU and memory requests/limits. Steady main-container memory limits total 3008 MiB; ingestion temporarily adds up to 1024 MiB, plus control-plane/system overhead. PostgreSQL shared_buffers=32MB/max_connections=40; Kafka heap 128–256 MiB; API heap 128–256 MiB; publisher heap 64–128 MiB; each worker/ingestion cap 1024 MiB. CPU limits bound inference. The 6 GiB **available**, not total, gate reserves control-plane/headroom. It is conservative, not a measured Kubernetes minimum. Do not lower it or stop existing services just to claim deployment success on this host.

## Validation without a cluster

Uses installed kubectl (Kustomize embedded), existing worker image (locked PyYAML) and checksum-verified kubeconform v0.6.7. Linux amd64 setup, small tool download only:

```bash
mkdir -p .incidentiq-backups/kubernetes/tools
# Run downloads/checksum in a temporary directory, then copy only the tool:
validation_tmp=$(mktemp -d)
curl -fsSL https://github.com/yannh/kubeconform/releases/download/v0.6.7/kubeconform-linux-amd64.tar.gz -o "$validation_tmp/kubeconform-linux-amd64.tar.gz"
curl -fsSL https://github.com/yannh/kubeconform/releases/download/v0.6.7/CHECKSUMS -o "$validation_tmp/CHECKSUMS"
(cd "$validation_tmp" && rg ' kubeconform-linux-amd64.tar.gz$' CHECKSUMS | sha256sum -c -)
tar -xzf "$validation_tmp/kubeconform-linux-amd64.tar.gz" -C .incidentiq-backups/kubernetes/tools kubeconform
python3 scripts/kubernetes-preflight.py
./scripts/validate-kubernetes.sh
docker run --rm --network none -v "$PWD:/repo:ro" --entrypoint python incidentiq-worker:local \
  -m unittest discover -s /repo/infra/kubernetes/tests -v
```

Validation renders only; it never calls a cluster API. Strict kubeconform schemas target Kubernetes 1.35.0. Initial schema retrieval needs public GitHub access; subsequent schemas are cached under ignored .incidentiq-backups/kubernetes. Cross-resource checks cover namespace isolation, Secret/ConfigMap references, Service selectors/ports, fixed image references, probes, resource bounds, migration gates and storage. All five referenced images must exist locally. Existing API/worker/frontend Dockerfiles build/test the application and cache local MiniLM weights. No registry account is needed.

## Future deployment on a machine with sufficient headroom

The following are **instructions, not completed deployment evidence**. Install a compatible kind release from its official distribution and use a kubectl version within the supported server skew (current client 1.36.1; target server 1.35.0). Ensure adequate disk space for the node image and imported application images. No default-context deployment is used.

```bash
# Build current app images with the existing Docker-only workflows first:
docker compose build api worker frontend
python3 scripts/kubernetes-preflight.py
# Proceed ONLY when cluster_attempt_allowed is true.
kind create cluster --name incidentiq-dev --image kindest/node:v1.35.0 \
  --config infra/kubernetes/kind.yaml
./scripts/kubernetes-local.sh deploy
./scripts/kubernetes-local.sh status
./scripts/kubernetes-local.sh smoke
```

The helper rechecks memory, named kind-cluster membership and a loopback API server before loading existing images, provisioning the Secret, applying manifests and waiting for all rollouts/ingestion. It does not create a cluster automatically. Failures stop deployment and preserve PVCs. A kubeconfig administrator could misconfigure context names; inspect the selected context before use. Secret read errors also fail safely at Secret creation rather than replacing credentials.

The smoke helper temporarily forwards **localhost:18082** to frontend and creates one synthetic incident through nginx→API→outbox→Kafka→worker. It requires HTTP RETRIEVAL_ONLY/RECEIVED plus exactly one published outbox/receipt/diagnosis and five snapshots in the Kubernetes database. The incident is retained. It does not execute remediation. The port-forward is stopped by a shell trap.

For interactive browsing:

```bash
kubectl --context kind-incidentiq-dev -n incidentiq-local port-forward --address 127.0.0.1 svc/frontend 18082:80
# http://localhost:18082
```

On upgrades, stop only the dedicated Kubernetes worker/publisher before API migrations; verify migration success, rerun ingestion, then restore their single replicas. Do not run an old worker against a changing schema or edit applied migrations. Job pod templates are immutable: if runbooks/config change, explicitly delete/recreate only job/runbook-ingest in the dedicated context/namespace after reviewing its status, then apply the updated overlay. No script deletes Jobs, PVCs, namespaces or clusters automatically. ConfigMap subPath changes require a frontend restart; reloading local-tag images likewise requires loading them into kind and restarting affected workloads.

## Data retention and limitations

Do not delete the namespace, PVCs, PVs, kind node container, cluster or Docker volumes without explicit data-disposal authorization. StatefulSet Retain preserves claims when its controller is removed; deleting a claim or cluster can still destroy node-local storage. No cleanup command that deletes data is provided. Leave the isolated environment intact for diagnosis.

This is local development, not production HA: one database, one Kafka broker/partition, plaintext intra-cluster networking, local PostgreSQL owner credentials, default StorageClass, no backups/TLS/NetworkPolicy/Ingress and no managed secret provider. Service-account token automount is disabled. Existing image entrypoints retain their required user/volume behavior; this is not a full pod-security hardening exercise. Image tags are pinned versions/local tags with actual IDs recorded; they are not immutable release digests. Load freshly built local images explicitly.

Prometheus/Grafana/Alertmanager and Ollama remain in existing Compose and are not deployed by this overlay. Frontend monitoring links retain their existing localhost destinations and refer to that separate monitoring stack, not Kubernetes metrics. Baseline diagnoses use provider none only. At-least-once delivery/idempotent receipts remain unchanged. Schema validation cannot establish scheduling, PVC provisioning, CoreDNS, Kafka restart persistence or a functioning Kubernetes incident flow; these remain runtime verification tasks.

References: [Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/), [init containers](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/), [probe semantics](https://kubernetes.io/docs/concepts/workloads/pods/probes/), [kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/), [kubeconform](https://github.com/yannh/kubeconform/tree/v0.6.7).
