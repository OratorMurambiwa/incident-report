# Local Ollama RAG verification — 2026-11-06 (America/Chicago)

## Hardware and model selection

Initial inspection: Intel Core Ultra 5 225U, 14 logical CPUs; WSL/Docker RAM 7.2 GiB with about 4.0 GiB available, 2 GiB swap; approximately 145 GiB free workspace disk. Windows WMI reports Intel Graphics, but no GPU device was exposed in WSL/containers (`/dev/dxg`/`/dev/dri` absent, nvidia-smi unavailable). Inference used CPU; Ollama reported size_vram=0.

Neither an Ollama executable nor a running server was initially available. localhost:11434 refused connections and the old host.docker.internal endpoint was unreachable. The optional Compose override uses private Docker DNS `ollama:11434` with no published host port. Base compose.yaml and .env.example retain LLM_PROVIDER=none.

Actual models downloaded explicitly from the Ollama registry:

| Model | Bytes | Quantization | Digest |
| --- | ---: | --- | --- |
| qwen2.5:0.5b | 397821319 | Q4_K_M | a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67 |
| qwen3:0.6b | 522653767 | Q4_K_M | 7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435 |

The first model produced schema-valid output but weak causes/investigation text. The slightly stronger qwen3 model became the selected verification model; its reported parameter count is 751.63M. Both small downloads remain cached locally; no multi-GB model or paid API was used. Loaded qwen3 metadata reported 1,726,601,898 bytes with zero VRAM. Runtime is limited to four CPUs and 2500 MiB.

## Small CPU runtime

Official Ollama 0.6.8 executable layer: 11,418,507 compressed bytes, SHA-256 2ace2f9dde9e03c2b920e6f482ad34fd7dc7fb992b8a75cc0343945f36d2e9f7. Matching official source: 8,330,813 bytes, SHA-256 46e3953373be41fae1699eaca97eb0e5f35b9a83d9652f38901938c1a988634d. Fetch scripts verify hashes and enforce size limits before use. AVX2/FMA/F16C libraries are compiled with two jobs from that source. This avoids the official release image's roughly 1.6 GiB GPU library layer. CPU backend selection was confirmed in real Ollama logs.

The standalone generic CPU executable was too slow for the existing 30-second request bound. AVX2 libraries, four inference threads, concise one-item-per-category output grammar and removal of unused prompt IDs/scores made bounded CPU generation practical. All five full evidence snapshots remain in PostgreSQL. The public/storage schema still accepts historical multi-item diagnoses. Requests retain 8192 context tokens, cap output at 512 tokens, and retain the existing 1–30 second timeout configuration.

Upstream references: https://docs.ollama.com/docker , https://github.com/ollama/ollama/blob/v0.6.8/Dockerfile , https://github.com/ollama/ollama/blob/v0.6.8/CMakeLists.txt , https://ollama.com/library/qwen3:0.6b .

## Observed grounding failure and repair

Actual qwen3 trial incident `e7716ad9-f31a-4bae-aad5-ebc1efa5206a` produced this Kafka recommendation while citing kafka-lag.md:

> Ensure offsets are restored forward and that consumers are only added up to available partitions.

Its retrieved runbook explicitly says **not** to reset offsets forward because that can hide unprocessed work. Filename validation passed, but the recommendation contradicted its evidence. This was a failed semantic quality gate, not a successful grounded diagnosis. No recommendation was executed. The synthetic trial diagnosis is retained unchanged as evidence; it must not be treated as operational advice.

Added a fail-closed runtime guard rejecting forward-offset references in generated investigation/remediation. It is intentionally conservative, including warnings that mention such operations. Unit tests replay the actual phrase and two variants. Model failures retain the existing transaction rollback, bounded retries, durable quarantine and offset-after-persistence handling. The prompt also explicitly prohibits forward-offset recommendations.

This narrow prohibition is not a general semantic entailment checker. Valid citations still do not prove a model's other claims. Small models can restate symptoms or give shallow hypotheses; human review and uncertainty remain necessary. Never execute suggestions automatically.

## Verification commands

```bash
./scripts/test-api.sh
./scripts/test-worker.sh
docker compose -f compose.yaml -f compose.ollama.yaml build ollama worker
docker compose -f compose.yaml -f compose.ollama.yaml up -d --no-deps --wait ollama
docker compose -f compose.yaml -f compose.ollama.yaml exec ollama ollama pull qwen3:0.6b
docker build -t incidentiq-browser:local infra/browser
python3 scripts/verify-local-ollama.py
```

Model pulls are explicit; neither worker nor runtime downloads models automatically. Build/test operations used a temporary empty DOCKER_CONFIG for public images because the WSL credential helper initially failed; no user credentials were changed.

The browser verifier submits real database, memory and Kafka incidents using React. It performs no route interception or response mocking. It checks generated fields/citations, real GET diagnosis and PostgreSQL counts: one published outbox, one durable receipt, five snapshots, one diagnosis. A naturally rejected Kafka answer is allowed only as an explicitly verified InvalidDiagnosis quarantine with no receipt/snapshots/diagnosis and an offset committed afterward. At least database and memory cases must store diagnoses.

