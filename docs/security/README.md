# Step 8D: container vulnerability remediation

Measured with **Trivy 0.69.3 and the same frozen vulnerability/Java databases**, not with an updated scanner that changes advisory coverage. No ignore file, severity exclusion, `--ignore-unfixed` or vulnerability suppression was added. Counts describe this local image/database pair, not proof that a container is safe.

| Runtime image | Before critical / high | After critical / high | Distinct CH CVEs before → after |
|---|---:|---:|---:|
| API / publisher | 7 / 12 | 2 / 0 | 18 → 2 |
| Python worker / ingestion | 1 / 60 | 0 / 48 | 25 → 12 |
| Frontend nginx | 3 / 61 | 0 / 0 | 48 → 0 |
| Total occurrences | **11 / 133** | **2 / 48** | Per-image totals: 91 → 14 |

**94 fewer critical/high occurrences (65.3%)**, from 144 to 50; 90 distinct CVE IDs across images become 14. One original CVE appears in more than one image. The frontend has no vulnerabilities detected at any severity in this snapshot; this is not a zero-vulnerability guarantee. API still has 22 medium/16 low, worker 81 medium/65 low. Other Compose images and build-stage tooling are outside this runtime-image comparison.

- [Full ledger](TRIAGE.md): every one of the 144 baseline CH occurrences, before/after package revisions and scanner-supplied fixed versions, followed by exploit conditions and deferrals.
- [Structured triage](triage.json): package paths, direct/transitive/vendor provenance, duplicate source groups, per-advisory exposure, all severity counts, image IDs and raw report hashes. No new CH rows remain in the final comparison.
- [Verification results](VERIFICATION.md) and [machine-readable evidence](verification.json), including actual local Ollama generation, explicitly rejected answers and failure guards.
- [Current exposure checks](exposure.json): actual worker capabilities/process and a bounded source-feature search; this is not an exploit proof.
- [Frozen database hashes](database-snapshot.json), [offline embedding parity](embedding-parity.json), actual [Maven dependency tree](java-runtime-dependencies.txt) and [pip inspect dependency metadata](python-dependencies.json).

The pip metadata lists installed distributions and their declared requirement markers. Optional extras in `requires_dist` are not proof those extra packages are installed; top-level entries are the actual installed set. Vendored setuptools helpers are recorded separately by the scanner, since pip does not list them as separate installations.

## Changes and compatibility

API keeps Java 21, Spring Boot 3.5.16 and Spring Framework 6.2.19. Refreshing the Java 21 runtime gives Temurin 21.0.13+9; supported Ubuntu Jammy package upgrades fix APT. Same-line overrides update Tomcat 10.1.55 → 10.1.61, Jackson BOM 2.21.4 → 2.21.8, JDBC 42.7.11 → 42.7.12, Kafka's transitive LZ4 1.10.1 → 1.11.4 and Snappy 1.1.10.5 → 1.1.10.9. The dependency tree records the actual resolution, including Jackson's separately versioned annotations artifact. Two new codec round-trip JUnit tests (Snappy native and LZ4 fastest supported factory) supplement the existing 62 tests. No applied Flyway migration changes.

Worker keeps Python 3.12 and Debian 13, updating its base to 3.12.16-slim-trixie and applying stable security packages (including zlib). LangChain stays on the 0.3 line at 0.3.30; core remains 0.3.86. Kafka client 2.2.15 → 2.3.2 fixes malformed broker-frame and excessive SCRAM-iteration handling. setuptools 78.1.0 → 84.2.1 fixes its own advisory and replaces **vendored** jaraco.context 5.3.0 → 6.1.0 and wheel 0.45.1 → 0.46.3. Installing a top-level wheel alone would not fix those embedded copies. Torch requires setuptools on Python 3.12: it was retained and explicitly pinned.

Fixing the critical sentence-transformers local model-code loading bypass requires an ML library major update: sentence-transformers 3.4.1 → 5.6.0, transformers 4.48.3 → 5.10.0 and CPU Torch 2.6.0 → 2.10.0. These candidates were adopted only after actual dependency resolution, `pip check`, database/retrieval tests and offline embedding parity. Hugging Face Hub 1.33.0 and tokenizers 0.22.2 satisfy the real Transformers requirements; Hub 2.x would not. `requirements.lock` comes from `pip freeze --all` in the resolved Docker environment, not hand-edited transitive guesses. No LangChain or Spring major upgrade was forced.

