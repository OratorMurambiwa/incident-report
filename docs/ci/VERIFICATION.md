# Step 8C local verification

Executed locally on 2026-11-07 UTC against application commit bf5ee9a25d1baa0d2f2029562f9d253b8e69944c. [Design/reproduction/security policy](README.md). Final measured results are recorded in verification.json.

**No Azure DevOps organization run or server-side preview was performed.** No organization/account/service connection was created, no Azure credential was used, no image was published and no deployment was attempted. The optional release gate was inspected/tested statically; it is disabled by default and deliberately exits 1 if selected. Local equivalents are not proof of hosted-agent or Azure task-service behavior.

## Corrections before the successful local checks

- The first isolated Java suite reported 62 errors because Mockito/Byte Buddy could not dynamically attach to the JVM from the Windows bind-mounted working directory. It was a genuine failed run, not counted as passing. Its JUnit files were exported and only that private database/network were removed. The fix copies read-only source into a container-local Linux working directory and exports only test reports. With the Linux dependency cache and workspace, the same 62 tests passed with no changes to application tests or mocking policy. The combined workspace/cache change is not a controlled performance benchmark.
- Microsoft's language-service JSON schema models Azure-coercible scalar fields as strings. A plain generic JSON-schema invocation rejected native YAML scalars, including the documented boolean parameter default. Compatible scalar encodings and a documented type-check adaptation now follow Azure language-service semantics; independent policies insist the release default is the actual boolean false. Raw generic validation failures are not counted as successful schema checks. No schema properties/required fields are removed.
- Initial generated YAML anchors were removed because Azure Pipelines does not support them; the validator explicitly rejects anchors/aliases.
- The initially selected Trivy 0.66.0 release URL returned 404 and was not executed. Public upstream release/advisory inspection selected immutable clean 0.69.3 instead. Its archive matched both official checksums and the independently recorded SHA256 1816b632dfe529869c740c0913e36bd1629cb7688bd5634f4a858c1d57c88b75. No compromised scanner/action version was run.

## Isolation and preservation

Every CI database run used a fresh random incidentiq-ci project, private Docker network and tmpfs PostgreSQL with no host port or shared volume. Real Flyway migrations and corpus ingestion ran against these databases, not normal Compose or its test database. Successful runs and failed runs cleaned only their own temporary projects; no --volumes/global prune was used. Standard Compose configuration, existing databases/volumes and PostgreSQL host port 55432 were preserved.

The only change to an existing test script is optional pytest JUnit export through TEST_REPORT_DIR. Default test flags remain unchanged. Application code, dependency locks, Dockerfiles, applied migrations, Terraform and Kubernetes manifests are unchanged. CI image tags are separate incidentiq-ci-* names, so working runtime tags are not replaced by the new image stage.

## Azure DevOps/runtime limitations

Not executed: organization pipeline import/compile/template expansion; hosted Ubuntu image/Python task availability; repository/PR permissions and trigger behavior; actual task versions; cache restore/save scopes; test-result ingestion and artifact retention; hosted resource quotas/parallelism/timeouts; branch/environment approvals; any ACR/AKS release flow. The local schema/policy checks are approximate structural validation with explicit Azure scalar semantics, not a substitute for the organization's preview API. No Azure DevOps token was requested or used.

Container tags and hosted-agent/task patches are mutable; CVE databases change with time. Scanner results do not establish exploitability, complete detection, SBOM provenance or zero vulnerabilities. The advisory inventory is not a release approval, and the future release remains blocked. Full browser/Kafka fault/Ollama integration is not part of the default new pipeline; database/model integration tests are real and separate from mocked Kafka/LLM unit paths. A real hosted end-to-end/release trial requires later authorization and isolated resources.

## Actual completed local equivalents

