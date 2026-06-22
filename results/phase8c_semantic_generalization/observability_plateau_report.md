# Observability Plateau Analysis

No API calls or experiment reruns were performed. This analysis reads the frozen 1,815-cell Phase 5 observability status artifacts, filters to formal `ok` rows, excludes smoke/fake/provider-error/timeout/failed rows, and deduplicates by `cell_key`.

## Integrity
- Rows after filters: 1815
- Complete paired units: 363
- Level counts: O0_silent=363, O1_generic_error=363, O2_policy_error=363, O3_structured_policy_error=363, O4_migration_note=363
- Provider error / timeout / failed counted as agent-facing regression: no

## Overall Plateau
| Condition | N | Success | Rate |
| --- | ---: | ---: | ---: |
| O0_silent | 363 | 182 | 50.1% |
| O1_generic_error | 363 | 306 | 84.3% |
| O2_policy_error | 363 | 307 | 84.6% |
| O3_structured_policy_error | 363 | 309 | 85.1% |
| O4_migration_note | 363 | 308 | 84.8% |

- O0 silent vs any visible O1--O4: 50.1% vs 84.7%; difference +34.6 pp visible-minus-O0, bootstrap 95% CI [+29.7 pp, +39.5 pp], Fisher exact p=2.43e-12.
- O0 vs O1 generic error: 50.1% vs 84.3%; difference +34.2 pp O1-minus-O0, bootstrap 95% CI [+28.4 pp, +39.7 pp], Fisher exact p=1.25e-12.
- O1 vs O2_policy_error: 84.3% vs 84.6%; marginal +0.3 pp O2_policy_error-minus-O1, bootstrap 95% CI [-4.1 pp, +4.7 pp], Fisher exact p=1.
- O1 vs O3_structured_policy_error: 84.3% vs 85.1%; marginal +0.8 pp O3_structured_policy_error-minus-O1, bootstrap 95% CI [-3.3 pp, +5.0 pp], Fisher exact p=0.837.
- O1 vs O4_migration_note: 84.3% vs 84.8%; marginal +0.6 pp O4_migration_note-minus-O1, bootstrap 95% CI [-3.6 pp, +5.0 pp], Fisher exact p=0.918.

## By Domain
### airline
| Level | N | Success rate |
| --- | ---: | ---: |
| O0_silent | 258 | 53.9% |
| O1_generic_error | 258 | 83.7% |
| O2_policy_error | 258 | 86.0% |
| O3_structured_policy_error | 258 | 85.3% |
| O4_migration_note | 258 | 84.5% |
- O0 to any visible uplift: +31.0 pp; bootstrap 95% CI [+25.3 pp, +36.7 pp], Fisher p=2.23e-12.
### retail
| Level | N | Success rate |
| --- | ---: | ---: |
| O0_silent | 105 | 41.0% |
| O1_generic_error | 105 | 85.7% |
| O2_policy_error | 105 | 81.0% |
| O3_structured_policy_error | 105 | 84.8% |
| O4_migration_note | 105 | 85.7% |
- O0 to any visible uplift: +43.3 pp; bootstrap 95% CI [+33.8 pp, +52.9 pp], Fisher p=4.84e-13.

## By Model
- `dashscope/glm-5.1`: O0_silent=50.9%, O1_generic_error=82.4%, O2_policy_error=89.8%, O3_structured_policy_error=88.0%, O4_migration_note=85.2%; O0-to-any-visible uplift +35.4 pp, bootstrap 95% CI [+26.4 pp, +44.4 pp], Fisher p=7.31e-13.
- `dashscope/kimi-k2.6`: O0_silent=53.5%, O1_generic_error=90.9%, O2_policy_error=85.9%, O3_structured_policy_error=87.9%, O4_migration_note=87.9%; O0-to-any-visible uplift +34.6 pp, bootstrap 95% CI [+24.7 pp, +44.2 pp], Fisher p=3.89e-13.
- `dashscope/qwen-max`: O0_silent=30.2%, O1_generic_error=69.8%, O2_policy_error=73.6%, O3_structured_policy_error=71.7%, O4_migration_note=73.6%; O0-to-any-visible uplift +42.0 pp, bootstrap 95% CI [+26.4 pp, +56.1 pp], Fisher p=4.26e-08.
- `deepseek/deepseek-v4-flash`: O0_silent=56.3%, O1_generic_error=87.4%, O2_policy_error=83.5%, O3_structured_policy_error=86.4%, O4_migration_note=87.4%; O0-to-any-visible uplift +29.9 pp, bootstrap 95% CI [+21.4 pp, +38.1 pp], Fisher p=2.36e-10.

## Answer
The dominant empirical effect is the transition from silent drift to visible feedback. O1 already recovers most of the lost success. O1--O4 differences are smaller, not strictly monotonic, and vary by domain and model.

The dominant effect is visibility itself. The paper should not claim that richer feedback formats strictly dominate simpler ones.
