# Artifact Manifest

Generated for Phase 6D on 2026-06-16. This manifest is documentation only: no API calls, no Phase 5 shards, no baseline/mutation/observability reruns, and no GPT/WYZ partial-row merges were performed.

## Repository / Environment

- Project root: `<PROJECT_ROOT>`
- WSL paper path: `<PROJECT_ROOT>/IEEE_Conference_Template`
- Repository state: exported paper package; `git rev-parse` does not find a repository at the project root, so no package commit hash is recorded here.
- Windows shell used for the audit: PowerShell on Windows NT 10.0.26200.0.
- Windows Python detected: `Python 3.13.9`; `pip 25.3`.
- WSL Python detected at the paper path: `Python 3.12.3`; WSL kernel reported `Linux 6.6.87.2-microsoft-standard-WSL2`.
- Package files:
  - root `requirements.txt`: not present in this package export.
  - `code/requirements.txt`: present.
  - `code/schema_mutation/requirements.txt`: present.
- TAU-BENCH package: `tau_bench` version `0.1.0`, installed from `https://github.com/sierra-research/tau-bench.git` at commit `59a200c6d575d595120f1cb70fea53cef0632f6b` according to `tau_bench-0.1.0.dist-info/direct_url.json`.
- HAL harness: no installed `hal-harness`/`hal_harness` package version was detected in the active Windows Python environment. The local runner is HAL-compatible but bypasses the HAL official CLI and directly uses TAU-BENCH (`code/schema_mutation/runner.py`, `code/schema_mutation/batch_runner.py`).

## Main Scripts

- `code/schema_mutation/phase5_plan.py`: builds Phase 5 baseline, mutation-candidate, and observability shard plans, including task/seed/model grids and retry-aware filtered shard generation.
- `code/schema_mutation/run_phase5_shard.py`: executes one Phase 5 shard with per-cell subprocess isolation and status logging; API-required for live cells and not used for offline reproduction.
- `code/schema_mutation/summarize_phase5.py`: summarizes Phase 5 status JSONL files into audit summaries and paper table/figure artifacts.
- `code/schema_mutation/build_prediction_dataset.py`: builds the Phase 6A predictor dataset from existing paired artifacts and formal Phase 5 observability status rows.
- `code/schema_mutation/evaluate_predictor_generalization.py`: evaluates feature-family predictor generalization across random and held-out task/tool/policy/model/env splits.
- `code/schema_mutation/evaluate_gate.py`: evaluates SchemaCheckerOnly, replay gates, AFCGate, and ExhaustiveReplayOracle using existing paired/replay-cache artifacts.
- `code/schema_mutation/static_compat_checker.py`: implements the static schema/typed-client compatibility baseline used by gate and checker analyses.
- `code/schema_mutation/changelog_realism.py`: generates lightweight changelog-grounding artifacts and the changelog mapping table for mutation realism.
- `code/schema_mutation/smoke_wyzai.py`: performs tiny WYZ AI endpoint smoke checks and writes provider-smoke artifacts; not part of formal main tables.

Supporting scripts observed in this package include `code/schema_mutation/runner.py`, `code/schema_mutation/batch_runner.py`, `code/schema_mutation/build_observability_review_packet.py`, and `code/schema_mutation/build_combined_observability_review.py`.

## Formal Phase 5 Observability Artifacts

### Retail

- Formal cells: `525`.
- Formal status glob: `runs/schema_mutation/phase5/status/observability_from_baseline_*_status.jsonl`.
- Review packet:
  - `runs/schema_mutation/phase5/observability_review_packet.md`
  - `runs/schema_mutation/phase5/observability_review_packet.json`
- Phase 5 summary:
  - `runs/schema_mutation/phase5/phase5_summary.md`
  - `runs/schema_mutation/phase5/phase5_summary.json`
- Paper table/figure artifacts:
  - `IEEE_Conference_Template/tables/combined_observability_gradient_auto.tex`
  - `IEEE_Conference_Template/tables/observability_by_domain_model_auto.tex`
  - `IEEE_Conference_Template/figures/combined_observability_gradient_curve.pdf`
  - `IEEE_Conference_Template/figures/combined_observability_uplift_forest.pdf`

### Airline

