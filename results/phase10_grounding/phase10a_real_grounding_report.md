# Phase 10A Real Grounding Report

## 1. Executive Summary

- Real API evolution corpus generated: yes (151 entries, 9 providers).
- High-confidence C-class examples found: 2.
- Real-change case candidates selected: 3.
- Oracle validation packet generated: yes.
- Non-obviousness control plan generated: yes.
- Blockers: none for planning; human review is required before paper integration.

## 2. Real API Grounding Results

- Corpus size: 151
- Providers: Anthropic, GitHub, Google Cloud, OpenAI, Shopify, Slack, Square, Stripe, Twilio
- Taxonomy distribution: {'C': 61, 'mixed': 39, 'A': 11, 'D': 18, 'B': 22}
- C-class subclass distribution: {'none': 30, 'C3_default_behavior': 31, 'C4_business_rule': 29, 'C2_currency_locale': 7, 'C1_unit_scale': 3}
- Schema-invisible C-class candidates: 61

Top examples are listed in `api_evolution_corpus_summary.md`.

## 3. Real-Change Case Candidates
- real_c3_default_behavior_8b11a458888a: GitHub C3 (https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout)
- real_c1_unit_scale_0a2066fde082: Stripe C1 (https://docs.stripe.com/changelog/dahlia/2026-04-22/billing-meter-event-values-validation.md)
- real_c4_business_rule_323e42cd6611: Stripe C4 (https://docs.stripe.com/changelog/dahlia/2026-05-27/adds-card-brand-restrictions-to-payment-links.md)

## 4. Oracle Validation
- Total sampled records: 180
- Sample counts: {'baseline_success_unmutated': 50, 'o0_hidden_violation_positive': 50, 'o0_non_hidden_violation_negative': 50, 'o3_o4_recovered': 30}
- Baseline oracle violation rate: 0.0
- Suspicious samples: 0

## 5. Non-Obviousness Control Plan

- Plan report: generated
- Recommended next action: inspect smoke shard manually, then run only the smoke shard in Phase 10B.

## 6. What Not To Claim Yet

- Do not claim production frequency yet; this corpus samples public changelogs.
- Do not claim human-validated oracle precision until manual review is done.
- Do not claim stronger reasoning fails until Phase 10B runs the non-obviousness controls.
- Do not merge real API grounding into the paper until case candidates are reviewed.
