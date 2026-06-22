# Phase 10E Real Case Audit

- Scope: real-changelog-grounded deterministic replay smoke.
- No real Stripe/GitHub API calls are used.
- Selected cases: real_c1_unit_scale_0a2066fde082, real_c4_business_rule_323e42cd6611
- Not selected: real_c3_default_behavior_8b11a458888a

| case | provider | class | evidence | before/after clear | wrapper | oracle | smoke | risks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| real_c3_default_behavior_8b11a458888a | GitHub | C3 | True | False/True | False | False | False | Requires human review before paper use; replay is grounded in changelog title/evidence and is not a production incident. Exact before/after semantics are under-specified in local evidence. |
| real_c1_unit_scale_0a2066fde082 | Stripe | C1 | True | True/True | True | True | True | Requires human review before paper use; replay is grounded in changelog title/evidence and is not a production incident. |
| real_c4_business_rule_323e42cd6611 | Stripe | C4 | True | True/True | True | True | True | Requires human review before paper use; replay is grounded in changelog title/evidence and is not a production incident. |

## Wrapper Cases

### real_c3_default_behavior_8b11a458888a

- Source: https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout
- Evidence: The pull_request_target event is one of the most commonly misused triggers in GitHub Actions, leading to vulnerabilities in workflows. Workflows triggered by pull_request_target run
- Selected: False
- Reason: Not selected for this smoke. The local Phase 10A evidence names a safer default and includes a truncated snippet, but it does not specify the exact before/after default needed for a faithful deterministic wrapper.
- Old semantics: Insufficiently specified in local evidence for deterministic replay without further human review.
- New semantics: Insufficiently specified in local evidence for deterministic replay without further human review.
- Oracle: None

### real_c1_unit_scale_0a2066fde082

- Source: https://docs.stripe.com/changelog/dahlia/2026-04-22/billing-meter-event-values-validation.md
- Evidence: Billing | Breaking | api
- Selected: True
- Reason: The title gives a concrete validation boundary (>15 digits), enabling a deterministic local oracle.
- Old semantics: The old replay wrapper accepts a billing meter event integer value and records the requested total.
- New semantics: The new replay wrapper treats billing meter event values with more than 15 decimal digits as invalid; large totals must be split across valid events.
- Oracle: Success requires total recorded usage to equal 1234567890123456; under new semantics every individual event value must be <= 999999999999999.

### real_c4_business_rule_323e42cd6611

- Source: https://docs.stripe.com/changelog/dahlia/2026-05-27/adds-card-brand-restrictions-to-payment-links.md
- Evidence: Paymentlinks | Non-breaking | api
- Selected: True
- Reason: The title gives a concrete changed payment policy (card-brand restrictions), enabling a deterministic local oracle.
- Old semantics: The old replay wrapper creates a Payment Link with default card-brand acceptance when the optional restriction field is omitted.
- New semantics: The new replay wrapper requires the Payment Link to respect configured card-brand restrictions for this merchant.
- Oracle: Under new semantics the created Payment Link must restrict accepted card brands to visa and mastercard only.
