# Phase 10B Report: Human-Review Packaging and Non-Obviousness Smoke

## 1. Executive Summary

- Human-review packages generated: yes.
- Oracle-review packages generated: yes.
- Non-obviousness smoke run completed: yes, after switching to a Python environment with `tau_bench` available.
- Smoke status: `completed`; all 18 planned smoke cells ran with `ok` status.
- Formal recommended now: yes for Phase 10C infrastructure readiness, but only after treating the smoke as pipeline evidence rather than a paper result.

No paper files were modified. No Phase 5, Phase 8A, or Phase 8C results were rerun. No formal non-obviousness shards were run.

## 2. Real API Grounding Human-Review Package

Generated files:

- `runs/schema_mutation/phase10/phase10b/human_review/api_evolution_annotation_sheet.csv`
- `runs/schema_mutation/phase10/phase10b/human_review/api_evolution_annotation_sheet.md`
- `runs/schema_mutation/phase10/phase10b/human_review/real_case_candidate_review_sheet.csv`
- `runs/schema_mutation/phase10/phase10b/human_review/real_case_candidate_review_sheet.md`
- `runs/schema_mutation/phase10/phase10b/human_review/annotation_guidelines.md`
- `runs/schema_mutation/phase10/phase10b/human_review_package_manifest.json`

Package contents:

- Annotation sheet entries: 151.
- Providers: 9.
- C-class candidates: 61.
- Real-case candidates: 3.

The annotation sheet keeps Phase 10A automatic labels under `auto_*` fields and leaves `human_*` fields blank for manual review. The guidelines define A/B/C/D labels, C1--C4 subclasses, schema-invisible changes, runtime visibility, high-confidence C-class criteria, and conservative review rules.

Manual review required before paper integration:

- Confirm each candidate label against the official source URL and short evidence snippet.
- Mark uncertain cases as `unclear` rather than forcing a taxonomy class.
- Decide which examples, if any, are safe to use as paper examples.
- Treat the corpus as public-changelog grounding only, not as production-frequency evidence.

Real-case candidate review sheet covers:

- GitHub C3 default behavior candidate.
- Stripe C1 scale/validation candidate.
- Stripe C4 payment restriction candidate.

The sheet asks reviewers to assess source sufficiency, before/after semantic clarity, schema-invisible or semantic-contract nature, deterministic wrapper feasibility, agent-task feasibility, oracle feasibility, best Phase 10C candidate, and risks.

## 3. Oracle Review Package

Generated files:

- `runs/schema_mutation/phase10/phase10b/oracle_review/oracle_review_sheet.csv`
- `runs/schema_mutation/phase10/phase10b/oracle_review/oracle_review_guidelines.md`
- `runs/schema_mutation/phase10/phase10b/oracle_review/oracle_review_summary.md`

Package contents:

- Oracle samples: 180.
- Categories: `baseline_success_unmutated=50`, `o0_hidden_violation_positive=50`, `o0_non_hidden_violation_negative=50`, `o3_o4_recovered=30`.
- Baseline oracle violation rate from Phase 10A packet: 0.0%.

Human labels needed:

- `human_oracle_correct`
- `human_failure_type`
- `human_confidence`
- `human_notes`

The package does not compute agreement statistics because no independent human annotation has been collected yet.

## 4. Non-Obviousness Smoke

Scripts added:

- `code/schema_mutation/phase10_run_nonobviousness_smoke.py`
- `code/schema_mutation/phase10_summarize_nonobviousness.py`
- `code/schema_mutation/phase10_run_nonobviousness_formal.py`
- `code/schema_mutation/phase10_summarize_nonobviousness_formal.py`

Runner hook added:

- `code/schema_mutation/runner.py` now supports a gated `phase10_nonobviousness` prompt hook.
- The hook is inactive for ordinary Phase 5/8 runs.
- `reflection_scaffold` adds generic plan-and-check guidance without exposing the evolved rule.
- `rule_visible_preamble` exposes the evolved rule only for the upper-bound condition.
- The hook was runtime-validated by the completed Phase 10B smoke.

Command run:

```bash
python code/schema_mutation/phase10_run_nonobviousness_smoke.py \
  --shard runs/schema_mutation/phase10/nonobviousness/shards/nonobviousness_smoke.jsonl \
  --max-workers 1
```

Summary command:

```bash
python -m code.schema_mutation.phase10_summarize_nonobviousness
```

Generated files:

