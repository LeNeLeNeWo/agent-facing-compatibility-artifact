# Phase 8C C1-C3 Semantic-Class Generalization Report

## 1. Plan Counts
- planned formal cells: 480
- by semantic class: {'C1': 160, 'C2': 160, 'C3': 160}
- by observability level: {'O0_silent': 240, 'O3_structured_policy_error': 240}
- by domain: {'airline': 336, 'retail': 144}
- by model: {'dashscope/glm-5.1': 120, 'dashscope/kimi-k2.6': 120, 'dashscope/qwen-max': 120, 'deepseek/deepseek-v4-flash': 120}
- planned mutations: C1_unit_scale_drift, C2_currency_locale_drift, C3_default_behavior_drift
- planned excluded mutation classes: A/B/D and C4

## 2. Smoke Status
- smoke cells latest: 12
- status: {'ok': 12}
- by class: {'C1': 4, 'C2': 4, 'C3': 4}
- O0 hidden violations: 6/6
- O3 structured visible: 6/6
- smoke passed stop rules: yes

## 3. Formal Status
- baseline_failed_rows: 0
- completed_rows_latest: 480
- failed: 0
- formal_rows_after_filters: 480
- no_gpt_wyz_grok: True
- ok: 480
- provider_error: 0
- schema_changed_rows: 0
- timeout: 0
- transient retry: 1 DashScope read timeout retried successfully by cell_key

## 4. C1 Result
- mutation: C1_unit_scale_drift
- O0: N=80, success=43.8%, hidden_violation=50.0%
- O3 visible: N=80, success=85.0%, hidden_violation=0.0%
- visible minus O0 success uplift: +41.2 pp; bootstrap 95% CI [+27.5 pp, +53.8 pp]
- Fisher exact p-value: 6.82e-08

## 5. C2 Result
- mutation: C2_currency_locale_drift
- O0: N=80, success=56.2%, hidden_violation=40.0%
- O3 visible: N=80, success=85.0%, hidden_violation=0.0%
- visible minus O0 success uplift: +28.7 pp; bootstrap 95% CI [+15.0 pp, +41.3 pp]
- Fisher exact p-value: 0.000108

## 6. C3 Result
- mutation: C3_default_behavior_drift
- O0: N=80, success=56.2%, hidden_violation=36.2%
- O3 visible: N=80, success=91.2%, hidden_violation=0.0%
- visible minus O0 success uplift: +35.0 pp; bootstrap 95% CI [+22.5 pp, +46.2 pp]
- Fisher exact p-value: 5.81e-07

## 7. O0 vs Visible Comparison
- All three semantic classes have lower O0 success than O3 visible feedback.
- All three semantic classes produce hidden business-rule/semantic violations under O0.
- O3 visible feedback eliminates hidden violations in the completed formal rows and raises task success by +28.7 to +41.2 percentage points depending on class.

## 8. By-Domain Summary
- airline: C1 O0=48.2% visible=83.9% N=112; C2 O0=53.6% visible=85.7% N=112; C3 O0=60.7% visible=89.3% N=112
- retail: C1 O0=33.3% visible=87.5% N=48; C2 O0=62.5% visible=83.3% N=48; C3 O0=45.8% visible=95.8% N=48

## 9. By-Model Summary
- dashscope/glm-5.1: C1 O0=45.0% visible=90.0% N=40; C2 O0=65.0% visible=90.0% N=40; C3 O0=55.0% visible=100.0% N=40
- dashscope/kimi-k2.6: C1 O0=50.0% visible=80.0% N=40; C2 O0=85.0% visible=100.0% N=40; C3 O0=55.0% visible=95.0% N=40
- dashscope/qwen-max: C1 O0=30.0% visible=70.0% N=40; C2 O0=20.0% visible=65.0% N=40; C3 O0=45.0% visible=80.0% N=40
- deepseek/deepseek-v4-flash: C1 O0=50.0% visible=100.0% N=40; C2 O0=55.0% visible=85.0% N=40; C3 O0=70.0% visible=90.0% N=40

## 10. Supports Generalization Beyond C4
- c1_c3_produce_schema_compatible_agent_facing_regressions: True
- direction_consistent_enough_for_c_class_generalization: True
- visible_feedback_helps_beyond_c4: True
- interpretation: compliant semantic failure is not limited to C4 business-rule drift; C1 unit/scale, C2 currency/locale, and C3 default-behavior drifts also create agent-facing regressions when execution-exposed.

## 11. Generated Review Packet Paths
- `runs/schema_mutation/phase8/c_semantic_generalization/c_semantic_generalization_review_packet.md`
- `runs/schema_mutation/phase8/c_semantic_generalization/c_semantic_generalization_review_packet.json`
- `runs/schema_mutation/phase8/c_semantic_generalization/c_semantic_generalization_plan.md`
- `runs/schema_mutation/phase8/c_semantic_generalization/c_semantic_generalization_plan.jsonl`

## 12. Generated Table/Figure Paths
- `IEEE_Conference_Template/tables/c_semantic_generalization_auto.tex`
- `IEEE_Conference_Template/figures/c_semantic_generalization.pdf`
- Optional table/figure were also synced to the WSL paper directory when available.

## 13. Additional Cells Needed
- No additional cells required for the stated Phase 8C acceptance criteria: total formal rows >=300, each class >=80 rows, both domains represented, and all four frozen formal models covered.