| Workflow | Verified result |
| --- | --- |
| `ci/bootstrap.sh basic` | Compose 2.39.2 archive checksum passed; private Docker configuration used |
| `ci/test.sh java` (corrected rerun) | **62 JUnit tests, zero failures/errors/skips**, Maven verify BUILD SUCCESS; 1:01 observed Maven duration with warm Linux cache |
| `ci/test.sh python` | **10 Java PostgreSQL seed tests**, fresh Flyway schema; ten real runbooks/60 chunks ingested; **77 pytest passed in 11.28s**, JUnit XML exported; pip check: No broken requirements found |
| `ci/test.sh frontend` | **7 Node test cases in JUnit XML**, strict TypeScript checks and Vite production build passed |
| `ci/bootstrap.sh infra`, `ci/infra.sh` | Versioned tool/schema checksums; Terraform fmt/init -backend=false/validate; **10 HCL tests**, **9 local Kubernetes tests**, **10 final pipeline tests**, **19 existing helper tests** passed |
| Kubernetes schema checks | Local **17**, Azure template **19**, generated Azure example **19** valid; no schema errors/skips, including CSI CRD |
| Pipeline schema | Pinned Microsoft schema commit 9e40e814abd20917f273dd587497086f0476a563 with documented Azure scalar coercion; safety policies passed |
| Release placeholder | Local empty-environment shell test returned expected exit 1; no publishing/deployment command |
| `ci/images.sh` | All three existing Dockerfile builds completed using cached layers; source and image-config gates passed; API user incidentiq, worker user worker, existing nginx default root behavior documented |
| Trivy image scans | All three actual image scans completed against current vulnerability + Java advisory-index databases; JSON reports generated |
| `ci/locks.sh` | Frontend package-lock scanned separately, **including dev dependencies**; zero reported findings |
| Syntax/whitespace | CI shell/Python checks and git diff --check passed |

A later local static invocation hit the known WSL relative-working-directory import error after Terraform/Kubernetes schema checks had passed. The final CI infrastructure wrapper uses stable /tmp and absolute source paths; its full rerun passed. The final pipeline-policy suite was rerun after the frontend-lockfile step and release execution test were added. These corrected failures are retained in private local logs, not counted as passing runs.

Maven/Node/tools run in their configured pinned containers where applicable. Azure's exact UsePythonVersion task did not run locally; the host Python patch version is recorded in verification.json. Cached Dockerfile test layers are not represented as freshly executed database integration tests; explicit Java/Python stages supply those counts. Local JUnit XML generation/parsing succeeded, but publishing/merging those reports in Azure DevOps remains unverified.

## Actual security inventory — not a clean-security claim

| Scan | Critical | High | Medium | Low |
| --- | ---: | ---: | ---: | ---: |
| API runtime image | 7 | 12 | 41 | 17 |
| Worker runtime image | 1 | 60 | 96 | 71 |
| Frontend nginx runtime image | 3 | 61 | 90 | 40 |
| Frontend lockfile, including development dependencies | 0 | 0 | 0 | 0 |

These are **finding occurrences**, not distinct CVE counts or verified exploitable issues. No ignore file/severity suppression was added. The inventory is explicitly advisory (--exit-code 0), while scanner/database errors and credential/config gates fail the stage. No fixes or waivers are invented; existing production dependencies/base-image behavior were preserved. Future release remains hard blocked and needs triage/approved enforcement before implementation. [Sanitized image IDs, DB timestamps, counts and critical identifiers](security-inventory.json). Raw scanner/JUnit reports remain ignored locally and are the only report artifacts configured for Azure DevOps publication; no images/state/data/credentials are artifact inputs.

Final health: normal API/publisher/worker/frontend/PostgreSQL/Kafka/monitoring remained running/healthy, all private CI containers removed. PostgreSQL host port remains 55432. Original six data/model volume creation timestamps match the previous milestones and are recorded in verification.json. No normal Compose data was used for CI. All runtime source, dependency locks, Dockerfiles, Terraform/Kubernetes configurations and migrations remain unchanged.
