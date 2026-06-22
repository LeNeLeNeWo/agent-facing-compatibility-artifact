# Real Case Candidate Review Sheet

These three candidates are not treated as fully validated examples. Reviewers should inspect the official source URL and decide whether each case is suitable for a deterministic Phase 10C replay.

| case_id | provider | real_change_type | source_url | possible_oracle | risks |
| --- | --- | --- | --- | --- | --- |
| real_c3_default_behavior_8b11a458888a | GitHub | C3 | https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout | Check that omitted optional fields produce the expected changed default outcome. | Requires human review of the official entry before paper use; wrapper should not claim a real production outage. |
| real_c1_unit_scale_0a2066fde082 | Stripe | C1 | https://docs.stripe.com/changelog/dahlia/2026-04-22/billing-meter-event-values-validation.md | Deterministically check final state value after unit/scale conversion. | Requires human review of the official entry before paper use; wrapper should not claim a real production outage. |
| real_c4_business_rule_323e42cd6611 | Stripe | C4 | https://docs.stripe.com/changelog/dahlia/2026-05-27/adds-card-brand-restrictions-to-payment-links.md | Check that final state satisfies the changed eligibility/policy rule. | Requires human review of the official entry before paper use; wrapper should not claim a real production outage. |

## Reviewer Decisions Needed

- Is the official source evidence sufficient?
- Are before/after semantics clear enough for a wrapper?
- Is the schema-invisible or semantic-contract nature clear?
- Can we construct a deterministic wrapper, agent task, and oracle?
- Which candidate is the best Phase 10C real-case replay target?
