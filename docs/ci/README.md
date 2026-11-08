# Step 8C: Azure DevOps CI, release disabled

`azure-pipelines.yml` defines five default stages and a disabled future-release gate. No Azure DevOps organization, service connection, credential, registry publish or deployment is configured or accessed by this change. [Actual local verification](VERIFICATION.md).

| Stage | Checks and reports |
| --- | --- |
| Java | Maven 3.9.11/Java 21 container, real isolated PostgreSQL/pgvector, `mvn verify`, all JUnit tests, JUnit XML export |
| Python | A fresh private DB seeded through the existing ten PostgreSQL/Flyway integration tests, existing `scripts/test-worker.sh`, real embeddings/retrieval/DB pytest tests, `pip check`, pytest JUnit XML |
| React | Locked `npm ci`, existing TypeScript test configuration/Node tests, JUnit output, strict TypeScript/Vite production build |
| Infrastructure | Credential-filtered Terraform fmt/init-backend=false/validate and parsed-HCL tests, local/Azure Kustomize schemas including CSI CRD, local-manifest and pipeline policy tests |
| DockerSecurity | Build existing API/worker/frontend Dockerfiles locally, block source credential patterns and baked credential/nonroot-app violations, run pinned Trivy vulnerability inventories, scan the frontend lockfile separately, publish JSON reports only |

First four stages can run independently on separate Microsoft-hosted Ubuntu 24.04 agents. DockerSecurity depends on all four. Hosted parallel-job grants, billing/quotas, GitHub repository authorization, checkout, Cache/TestResults/Artifact tasks and real server-side expansion require an Azure DevOps organization and remain unverified. No organization/account or paid capacity was created here. Agent image updates and built-in task major versions are Microsoft-managed; this is not a fully hermetic build.

## Test isolation and resource bounds

`ci/test.sh` always creates its own random `incidentiq-ci-<hex>` project using **ci/compose.yaml**, disables .env loading and generates an ephemeral DB password. Its only dependency service is PostgreSQL/pgvector in a private bridge network with tmpfs data. No host port, external network, hostPath/data volume or existing Compose database is referenced. The CI database name is incidentiq_api_test on its own server; it is not the similarly named database in normal Compose. The password is never saved, logged, cached or published.

The exit trap runs `down` only for this shell's private project, without --volumes or prune. Its disposable DB is lost on shutdown by design; existing named volumes are never deleted. Hard agent termination may bypass a shell trap; hosted-agent disposal handles that test environment. On a self-hosted runner, inspect leftover incidentiq-ci project labels explicitly; never use global pruning.

Maven copies read-only source into a container-local Linux working directory, exports only JUnit XML and is bounded to 1536 MiB/two CPUs, JVM heaps to 512 MiB, PostgreSQL to 512 MiB/one CPU, frontend to 512 MiB/one CPU. Worker builds/tests follow the existing Dockerfile; run local equivalents serially on the 7.2 GiB host. Docker image builds/scans are serial. Cold dependency/model/Java advisory databases can require several GB disk and substantial download/build time. CI does not start Kafka/API/worker production services or run fault injection against them.

The existing worker script changed only to support an optional TEST_REPORT_DIR. With no such variable its ordinary workflow is unchanged. Source test suites and applied migrations are reused; Python's private migration seed reruns ten Java tests, not a second full Java suite. The Dockerfile build tests may skip DB-specific cases; only the explicitly database-enabled stages establish integration counts.

## Pinned tools and caches

Versions live in ci/tool-versions.env: Maven 3.9.11/Java 21, Node 22.14.0, Python tooling 3.12.11, Terraform 1.12.2, kubectl 1.36.1, kubeconform 0.6.7, Compose 2.39.2, Trivy 0.69.3. Static tooling dependencies are pinned separately in ci/requirements.txt; runtime dependency locks are unchanged. Existing runtime Dockerfiles retain their established base tags; semantic tags/base package indexes can change and are not immutable image digests.

Bootstrap downloads versioned public binaries and verifies upstream SHA256. Trivy additionally has its exact archive digest recorded in the versions file, matching its immutable 0.69.3 release and [upstream clean-version advisory](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23). No third-party scanner action/latest tag is used. Existing downloaded tool paths are trusted local caches; use fresh caches if their integrity is in doubt. Do not cache Docker credentials, state, private tfvars, DB data or report payloads.

Azure Cache@2 stores Maven artifacts (keyed by pom.xml), npm downloads (package-lock.json), Terraform provider binaries only (actual provider lock), and public scanner databases (tool versions). Branch/PR cache scope and permissions are Azure DevOps concerns, not locally verified. Maven is not configured with private repository credentials; no settings.xml or account configuration is passed. Docker layer caching is reused within a job/locally; hosted jobs do not share a daemon and no images are exported as pipeline artifacts. Worker model downloads/builds may repeat across fresh hosted jobs. Cache misses affect performance, not test selection.

