# Cluster-Aware Statistics Audit

Offline sensitivity analysis over persisted artifacts. No experiments or model APIs were run.

## phase5_o4_minus_o0
- `n_o0`: 363
- `n_o4`: 363
- `rate_o0`: 0.5014 (50.1%)
- `rate_o4`: 0.8485 (84.8%)
- `raw_diff`: 0.3471 (34.7%)
- `ordinary_bootstrap_ci`: `{"ci": [0.28099173553719015, 0.41046831955922863], "samples": 2000}`
- `cluster_by_env_task_ci`: `{"ci": [0.2128124999999999, 0.4985856468366383], "clusters": 45, "samples": 2000}`
- `paired_by_env_model_task_seed_n`: 363
- `paired_cluster_by_task_ci`: `{"ci": [0.21447725559185724, 0.49835214829894203], "clusters": 45, "samples": 2000}`
- `direction_supported_by_cluster_ci`: `true`

## phase5_any_visible_minus_o0
- `n_o0`: 363
- `n_any_visible`: 1452
- `rate_o0`: 0.5014 (50.1%)
- `rate_any_visible`: 0.8471 (84.7%)
- `raw_diff`: 0.3457 (34.6%)
- `ordinary_bootstrap_ci`: `{"ci": [0.28787878787878785, 0.39876033057851235], "samples": 2000}`
- `cluster_by_task_ci`: `{"ci": [0.21594060900655285, 0.4926772167173639], "clusters": 45, "samples": 2000}`
- `note`: Any-visible pools O1--O4 rows; task-cluster bootstrap is a sensitivity check for shared tasks.
- `direction_supported_by_cluster_ci`: `true`

## phase8a_unused_minus_exposed_o0
- `n_exposed`: 363
- `n_unused`: 363
- `rate_exposed`: 0.5014 (50.1%)
- `rate_unused`: 0.7631 (76.3%)
- `raw_diff`: 0.2617 (26.2%)
- `ordinary_bootstrap_ci`: `{"ci": [0.1955922865013774, 0.3278236914600551], "samples": 2000}`
- `paired_cluster_by_task_ci`: `{"ci": [0.1502754467298495, 0.37848538359325806], "clusters": 45, "samples": 2000}`
- `paired_cluster_by_source_cell_ci`: `{"ci": [0.20385674931129477, 0.3168044077134986], "clusters": 363, "samples": 2000}`
- `direction_supported_by_cluster_ci`: `true`

## phase10d_visible_minus_O0_increased_reasoning_budget
- `n_o0_variant`: 96
- `n_visible`: 95
- `rate_o0_variant`: 0.0312 (3.1%)
- `rate_visible`: 0.7474 (74.7%)
- `raw_diff`: 0.7161 (71.6%)
- `ordinary_bootstrap_ci`: `{"ci": [0.6212719298245614, 0.8004413377192983], "samples": 2000}`
- `cluster_by_source_o0_cell_ci`: `{"ci": [0.625, 0.8020833333333333], "clusters": 96, "samples": 2000}`
- `cluster_by_task_ci`: `{"ci": [0.5721185388516197, 0.8333333333333333], "clusters": 26, "samples": 2000}`
- `direction_supported_by_cluster_ci`: `true`

## phase10d_visible_minus_O0_reflection_scaffold
- `n_o0_variant`: 95
- `n_visible`: 95
- `rate_o0_variant`: 0.0632 (6.3%)
- `rate_visible`: 0.7474 (74.7%)
- `raw_diff`: 0.6842 (68.4%)
- `ordinary_bootstrap_ci`: `{"ci": [0.5894736842105263, 0.7789473684210526], "samples": 2000}`
- `cluster_by_source_o0_cell_ci`: `{"ci": [0.5857754759238522, 0.7775075783573552], "clusters": 96, "samples": 2000}`
- `cluster_by_task_ci`: `{"ci": [0.5333299798792757, 0.803257722007722], "clusters": 26, "samples": 2000}`
- `direction_supported_by_cluster_ci`: `true`

## phase10f_real_replay_visible_minus_silent
- `n_silent`: 23
- `n_visible`: 23
- `rate_silent`: 0.0000 (0.0%)
- `rate_visible`: 0.9565 (95.7%)
- `raw_diff`: 0.9565 (95.7%)
- `ordinary_bootstrap_ci`: `{"ci": [0.8695652173913043, 1.0], "samples": 2000}`
- `cluster_by_case_id_ci`: `{"ci": [0.9166666666666666, 1.0], "clusters": 2, "samples": 2000}`
- `note`: case-level cluster bootstrap has only two clusters and should be treated as sensitivity evidence, not a precise interval.
- `direction_supported_by_cluster_ci`: `true`

## phase10f_real_replay_baseline_minus_silent
- `n_baseline`: 24
- `n_silent`: 23
- `rate_baseline`: 1.0000 (100.0%)
- `rate_silent`: 0.0000 (0.0%)
- `raw_diff`: 1.0000 (100.0%)
- `cluster_by_case_id_ci`: `{"ci": [1.0, 1.0], "clusters": 2, "samples": 2000}`
- `direction_supported_by_cluster_ci`: `true`

## Recommendation
The direction of the headline effects remains positive under available cluster-bootstrap sensitivity checks. Fisher exact p-values should be treated as descriptive because rows share tasks, models, and source cells; the paper should emphasize effect sizes and cluster-bootstrap sensitivity rather than p-values alone.