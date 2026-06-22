# Phase 8C C1-C3 Semantic-Class Generalization Review

## Integrity
- completed_rows_latest: 480
- ok: 480
- provider_error: 0
- timeout: 0
- failed: 0
- formal_rows_after_filters: 480
- no_gpt_wyz_grok: True
- schema_changed_rows: 0
- baseline_failed_rows: 0

## Overall by Semantic Class
| Class | O0 N | O0 Success | Visible N | Visible Success | O0 Hidden | Visible Hidden | Uplift | 95% CI | Fisher p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C1 | 80 | 43.8% | 80 | 85.0% | 50.0% | 0.0% | +41.2 pp | [+27.5 pp, +53.8 pp] | 6.82e-08 |
| C2 | 80 | 56.2% | 80 | 85.0% | 40.0% | 0.0% | +28.7 pp | [+15.0 pp, +41.3 pp] | 0.000108 |
| C3 | 80 | 56.2% | 80 | 91.2% | 36.2% | 0.0% | +35.0 pp | [+22.5 pp, +46.2 pp] | 5.81e-07 |

## By Domain
### airline
- C1: N=112, O0=48.2%, visible=83.9%
- C2: N=112, O0=53.6%, visible=85.7%
- C3: N=112, O0=60.7%, visible=89.3%
### retail
- C1: N=48, O0=33.3%, visible=87.5%
- C2: N=48, O0=62.5%, visible=83.3%
- C3: N=48, O0=45.8%, visible=95.8%

## By Model
### dashscope/glm-5.1
- C1: N=40, O0=45.0%, visible=90.0%
- C2: N=40, O0=65.0%, visible=90.0%
- C3: N=40, O0=55.0%, visible=100.0%
### dashscope/kimi-k2.6
- C1: N=40, O0=50.0%, visible=80.0%
- C2: N=40, O0=85.0%, visible=100.0%
- C3: N=40, O0=55.0%, visible=95.0%
### dashscope/qwen-max
- C1: N=40, O0=30.0%, visible=70.0%
- C2: N=40, O0=20.0%, visible=65.0%
- C3: N=40, O0=45.0%, visible=80.0%
### deepseek/deepseek-v4-flash
- C1: N=40, O0=50.0%, visible=100.0%
- C2: N=40, O0=55.0%, visible=85.0%
- C3: N=40, O0=70.0%, visible=90.0%

## Main Answer
- c1_c3_produce_schema_compatible_agent_facing_regressions: True
- visible_feedback_helps_beyond_c4: True
- direction_consistent_enough_for_c_class_generalization: True