## Local equivalents

Linux amd64, Docker, Bash/curl/SHA256 and Python 3.12 tooling are required. Azure selects Python 3.12.11 through UsePythonVersion; local host patch versions may differ. Public internet is needed for package/tool/schema/CVE databases. Tools use ignored .incidentiq-backups, including a separate DOCKER_CONFIG with no inherited registry credentials. The global Docker/Compose configuration is untouched.

```bash
./ci/bootstrap.sh basic
./ci/test.sh java
./ci/test.sh python
./ci/test.sh frontend
./ci/bootstrap.sh infra
./ci/infra.sh
./ci/bootstrap.sh security
./ci/images.sh
./ci/locks.sh
```

CI_CACHE_DIR can point to a dedicated dependency-only directory. On WSL, a Linux-filesystem path performs better than a Windows mount; Azure uses Pipeline.Workspace on its Linux disk. Default local dependency caches use /tmp/incidentiq-ci-cache-<UID> on Linux; tools and reports use ignored .incidentiq-backups/ci. Reports are under .incidentiq-backups/ci/reports; raw local logs stay ignored. JUnit tasks publish even after failed tests and fail on missing reports; test/compile/scanner errors stop their stage. No continueOnError is used. A compilation failure may prevent test XML creation, which is reported as missing rather than treated as a passing suite.

The pipeline schema is fetched at a pinned Microsoft azure-pipelines-vscode commit and digest. Its language-service schema represents Azure-coercible YAML scalars as strings; ci/validate-pipeline.py follows that scalar coercion while separately enforcing exact native booleans for release/report safety. It also rejects YAML anchors/aliases, which Azure Pipelines does not support. This offline check does not execute Azure's template engine, task server, cache service, permissions or hosted pool. No Azure DevOps preview API/token was used.

## Security policy and reporting limits

Blocking checks cover detected credential patterns in nonignored source, baked credential-like environment fields, existing API/worker nonroot users, pipeline release/credential restrictions and scanner execution/database errors. Matching secret values are withheld from failures. This is heuristic detection, not proof that every credential is found. Frontend retains its existing root nginx image behavior; it is not claimed to be a hardened rootless image.

**CVE inventory is advisory**, using Trivy --exit-code 0 deliberately, with no ignore file/severity suppression. Scanner errors still return nonzero. All discovered OS/library findings are reported in per-image JSON, with a separate frontend package-lock inventory including development dependencies because bundled JavaScript has no runtime package manifest and summarized by severity. Reports do not mean zero vulnerabilities or verified exploitability. Public advisory databases change over time; their timestamps/scanner version and actual findings matter. No VEX/waiver baseline is fabricated. Before any future release, owners must triage findings, update dependencies/base images as appropriate, and approve an enforcement policy. No production dependency changes are made merely to suppress initial findings. ACR/AKS release is hard-blocked regardless of inventory results.

Only JUnit/security JSON artifacts are published by the pipeline. No Docker image, Terraform state, credentials, environment dump, database snapshot or kubeconfig is published. Pipeline artifacts are Azure DevOps storage, not ACR. Consider report access/retention and hosted-minute/storage costs before connecting an organization.

## Future release gate

`enableRelease` is a native boolean defaulting to false. FutureRelease additionally requires successful checks, refs/heads/main and a manual run. Even if enabled, its only job prints future prerequisites and exits 1. There is no AzureCLI/Docker login/push, Terraform apply or kubectl apply command and no service-connection reference. A successful deployment cannot be inferred by toggling this parameter.

A future separately authorized implementation needs protected environment approvals, reviewed fork/branch permissions, scoped OIDC identity/service connections, private AKS runner connectivity, immutable ACR image digests and provenance, reviewed Terraform state/plan, Key Vault/CSI checks, CVE enforcement/waivers, migrations before workers, retrieval-only smoke checks and rollback/data-retention procedures. It must follow docs/azure/README.md and never reuse Compose data or port 55432. Nothing in this step authorizes those cloud operations.

References: [Azure stages](https://learn.microsoft.com/en-us/azure/devops/pipelines/process/stages), [cache](https://learn.microsoft.com/en-us/azure/devops/pipelines/release/caching), [test reporting](https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/publish-test-results-v2), [official schema](https://github.com/microsoft/azure-pipelines-vscode), [Trivy vulnerability scanning](https://trivy.dev/docs/latest/guide/scanner/vulnerability/).
