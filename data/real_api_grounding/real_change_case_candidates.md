# Real Semantic-Change Case Candidates

## real_c3_default_behavior_8b11a458888a

- Provider: GitHub
- Source: https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout
- Type: C3
- Why semantic: Semantic behavior keyword matched; subclass=C3_default_behavior.
- Task template: Agent omits an optional setting whose default behavior changed.
- Oracle: Check that omitted optional fields produce the expected changed default outcome.
- Risks: Requires human review of the official entry before paper use; wrapper should not claim a real production outage.

## real_c1_unit_scale_0a2066fde082

- Provider: Stripe
- Source: https://docs.stripe.com/changelog/dahlia/2026-04-22/billing-meter-event-values-validation.md
- Type: C1
- Why semantic: Semantic behavior keyword matched; subclass=C1_unit_scale.
- Task template: Agent must choose an amount, quantity, weight, fee, or threshold whose unit/scale changed.
- Oracle: Deterministically check final state value after unit/scale conversion.
- Risks: Requires human review of the official entry before paper use; wrapper should not claim a real production outage.

## real_c4_business_rule_323e42cd6611

- Provider: Stripe
- Source: https://docs.stripe.com/changelog/dahlia/2026-05-27/adds-card-brand-restrictions-to-payment-links.md
- Type: C4
- Why semantic: Semantic behavior keyword matched; subclass=C4_business_rule.
- Task template: Agent must satisfy an eligibility, billing, payment, refund, or policy rule that changed.
- Oracle: Check that final state satisfies the changed eligibility/policy rule.
- Risks: Requires human review of the official entry before paper use; wrapper should not claim a real production outage.
