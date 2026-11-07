# Step 8B actual static verification

Executed locally on 2026-11-07 against application commit 38db6b05d8378d671c42bd9b66f5768904059e01. [Structured results/source hashes](verification.json), [architecture/setup/costs](README.md).

**No Azure authentication or deployment was performed.** No Azure credentials/account/CLI, Terraform plan/apply/destroy, Azure image push or Kubernetes apply was used. Software/provider/schema downloads were public endpoints. No Azure resource or backend was created. Static success is not evidence of a deployable cloud environment or an approved bill.

## Checks actually passed

| Check | Actual result |
| --- | --- |
| Terraform tool archive | Terraform 1.12.2 Linux amd64 matched official SHA256SUMS before extraction |
| `terraform fmt -recursive`, then `fmt -check -recursive` | Passed for root and all five modules |
| `terraform init -backend=false -input=false` | Passed; installed AzureRM 4.30.0 and generated the real dependency lock |
| Credential-isolated repeat `init -backend=false -input=false -lockfile=readonly` | Passed; reused locked provider; no backend configured |
| `terraform validate -no-color` | `Success! The configuration is valid.` |
| `python3 scripts/verify-terraform-azure.py` | Passed using temporary HOME/CLI config and filtered environment; executes only fmt/init/validate plus offline tests |
| Parsed-HCL/static integration tests | **10 passed**, including private AKS/vault, managed identities, scoped roles/federation, CIDR separation, no cloud data sources/secret values, ignored state/plans, CSI wiring and renderer refusal cases |
| Azure committed Kustomize template | **19 resources valid, 0 invalid/errors/skipped**, strict Kubernetes 1.35 + custom CRD schemas |
| Nonsecret generated example overlay | Same **19 valid, 0 invalid/errors/skipped**; no apply |
| SecretProviderClass custom schema | Upstream Secrets Store CSI Driver v1.4.8 CRD; SHA256 ef1623b34403bb11311fc92763b5b364ba456a166f1637eeec8d29052dd115f3 |
| Existing local Kustomize | **17 resources valid**, cross-resource checks passed; **9 negative/positive manifest tests passed** |
| Shell/Python syntax and Git whitespace | Passed |

Static-tool dependencies are isolated/pinned in tests/requirements.txt: python-hcl2 7.3.1, lark 1.2.2, regex 2026.11.7 and PyYAML 6.0.2. Docker installs them into ignored workspace tooling; no application dependencies/global host environment changed. Terraform's actual lock, examples and sanitized evidence are intentional tracked files. Providers, temporary overlays, state/plans, private tfvars and credential configurations remain excluded.

## Regression checks actually executed

- `./scripts/test-api.sh`: **62 JUnit tests, zero failures/errors/skips**, BUILD SUCCESS; includes isolated real PostgreSQL integration.
- `./scripts/test-worker.sh`: **77 pytest tests passed in 9.40s**, including real local embeddings/database retrieval. Ten unchanged runbooks skipped on ingestion.
- Existing frontend test image `npm test && npm run build`: **7 tests passed**, strict TypeScript/Vite production build passed.
- `bash scripts/test-dashboard.sh`: **14 browser checks passed**, zero browser errors; actual mode RETRIEVAL_ONLY. UI-only generated-mode fixture remains separate from live generation.
- Fault/benchmark/alert-observer helper tests: **8 + 8 + 3 = 19 passed**.
- `python3 scripts/verify-api.py`: **12 HTTP checks passed**.
- Real `python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY`: HTTP 201 → outbox → Kafka → worker → stored diagnosis HTTP 200; one receipt/diagnosis, five snapshots, unchanged diagnosis/evidence after duplicate. Final incident fe07425c-8a49-4b69-b83d-54944923e00e; event 85bd7889-34db-45c0-aafa-19f47b593c51; duplicate offset 102, committed 103.
- `docker compose config --quiet`: valid; normal Compose unchanged.

The expensive distributed-fault/automatic-alert/live-Ollama workflows were not repeated for this infrastructure-only change. Their existing helper/application unit coverage ran; no application source changed. These real application integration checks used Compose, **not AKS**, and retained synthetic fixtures.

## Failures investigated before final success

The first validate command was started before provider initialization finished and correctly reported Missing required provider; after init completed, validation passed. No Azure configuration/API error was inferred from that ordering mistake.

The example Key Vault placeholder initially exceeded its 24-character name constraint; shortened it to replace-vault and rerendered successfully. A static parser helper initially overwrote previous blocks sharing a resource type, making its role assertion fail despite the actual assignments being present; merging blocks fixed the observer, and all ten tests passed on rerun.

Several host Python invocations hit the recurring WSL working-directory/path initialization error. Running the final isolated verification from stable /tmp with absolute project paths passed. Host pip was absent; documented tooling uses Docker instead. No tests are counted as passed from those interrupted invocations.

One RAG observer Docker exec exited 137 while the normal worker restarted. Logs showed the known CommitFailedError/UnknownMemberIdError, then group rejoin and duplicate handling for the same event. The worker reported OOM=false; resource inspection showed recovery. The diagnosis had committed before the failure; a fresh full RAG/replay rerun passed. The historical/root membership-expiry trigger remains unresolved; no production logic was changed to suppress commit errors. This is consistent with the tested fail-closed, at-least-once recovery documented in Step 7C, not exactly-once Kafka delivery.

## Preservation and untested boundaries

Normal services ended healthy/running (publisher has no Docker health check); provider none confirmed. PostgreSQL remains on localhost:55432. Original postgres_data/kafka_data timestamps are 2026-11-06T00:00:34Z; prometheus_data/grafana_data 2026-11-06T01:22:39Z; alertmanager_data 2026-11-06T01:58:52Z; ollama_data 2026-11-06T16:26:37Z. No data/volume was deleted or copied to cloud. Existing Compose, API, worker, frontend, Kubernetes base and local overlay source files are unchanged.

Still untested: subscription/tenant correctness and permissions; provider registration; regional Kubernetes/VM support and quota; global name uniqueness; OIDC deployer bootstrap and role propagation; AKS private-network access, scheduling and health; ACR publishing/pulls; private DNS/Key Vault endpoint reachability; real workload-identity federation and CSI Secret synchronization/rotation; managed disk provisioning/persistence; remote-state security; backups/HA; runtime cost and the complete Azure incident flow. All example UUIDs/references are nonworking placeholders. Static schemas do not establish admission-policy compliance or cloud feasibility. Future cloud operations require explicit authorization and a cost review.