MiniLM model name, revision, weights and 384-dimensional normalized embeddings remain unchanged. Five offline queries (database, HTTP errors, memory, Kafka and authentication) compare old/new embeddings: minimum cosine **0.9999999999998836**, maximum absolute difference **8.475e-8**. `model.safetensors` SHA256 is identical. Fresh runbook ingestion/relevance tests and live processing provide additional compatibility evidence; parity is sampled, not a guarantee for every possible input. Existing document vectors and incident snapshots were not rewritten.

Frontend keeps nginx 1.28, updating to `1.28.3-alpine3.23-slim` plus Alpine's patched `nginx=1.28.3-r7`. Slim removes unused XML/image/curl/Brotli dependency chains (absence verified against package inventory). Retained OpenSSL, musl, PCRE2 and zlib are updated on Alpine 3.23. Explicit nginx package selection is necessary because the upstream image pins `1.28.3-r1` in `/etc/apk/world`; generic `apk upgrade` leaves it vulnerable. The distribution package overwrites global configuration, so the Dockerfile preserves the upstream global nginx config and verifies it with `nginx -t`. Actual browser/proxy checks run against the patched binary. React/Vite application source and its lock remain unchanged.

## Remaining risk and deferred fixes

**Two scanner-critical Spring MVC findings:** [CVE-2026-47884](https://spring.io/security/cve-2026-47884/) needs XsltView with broad mapping/implicit view names; [CVE-2026-47890](https://spring.io/security/cve-2026-47890/) needs SSE view-fragment streaming. This API uses JSON REST controllers, without those features. Upstream rates them medium and low respectively; the Trivy-critical rows are still retained. The public fixed version is 7.0.9; 6.2.20 is enterprise-only. Boot 3.5.16's available managed Spring version is 6.2.19. Do not download enterprise artifacts without entitlement, buy services, or substitute Spring 7 beneath Boot 3. A separately tested Boot 4/Spring 7 migration is required for a compatible public fix. This review is not an exploit test and must be revisited before enabling MVC views/SSE.

**One LangChain core high:** CVE-2026-34070 affects legacy `load_prompt`/`load_prompt_from_config` path loading, which the worker does not call. Fixed core 1.2.22 is incompatible with LangChain 0.3.30's `<1` constraint. Defer a coordinated LangChain 1 migration rather than override the resolver or silently remove the finding. Locally constructed prompt templates still treat incident/runbook text as untrusted data; no remediation is executed.

**47 Debian high occurrences, 11 distinct source advisories:** util-linux (36 occurrences / four CVEs), ncurses (four / one), SQLite (three / three), systemd libraries (two / one), ACL and Perl (one each). The frozen database supplies no Debian 13 fixed versions. Current worker is uid 999 without mount privileges, and it never invokes mount helpers/nsenter, infocmp, privileged ACL actions, Perl archive parsing or untrusted SQLite/session/FTS databases. The actual `systemd-homed` executable is absent; matching libsystemd/libudev by source package does not establish that homed runs. These observations reduce apparent reachability but are not suppression or a guarantee. Do not mix Debian unstable libraries, downgrade to a distribution with less advisory coverage or strip required libraries just to improve counts. Upstream fixed versions are recorded separately in the ledger (util-linux 2.41.6/2.42.3, ACL 2.4.0, ncurses 6.5-20251213, SQLite 3.54.0, Archive::Tar 3.10 and maintained systemd branches); these are not Debian 13 package fixes. Track vendor fixes and rebuild on release; revisit before adding archive/model upload, SQLite, terminal or privileged functionality.

Additional reachability limit: CVE-2026-78409 requires a Linux >=6.15 detached-tree path, while the actual Docker kernel is 6.6.87.2-microsoft-standard-WSL2. Its upstream affected-range metadata starts at util-linux 2.42 while Debian flags 2.41.5; this uncertainty is retained, not used to remove findings.

Metadata limitations: Debian's [CVE-2026-76844 tracker](https://security-tracker.debian.org/tracker/CVE-2026-76844) identifies a zlib gzip write-error flaw, despite the scanner's incorrect webpack title; it shares the remedial commit with CVE-2026-85091. Both rows are preserved and both fixed by the stable zlib package. The Transformers CVE-2026-5241 description concerns the 5.2.0 LightGlue implementation while the baseline is 4.48.3; this potential affected-range mismatch is recorded, not silently excluded. The candidate is above its fixed version. Fixed-version fields in the ledger reflect the distribution/scanner value, which can differ from upstream releases.

This milestone does not certify authorization, Internet exposure, exploit resistance, other Compose images, scanner accuracy or all possible LLM answer quality. Existing local-development credentials/configuration and disabled Azure release gate remain unchanged. Keep the deployment local.

## Reproduce the comparison

Use Docker only for application toolchains. Preserve the old image tags **before building**; the tested originals are retained locally as `incidentiq-security-{api,worker,frontend}:before`, with exact IDs in the ledger. The updated ones use `:after`; normal local tags now reference the verified updated images. Never pull an old semantic tag and assume it reconstructs the tested original image.

```bash
./ci/bootstrap.sh
# Freeze both db/ and java-db/ from the scanner cache to a separate local directory.
# This run used /tmp/incidentiq-security-db-8d; files total about 3.25 GB.
# docs/security/database-snapshot.json identifies the exact tested contents.
export SECURITY_DB_CACHE=/tmp/incidentiq-security-db-8d
bash security/scan.sh before
export DOCKER_CONFIG="$PWD/.incidentiq-backups/ci/docker"
docker build --pull -t incidentiq-security-api:after api
docker build --pull -t incidentiq-security-worker:after worker
docker build --pull -t incidentiq-security-frontend:after frontend
bash security/scan.sh after
python3 security/triage.py --cache "$SECURITY_DB_CACHE"
python3 -m unittest discover -s security -v
```

The scanner uses `--skip-db-update --skip-java-db-update --offline-scan --skip-version-check --image-src docker --list-all-pkgs`, all vulnerability severities, no network advisory refresh and no ignores. The comparison verifies streaming SHA256 of all four database files after scanning. Raw reports remain under ignored `.incidentiq-backups/security/8d/{before,after}`. Database UpdatedAt: vulnerability DB **2026-11-07T18:32:58Z**, Java index **2026-11-07T01:07:52Z**. Trivy's archive SHA256: `1816b632dfe529869c740c0913e36bd1629cb7688bd5634f4a858c1d57c88b75`, the existing pinned clean version; it was not changed for this comparison.

The large advisory databases/raw reports are not committed. Preserve the frozen cache locally if exact reruns are needed; if it is lost, the public latest database cannot recreate this snapshot. A different snapshot must be documented as a new comparison, not substituted under these hashes. Base tags and apt/apk repositories are mutable, so future rebuilds can resolve different patch packages; exact tested image IDs/digests and package metadata are recorded rather than claiming hermetic builds. The explicit nginx package revision may disappear from a rolling mirror; update it deliberately with tests if required.

For an offline MiniLM parity rerun, the preserved baseline contains five synthetic query vectors; `security/check-embeddings.py` runs in the candidate worker with `--network none`, `/app` on PYTHONPATH and that baseline mounted read-only. It asserts dimensions/cosine/maximum difference and returns the pinned weight hash. Do not replace production embeddings or re-ingest unchanged documents to manufacture parity.

See verification for the actual test commands and their observed outcomes. None of these commands deletes existing Docker volumes, touches Azure credentials, publishes images or provisions resources.

```bash
# Exact parity commands; synthetic vectors stay ignored, both model runs are offline.
root="$PWD"
mkdir -p .incidentiq-backups/security/8d/before
docker run --rm --network none --memory 1024m --cpus 1 \
  -e PYTHONPATH=/app -v "$root/security:/checks:ro" --entrypoint python \
  incidentiq-security-worker:before /checks/export-embeddings.py \
  > .incidentiq-backups/security/8d/before/embedding-vectors.json
docker run --rm --network none --memory 1024m --cpus 1 \
  -e PYTHONPATH=/app -v "$root/security:/checks:ro" \
  -v "$root/.incidentiq-backups/security/8d/before/embedding-vectors.json:/baseline.json:ro" \
  --entrypoint python incidentiq-security-worker:after /checks/check-embeddings.py /baseline.json \
  > docs/security/embedding-parity.json
```
