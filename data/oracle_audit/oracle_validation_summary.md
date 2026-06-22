# Phase 10A Oracle Validation Summary

This packet is human-review-ready. It does not claim human-validated oracle precision.

- Total samples: 180
- Sample counts: {'baseline_success_unmutated': 50, 'o0_hidden_violation_positive': 50, 'o0_non_hidden_violation_negative': 50, 'o3_o4_recovered': 30}
- By env: {'airline': 106, 'retail': 74}
- By model: {'dashscope/glm-5.1': 49, 'dashscope/kimi-k2.6': 45, 'dashscope/qwen-max': 44, 'deepseek/deepseek-v4-flash': 42}
- By semantic class: {'baseline': 50, 'C1': 34, 'C2': 32, 'C3': 32, 'C4': 32}
- Baseline oracle violation rate: 0.0
- O0 positive consistency: 1.0
- O0 negative consistency: 1.0
- Recovered consistency: 1.0
- Suspicious samples: 0

## Suspicious Samples for Human Review

Note: Proxy only: baseline/non-hidden samples approximate specificity and O0 hidden-positive samples approximate rule-trigger consistency. Human annotation is still required for oracle precision.
