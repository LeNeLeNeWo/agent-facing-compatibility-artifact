# Phase 10A Real API Evolution Corpus Summary

This is a public-changelog corpus estimate, not a production incident frequency estimate.

- Total entries: 151
- Providers: 9 (Anthropic, GitHub, Google Cloud, OpenAI, Shopify, Slack, Square, Stripe, Twilio)
- Schema-invisible C-class candidates: 61
- High-confidence C-class examples: 2

## Entries by Provider
- Anthropic: 16
- GitHub: 10
- Google Cloud: 18
- OpenAI: 16
- Shopify: 20
- Slack: 18
- Square: 5
- Stripe: 30
- Twilio: 18

## Taxonomy Distribution
- A: 11
- B: 22
- C: 61
- D: 18
- mixed: 39

## C-Class Subclasses
- C1_unit_scale: 3
- C2_currency_locale: 7
- C3_default_behavior: 31
- C4_business_rule: 29
- none: 30

## Top High-Confidence C-Class Examples
- Twilio | 2010-04-01 | Conference list endpoint will default to in-progress conferences only on July 13, 2026 | C3_default_behavior | https://www.twilio.com/en-us/changelog
- Twilio | 2010-04-01 | Starting July 13, 2026 , the Conference list endpoint (GET /2010-04-01/Accounts/{AccountSid}/Conferences.json) will default to returning only in-progress conferences. | C3_default_behavior | https://www.twilio.com/en-us/changelog

## Case Candidates
- real_c3_default_behavior_8b11a458888a (GitHub): C3 | https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout
- real_c1_unit_scale_0a2066fde082 (Stripe): C1 | https://docs.stripe.com/changelog/dahlia/2026-04-22/billing-meter-event-values-validation.md
- real_c4_business_rule_323e42cd6611 (Stripe): C4 | https://docs.stripe.com/changelog/dahlia/2026-05-27/adds-card-brand-restrictions-to-payment-links.md

## Limitations
- Automatic labels are conservative and require human review before paper integration.
- This is a public-changelog corpus estimate, not a production incident frequency estimate.
- Some provider pages are dynamic; parser failures or noisy entries are recorded in fetch_log.