- Formal cells: `1290`.
- Formal status glob: `runs/schema_mutation/phase5/status/airline_observability_from_baseline_*_status.jsonl`.
- Review packet:
  - `runs/schema_mutation/phase5/airline_observability_review_packet.md`
  - `runs/schema_mutation/phase5/airline_observability_review_packet.json`
- Standalone retry-provider-error status files are explicitly excluded when they have already been appended or superseded in the formal status files.

### Combined

- Formal total: `1815`.
- Combined packet:
  - `runs/schema_mutation/phase5/combined_observability_review_packet.md`
  - `runs/schema_mutation/phase5/combined_observability_review_packet.json`
- Combined integrity recorded in the packet: `1815/1815` ok, `0` provider errors, `0` timeouts, `0` failed rows, no smoke rows, no fake rows, no WYZLab rows, and no mutation-candidate rows.

## Inclusion / Exclusion Rules

Formal Phase 5 tables include only rows satisfying all of the following:

- `baseline_success=true`
- `status=ok`
- non-smoke
- non-fake
- non-WYZ partial
- no `provider_error`
- no timeout
- no failed status
- deduplicated by `cell_key`, with the latest successful retry winning

Formal tables exclude:

- smoke shards
- local fake smoke rows
- standalone retry status files if already appended or merged
- `provider_error` rows
- timeout rows
- failed rows
- WYZ/GPT/Grok partial rows unless explicitly complete and marked formal
- mutation_candidate shards

## Retry / Deduplication Policy

- Provider errors caused by temporary provider-side issues are not counted as agent-facing regressions.
- Retry rows may be appended to the main status file or tracked in separate retry status files.
- Formal summaries use latest-by-`cell_key` semantics.
- An old `provider_error` row is overwritten by a later `ok` row for the same `cell_key`.
- Duplicate attempts are not double counted.
- The airline review packet records `1344` raw status rows in formal airline files, `1290` deduplicated latest rows, and `54` duplicate rows removed by `cell_key`.

## Models / Providers

Formal main models:

- `deepseek/deepseek-v4-flash`
- `dashscope/qwen-max`
- `dashscope/kimi-k2.6`
- `dashscope/glm-5.1`

User simulator:

- `dashscope/qwen-flash`

Provider extensions:

- GPT-5.5 / Grok are optional provider extensions unless complete formal artifacts exist.
- Partial GPT/WYZ/Grok rows are not included in the main formal tables.
- WYZ smoke artifacts record Grok/Grok-fast provider-side HTTP 403 upstream anti-bot failures in `runs/schema_mutation/wyzai_smoke/WYZAI_PROVIDER_FIX_SUMMARY.md` and related smoke result files.

Supplementary GPT-5.5 airline extension:

- Review packet: `runs/schema_mutation/phase5/wyz_gpt55_airline_review_packet.md` / `runs/schema_mutation/phase5/wyz_gpt55_airline_review_packet.json`.
- Formal cells: `395` airline paired observability cells after baseline filtering.
- Result: O0--O4 success `0.532 / 0.873 / 0.886 / 0.835 / 0.924`; O4--O0 uplift `+0.392`, bootstrap 95% CI `[0.266, 0.519]`.
- This extension is reported as supplementary appendix evidence and is not included in the frozen `1815`-cell main observability table.
- It is not included in the Phase 6A predictor dataset or AFC-Gate reruns.
- Transient WYZ provider transport errors were retried and de-duplicated by `cell_key`.
- Grok/Grok-fast variants remain excluded due to provider-side HTTP 403 anti-bot errors.

Provider configuration:

- API keys are read from environment variables and are not stored or printed in the artifact package.
- Provider base URLs are configured by environment variables such as `DEEPSEEK_BASE_URL`, `DASHSCOPE_BASE_URL`, `WYZAI_API_BASE`, `WYZLAB_API_BASE`, and aliases handled in `code/schema_mutation/run_phase5_shard.py` and `code/schema_mutation/runner.py`.

## Runtime Settings

Detected from local scripts and persisted metadata:

- Seeds: `0,1,2`.
- Retail candidate tasks: `0-19`.
- Airline candidate tasks: `0-49`.
- `max_num_steps=30`.
- `timeout_seconds=600`.
- `temperature=0.0` where supported.
- Formal Phase 5 runbook: `runs/schema_mutation/phase5/RUNBOOK.md`.
- Prompt construction path: `code/schema_mutation/runner.py` instantiates TAU-BENCH `ToolCallingAgent` and TAU-BENCH user simulator with the configured model/provider values.
- Raw JSONL metadata records `env_user_model=dashscope/qwen-flash`, `env_user_provider=dashscope`, `temperature=0.0`, `max_num_steps=30`, and timeout/cell settings.

