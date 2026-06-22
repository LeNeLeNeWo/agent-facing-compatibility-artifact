# Trace Case Summary

No API calls or experiment reruns were performed. Cases are extracted from existing Phase 8C raw artifacts and summarized without full logs or credentials.

## A_silent_compliant_semantic_failure
- Cell: `p8c_b5ee615dd16c`; airline, `dashscope/glm-5.1`, task 0, seed 1, C1 / O0_silent.
- Schema changed: False; typed-client compatible: True; target tool called: True.
- Agent action: book_reservation with certificate $250 plus card $5.
- API feedback: No visible policy error; call remains syntactically valid.
- Outcome: reward=0, hidden_business_rule_violation=true.
- Interpretation: The agent follows the baseline-compatible payment workflow, but the evolved semantic rule is silent and only the hidden oracle detects the violation.

## B_visible_recovery
- Cell: `p8c_500fb2fc42ff`; airline, `dashscope/glm-5.1`, task 0, seed 1, C1 / O3_structured_policy_error.
- Schema changed: False; typed-client compatible: True; target tool called: True.
- Agent action: book_reservation revised to card-only payment $255.
- API feedback: Structured policy error on payment_methods: Use a single payment method or request explicit approval.
- Outcome: reward=1, hidden_business_rule_violation=false.
- Interpretation: The visible diagnostic exposes the changed semantic rule; the agent changes the payment workflow and completes the task.