Adversarial tests request actual model responses constrained to contain an invented filename or the observed prohibited offset advice. The application must reject both. These are deliberate model-output contract tests, not naturally occurring answers or mocked responses. Separate actual worker cases use a nonexistent model and an installed model with a one-second timeout: three attempts, FAILED incident, one durable failure record, no partial diagnosis, Kafka offset committed only afterward.

Raw proof JSON, screenshots and model-call logs remain under ignored .incidentiq-backups/ollama-verification. Earlier small-model trial evidence is retained separately. Generated fields are reference hypotheses, never verified incident measurements.

## Results

The initial run and final hardened run are distinguished below. Initial qwen3 transport/storage checks completed for three cases, but that initial run FAILED semantic review as described above. Initial successful model-call times were 18.742, 28.918 and 20.499 seconds; browser-to-diagnosis times were 55.394, 30.247 and 55.363 seconds. Database and Kafka had one cold/cache-miss 30-second timeout followed by a successful retry. Those timing differences must not be hidden by reporting successful request latency alone.

## Final hardened results

`python3 scripts/verify-local-ollama.py`: real transport, persistence, browser and negative checks passed after the repair. No application/model responses were mocked in these checks.

| Case | Incident | Successful Ollama call | React submission to displayed diagnosis |
| --- | --- | ---: | ---: |
| Database | 42e33a05-3272-4a34-9da1-1ffa30e47fe7 | 18.487s | 55.704s |
| Memory | 85c44938-02da-459b-a80d-dded98c156e5 | 26.493s | 30.949s |
| Kafka | 71fedca3-5b10-4221-be2e-d5f87e0c0312 | 27.783s | 30.337s |

All three ended DIAGNOSED with provider ollama, model qwen3:0.6b, one published outbox event, one receipt, five snapshots and one stored GENERATED diagnosis. GET diagnosis returned HTTP 200; React displayed actual model provenance and all three cited action/cause sections. The database case had one cold 30-second timeout and safe retry; this is included in its 55.704s end-to-end time. Successful-call durations are not cold-start SLA measurements.

Manual review compared the final likely causes, investigation steps, remediation and exact source filenames with their five snapshots. The database investigation used pg_stat_activity and suggested rolling back the application/pool change; memory checks covered limits/restart evidence and reducing a confirmed memory-heavy workload; Kafka checks covered broker/group state with dependency recovery and reducing per-event work. These suggestions appeared in their supplied runbooks. The final Kafka result did not contain the earlier forward-offset contradiction. Screenshots were captured and the actual generated database view was visually inspected.

This is sampled evidence review, not a guarantee of root-cause accuracy. Causes can be generic symptom restatements, summaries can blur observations with runbook possibilities, and generated uncertainty language can be imprecise about what evidence is present. The helper deliberately leaves general semantic certification false until human review; a separate sampled-field review is recorded locally. Do not treat GENERATED/DIAGNOSED as proof of an incident's real cause or as permission to execute remediation.

Actual negative checks:

- Invented-citation answer from qwen3:0.6b rejected in 18.114s; no diagnosis persistence call.
- Actual answer with valid evidence filenames but the prohibited offset sentence rejected by the new policy in 13.257s; no diagnosis persistence call.
- Missing model incident f4b79aee-f58d-4eef-8ca3-40599cc5de3f: three attempts, FAILED, one ModelUnavailable quarantine at partition 0/offset 57; committed offset 58 afterward. Zero receipts/snapshots/diagnoses.
- One-second timeout incident c10f3468-8ef2-406d-90e6-601f28e467c4: three attempts, FAILED, one ModelUnavailable quarantine at partition 0/offset 58; committed offset 59 afterward. Zero receipts/snapshots/diagnoses.

The first two are deliberately constrained actual-model output tests, not claims that the model spontaneously emitted those answers in that run. The earlier ordinary Kafka contradiction was a natural model answer and is preserved separately. The offset policy is narrow and conservative; it does not recognize all possible unsupported paraphrases or perform general semantic entailment.

Regression checks executed:

- `./scripts/test-api.sh`: **62 tests, 0 failures, 0 errors, 0 skipped; BUILD SUCCESS**.
- Final `./scripts/test-worker.sh`: **77 passed in 11.15s**, including three new offset-policy regression cases and the new timeout case. Full integration tests use real local embeddings/PostgreSQL; Ollama unit fixtures remain distinct from live generation.
- Frontend build-stage `npm test && npm run build`: **7 tests passed**, strict TypeScript and production Vite build passed.
- `python3 scripts/verify-api.py`: **12 HTTP checks passed**.
- Final `python3 scripts/verify-rag-flow.py --expect-mode RETRIEVAL_ONLY`: HTTP 200 none-mode diagnosis, one receipt/five snapshots, duplicate preserved diagnosis/evidence.
- Final `bash scripts/test-dashboard.sh`: **14 browser checks passed**, actual retrieval-only mode, zero JavaScript errors.
- Base and Ollama-override Compose validation, verification-helper syntax and `git diff --check`: passed.

The default worker was restored to LLM_PROVIDER=none in finally and verified again with a real incident. Optional Ollama was stopped to free memory; both model downloads remain cached in the separate volume. Existing API/Kafka/PostgreSQL/monitoring/frontend services and data were preserved. PostgreSQL remains on host port 55432. No model-suggested command was executed, no existing diagnosis was overwritten, and no persistent volume was deleted.
