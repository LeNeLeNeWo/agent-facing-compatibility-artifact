# Phase 10C Formal Run Report: Non-Obviousness Control

## 1. Executive Summary

- Formal run completed: yes, terminal-complete.
- Planned cells: 288.
- Completed/observed cells: 288.
- Status counts: `ok=286`, `failed=1`, `timeout=1`.
- Stop-rule events: none. No shard reached `provider_error >= 5`, `timeout >= 5`, or `failed >= 5`.
- Formal summary generated:
  - `runs/schema_mutation/phase10/phase10c/nonobviousness_formal/formal_summary.md`
  - `runs/schema_mutation/phase10/phase10c/nonobviousness_formal/formal_summary.json`

All 8 formal shards wrote metadata with `status=completed`. The run is not clean-complete because two cells have non-ok infrastructure statuses, but it is terminal-complete and ready for Phase 10D with explicit handling of the non-ok rows.

## 2. Environment

- Python used for the formal runner: `D:\anaconda\python.exe`.
- Python version checked before formal execution: Python 3.13.9.
- Virtual environment: no project venv was activated; the successful Phase 10B/10C runner used the Windows Anaconda Python environment.
- `tau_bench` import path checked before formal execution: `C:\Users\yang\AppData\Roaming\Python\Python313\site-packages\tau_bench\__init__.py`.
- Formal run window: shard `0000` completed at `2026-06-21T19:19:15`; the sequential controller for shards `0001` through `0007` ran from `2026-06-21T19:21:20` to `2026-06-22T00:47:31`.

Runner commands:

```bash
python code/schema_mutation/phase10_run_nonobviousness_formal.py \
  --shard runs/schema_mutation/phase10/nonobviousness/shards/nonobviousness_0000.jsonl \
  --output-dir runs/schema_mutation/phase10/phase10c/nonobviousness_formal \
  --max-workers 1 \
  --skip-existing
```

Then shards `0001` through `0007` were run in order with the same runner, output directory, `--max-workers 1`, and `--skip-existing`.

Summarizer command:

```bash
python code/schema_mutation/phase10_summarize_nonobviousness_formal.py \
  --input-dir runs/schema_mutation/phase10/phase10c/nonobviousness_formal \
  --output-md runs/schema_mutation/phase10/phase10c/nonobviousness_formal/formal_summary.md \
  --output-json runs/schema_mutation/phase10/phase10c/nonobviousness_formal/formal_summary.json
```

## 3. Formal Results Overview

| condition | planned | observed | ok | status counts | success | hidden violation |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| O0_increased_reasoning_budget | 96 | 96 | 96 | ok=96 | 3/96 = 3.1% | 92/96 = 95.8% |
| O0_reflection_scaffold | 96 | 96 | 95 | ok=95, failed=1 | 6/95 = 6.3% | 88/95 = 92.6% |
| rule_in_tool_preamble_upper_bound | 96 | 96 | 95 | ok=95, timeout=1 | 71/95 = 74.7% | 0/95 = 0.0% |

Preliminary contrast:

- O0 increased reasoning remained low-recovery: 3.1% success among ok rows, with 95.8% hidden violations.
- O0 reflection scaffold also remained low-recovery: 6.3% success among ok rows, with 92.6% hidden violations.
- Rule-visible upper bound recovered much more often: 74.7% success among ok rows, with 0.0% hidden violations and 96.8% visible policy-error rate.
- This is a Phase 10C formal run result, not a paper-integrated claim yet. Phase 10D should decide the statistical treatment and how to handle non-ok infrastructure rows.

Splits:

- Domain/status: `airline/ok=172`, `airline/failed=1`, `airline/timeout=1`, `retail/ok=114`.
- Model/status: `dashscope/glm-5.1/ok=74`, `dashscope/glm-5.1/timeout=1`, `dashscope/kimi-k2.6/ok=69`, `dashscope/qwen-max/ok=77`, `dashscope/qwen-max/failed=1`, `deepseek/deepseek-v4-flash/ok=66`.
- C-class/status: `C1/ok=81`, `C2/ok=57`, `C3/ok=67`, `C3/failed=1`, `C3/timeout=1`, `C4/ok=81`.

Non-ok rows:

- `failed`: `p10_nonobv_a1a33c598319`, condition=`O0_reflection_scaffold`, model=`dashscope/qwen-max`, class=`C3`.
- `timeout`: `p10_nonobv_8bc60a8c512f`, condition=`rule_in_tool_preamble_upper_bound`, model=`dashscope/glm-5.1`, class=`C3`.

## 4. Integrity

- Frozen main result modification: not detected; Phase 10C runner writes only under `runs/schema_mutation/phase10/phase10c/nonobviousness_formal/`.
- Phase 5/8 outputs modified: not detected; no Phase 5, Phase 8A, or Phase 8C runner was invoked, and no files under Phase 5/8 or paper directories were modified after the Phase 10C formal start time.
- Provider-error rows counted as agent failures: no. Provider errors are tracked separately; this run had `provider_error=0`.
- Rule leakage detected: no. O0 increased reasoning and O0 reflection cells stayed `O0_silent` and did not use `rule_visible_preamble`.
- Fake rows: 0.
- Baseline-success false rows: 0.
- Schema-changed-not-false rows: 0.
- JSONL integrity: status files contain 288 rows; raw files contain 286 rows, matching the 286 ok cells. The 1 failed row and 1 timeout row do not have raw result payloads.

## 5. Recommendation

- Phase 10D statistical analysis should proceed, but it must explicitly handle the 2 non-ok infrastructure rows.
- Recommended before paper integration: either retry the 1 failed row and 1 timeout row in the same Phase 10C output namespace with `--skip-existing`, or pre-register an exclusion rule for non-ok infrastructure rows in Phase 10D.
- Reflection scaffold was fully supported at the runner-hook level: reflection cells executed, and 95/96 produced ok status.
- The formal result is strong enough to address the obviousness critique at the experiment-result level: stronger O0 reasoning/reflection remains low-recovery, while rule-visible upper bound recovers substantially more often. The final statistical claim should wait for Phase 10D.

## 6. What Not To Claim Yet

- Do not merge Phase 10C into the paper until Phase 10D validates statistics and non-ok handling.
- Do not claim human-validated oracle precision.
- Do not claim production frequency.
- Do not claim real API case replay yet.
- Do not treat the 1 failed row or 1 timeout row as agent failures.
