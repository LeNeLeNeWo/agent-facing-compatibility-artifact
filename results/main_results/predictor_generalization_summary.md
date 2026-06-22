# Predictor Generalization Summary

Samples: 2174
Positive rate: 0.257
sklearn available: True

| Feature family | Random F1 | Leave-task F1 | Leave-tool F1 | Leave-policy F1 | Leave-model F1 |
|---|---:|---:|---:|---:|---:|
| majority | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| schema_diff_only | 0.409 | 0.439 | 0.412 | 0.409 | 0.350 |
| semantic_only | 0.408 | 0.437 | 0.410 | 0.408 | 0.350 |
| exposure_only | 0.275 | 0.282 | 0.281 | 0.408 | 0.275 |
| observability_only | 0.548 | 0.575 | 0.555 | 0.200 | 0.548 |
| trajectory_only | 0.279 | 0.286 | 0.286 | 0.276 | 0.220 |
| exposure+semantic | 0.279 | 0.282 | 0.288 | 0.408 | 0.275 |
| exposure+semantic+observability | 0.563 | 0.595 | 0.548 | 0.409 | 0.564 |
| all_features | 0.560 | 0.588 | 0.554 | 0.313 | 0.521 |

Warnings:
- majority:leave_task_out skipped 8 fold(s)
- majority:leave_tool_out skipped 3 fold(s)
- schema_diff_only:leave_task_out skipped 8 fold(s)
- schema_diff_only:leave_tool_out skipped 3 fold(s)
- semantic_only:leave_task_out skipped 8 fold(s)
- semantic_only:leave_tool_out skipped 3 fold(s)
- exposure_only:leave_task_out skipped 8 fold(s)
- exposure_only:leave_tool_out skipped 3 fold(s)
- observability_only:leave_task_out skipped 8 fold(s)
- observability_only:leave_tool_out skipped 3 fold(s)
- trajectory_only:leave_task_out skipped 8 fold(s)
- trajectory_only:leave_tool_out skipped 3 fold(s)
- exposure+semantic:leave_task_out skipped 8 fold(s)
- exposure+semantic:leave_tool_out skipped 3 fold(s)
- exposure+semantic+observability:leave_task_out skipped 8 fold(s)
- exposure+semantic+observability:leave_tool_out skipped 3 fold(s)
- all_features:leave_task_out skipped 8 fold(s)
- all_features:leave_tool_out skipped 3 fold(s)