## Prompt Archive

- Prompt/system-message archive path: `runs/schema_mutation/prompt_archive/`.
- Main archive file: `runs/schema_mutation/prompt_archive/PROMPT_ARCHIVE.md`.
- Agent construction path: `code/schema_mutation/runner.py::run` instantiates TAU-BENCH `ToolCallingAgent`; the installed TAU-BENCH agent initializes messages with `isolated_env.wiki` as the system message and the initial user-simulator observation as the first user message.
- User simulator construction path: `code/schema_mutation/batch_runner.py` and `code/schema_mutation/runner.py` pass `dashscope/qwen-flash` / `dashscope` into TAU-BENCH `LLMUserSimulationEnv`.
- Static templates archived:
  - `runs/schema_mutation/prompt_archive/agent_system_prompt_template.txt`
  - `runs/schema_mutation/prompt_archive/user_simulator_prompt_template.txt`
  - `runs/schema_mutation/prompt_archive/system_message_sources.md`
- Exact rendered per-cell `agent_messages`, `user_simulator_messages`, and mutated tool schemas were not emitted as standalone artifacts in the current run.
- TODO-HIGH before final artifact release: persist fully rendered per-cell agent and user-simulator messages for a clean reproduction run. Current archive records construction paths and static templates.

## Reproduction Commands

Offline reproduction commands only:

```bash
python code/schema_mutation/summarize_phase5.py --overwrite
python code/schema_mutation/build_prediction_dataset.py --input-existing-artifacts --include-phase5-observability --overwrite
python code/schema_mutation/evaluate_predictor_generalization.py --dataset runs/schema_mutation/predictor_dataset.jsonl --overwrite
python code/schema_mutation/evaluate_gate.py --input-existing-artifacts --include-phase5-observability --overwrite
```

Full live rerun stages are API-required and must not be run for offline artifact cleanup:

```bash
python code/schema_mutation/phase5_plan.py ...
python code/schema_mutation/run_phase5_shard.py ...
```

## Table / Figure Provenance

- Table VI, combined observability gradient: `runs/schema_mutation/phase5/combined_observability_review_packet.md/json`, `runs/schema_mutation/phase5/phase5_summary.md/json`, and `IEEE_Conference_Template/tables/combined_observability_gradient_auto.tex`.
- Table VII, per-domain/per-model observability: `runs/schema_mutation/phase5/combined_observability_review_packet.md/json` and `IEEE_Conference_Template/tables/observability_by_domain_model_auto.tex`.
- Observability figures: `IEEE_Conference_Template/figures/combined_observability_gradient_curve.pdf` and `IEEE_Conference_Template/figures/combined_observability_uplift_forest.pdf`, generated from the combined Phase 5 review packet.
- Table XIII, predictor generalization: `runs/schema_mutation/predictor_generalization_summary.md/json`, `runs/schema_mutation/predictor_dataset.jsonl`, and `IEEE_Conference_Template/tables/predictor_generalization_auto.tex`.
- Table XIV, gate evaluation: `runs/schema_mutation/gate_evaluation_summary.md/json`, `runs/schema_mutation/gate_evaluation_records.jsonl`, and `IEEE_Conference_Template/tables/gate_evaluation_auto.tex`.
- Changelog mapping table: `runs/schema_mutation/changelog_realism/changelog_mapping_summary.md/json`, `runs/schema_mutation/changelog_realism/changelog_items.jsonl`, and `IEEE_Conference_Template/tables/changelog_mapping_auto.tex`.

## Known Limitations

- The Phase 6A predictor dataset remains C-class-heavy (`2148` C-class samples and `26` A-class samples in `predictor_dataset_summary.json`).
- B/D mutation data remains future work for broader predictor and gate validation.
- Provider-side model snapshots may drift; model strings are recorded, but provider snapshot identifiers should be archived where available.
- Exact prompt/system-message files were not found as standalone archived artifacts and must be added before submission.
- GPT/Grok optional provider extensions are not in the main formal table unless complete artifacts are explicitly marked formal.