- `runs/schema_mutation/phase10/phase10b/nonobviousness_smoke/smoke_results.jsonl`
- `runs/schema_mutation/phase10/phase10b/nonobviousness_smoke/smoke_raw.jsonl`
- `runs/schema_mutation/phase10/phase10b/nonobviousness_smoke/smoke_summary.md`
- `runs/schema_mutation/phase10/phase10b/nonobviousness_smoke/smoke_summary.json`
- `runs/schema_mutation/phase10/phase10b/nonobviousness_smoke/smoke_run_metadata.json`

Smoke shard:

- Planned cells: 18.
- Actually run cells: 18.
- Status counts: `ok=18`.
- Stop-rule events: none.
- Previous preflight issue resolved in the active Windows Python environment: `tau_bench` imports successfully.
- Provider credentials were loaded from `.env`.
- `smoke_raw.jsonl` contains 18 rows, confirming all smoke cells produced raw runner output.

Cells by condition:

| condition | planned | run | status |
| --- | ---: | ---: | --- |
| O0_increased_reasoning_budget | 8 | 8 | ok=8 |
| O0_reflection_scaffold | 8 | 8 | ok=8 |
| rule_in_tool_preamble_upper_bound | 2 | 2 | ok=2 |

Smoke interpretation:

- O0 increased reasoning budget: 0/8 mutation successes; 8/8 hidden violations.
- O0 reflection scaffold: 0/8 mutation successes; 8/8 hidden violations.
- Rule-in-tool-preamble upper bound: 1/2 mutation successes; 0/2 hidden violations.
- Rule-in-prompt upper bound improves: true in smoke.
- O0 reasoning/reflection still struggles: true in smoke.
- Reflection hook worked at runtime: yes, all reflection smoke cells ran with `scaffold_type=reflection_scaffold`.
- Rule-in-prompt upper bound worked at runtime: yes, both upper-bound smoke cells surfaced visible policy errors; one succeeded and one failed.
- This is pipeline smoke evidence only, not a final experimental conclusion.

## 5. Recommended Phase 10C

The 18-cell smoke completed without stop-rule events. Phase 10C can include:

- `O0_increased_reasoning_budget`
- `O0_reflection_scaffold`
- `rule_in_tool_preamble_upper_bound`

Reflection cells no longer need to be excluded on hook-readiness grounds; the Phase 10B smoke confirms the prompt hook works at runtime. The formal run should still remain isolated under Phase 10 output paths and should not overwrite frozen Phase 5/8 results.

Formal runner readiness:

- `phase10_run_nonobviousness_formal.py` writes only under `runs/schema_mutation/phase10/phase10c/nonobviousness_formal/`.
- `phase10_summarize_nonobviousness_formal.py` summarizes Phase 10C formal status files without reading or updating paper outputs.
- Non-API dry-run succeeded for `nonobviousness_0000.jsonl`.
- Validation/preflight checks passed for all 8 formal shards: 288 cells, `dashscope/deepseek` only, and 96 cells per condition.
- No formal Phase 10C cells were executed while preparing these scripts.

Formal shard inventory, not run:

- `nonobviousness_0000.jsonl` through `nonobviousness_0006.jsonl`: 40 cells each.
- `nonobviousness_0007.jsonl`: 8 cells.
- Total formal planned cells: 288.
- Phase 10A runner-ready subset before the hook: 192.
- With the Phase 10B hook implemented and smoke-validated, all 288 are technically runnable from the hook-readiness perspective, subject to Phase 10C stop rules and provider availability.

Estimated API calls:

- Completed smoke retry after dependency fix: 18 cells.
- Formal all-condition run: 288 cells.
- Conservative formal without reflection cells: 192 cells.

## 6. What Not To Claim Yet

- Do not claim production frequency until human review of corpus labels is complete.
- Do not claim human-validated oracle precision until human labels are collected.
- Do not claim stronger reasoning fails based on smoke alone.
- Do not merge Phase 10B smoke into paper main results.
- Do not treat the 18-cell smoke as formal Phase 10C evidence.
- Do not treat GPT/WYZ/Grok provider errors as scientific evidence.
- Do not treat the old Phase 10B preflight stop as evidence about agent reasoning or semantic observability.

## 7. Success-Criteria Check

- Human-review annotation package exists: yes.
- Oracle-review package exists: yes.
- Non-obviousness smoke runs or safely stops with actionable reason: ran successfully, 18/18 `ok`.
- No formal shard run: yes.
- No paper edits: yes.
- No raw artifact corruption: yes.
- Phase 10C readiness stated: ready from the Phase 10B smoke/infrastructure perspective; still requires a separate explicit formal run.
