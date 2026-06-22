# Phase 10F-R1 Real-Changelog-Grounded Case Replay Formal Report

## 1. Executive Summary

- Cases used: real_c1_unit_scale_0a2066fde082, real_c4_business_rule_323e42cd6611
- Formal cells planned/run: 72/72
- Status counts: failed=2, ok=70
- Provider errors: 0; timeouts: 0; failed: 2
- Headline results: baseline success 24/24 (100.0%); O0 silent success 0/23 (0.0%) with hidden violation 23/23 (100.0%); visible-feedback success 22/23 (95.7%) with hidden violation 0/23 (0.0%).
- Result supports paper integration as a small real-grounding subsection, with careful wording that this is deterministic replay grounded in changelogs, not production incident measurement.

## 2. Case Provenance

### real_c1_unit_scale_0a2066fde082

- Provider: Stripe
- Taxonomy class: C1 (C1_unit_scale)
- Official source URL: https://docs.stripe.com/changelog/dahlia/2026-04-22/billing-meter-event-values-validation.md
- Evidence: Billing | Breaking | api
- Old semantics: The old replay wrapper accepts a billing meter event integer value and records the requested total.
- New semantics: The new replay wrapper treats billing meter event values with more than 15 decimal digits as invalid; large totals must be split across valid events.
- Deterministic oracle: Success requires total recorded usage to equal 1234567890123456; under new semantics every individual event value must be <= 999999999999999.
- Grounding rationale: The title gives a concrete validation boundary (>15 digits), enabling a deterministic local oracle.

### real_c4_business_rule_323e42cd6611

- Provider: Stripe
- Taxonomy class: C4 (C4_business_rule)
- Official source URL: https://docs.stripe.com/changelog/dahlia/2026-05-27/adds-card-brand-restrictions-to-payment-links.md
- Evidence: Paymentlinks | Non-breaking | api
- Old semantics: The old replay wrapper creates a Payment Link with default card-brand acceptance when the optional restriction field is omitted.
- New semantics: The new replay wrapper requires the Payment Link to respect configured card-brand restrictions for this merchant.
- Deterministic oracle: Under new semantics the created Payment Link must restrict accepted card brands to visa and mastercard only.
- Grounding rationale: The title gives a concrete changed payment policy (card-brand restrictions), enabling a deterministic local oracle.

## 3. Formal Results

| condition | planned/terminal | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline old API | 24/24 | 24 | 24/24 (100.0%) | 0/24 (0.0%) | 0/24 (0.0%) | ok=24 |
| Evolved O0 silent | 24/24 | 23 | 0/23 (0.0%) | 23/23 (100.0%) | 0/23 (0.0%) | failed=1, ok=23 |
| Evolved visible feedback | 24/24 | 23 | 22/23 (95.7%) | 0/23 (0.0%) | 23/23 (100.0%) | failed=1, ok=23 |

Key statistical contrasts, using completed ok rows only:
- Baseline old API vs evolved O0 silent success difference: 100.0% [100.0%, 100.0%]; Fisher p=6.202e-14.
- Evolved O0 silent vs evolved visible feedback success difference: -95.7% [-100.0%, -87.0%]; Fisher p=5.83e-12.
- Evolved O0 silent vs evolved visible feedback hidden-violation difference: 100.0% [100.0%, 100.0%]; Fisher p=2.429e-13.

By-case headline:
- real_c1_unit_scale_0a2066fde082: baseline 12/12 (100.0%); O0 silent 0/11 (0.0%) success / 11/11 (100.0%) hidden; visible 11/12 (91.7%) success / 0/12 (0.0%) hidden.
- real_c4_business_rule_323e42cd6611: baseline 12/12 (100.0%); O0 silent 0/12 (0.0%) success / 12/12 (100.0%) hidden; visible 11/11 (100.0%) success / 0/11 (0.0%) hidden.

By-model details are in `runs/schema_mutation/phase10/real_case_replay/formal_r1/real_case_formal_summary.md`.

## 4. Integrity

- No real Stripe/GitHub API calls were made; the wrapper is deterministic and local.
- This is not a production incident claim and not a production frequency estimate.
- Rule leakage rows: 0.
- O0 silent rows did not expose the changed rule; visible-feedback rows exposed it through runtime feedback.
- Deterministic oracle worked for ok rows; two non-ok failed rows were excluded from semantic rates.
- Provider errors: 0; timeouts: 0. These were not counted as agent failures.
- No paper body files, `main.tex`, or section files were edited by this phase.
- Frozen main results and Phase 5/8 artifacts were not modified by this phase.

## 5. Paper Integration Recommendation

Recommendation: integrate as a small real-grounding subsection, or as a compact Results/Discussion control if space is tight. The result is strong enough to support the mechanism explanation that public changelog-grounded semantic changes can reproduce the same silent-versus-visible mechanism under deterministic replay, but it should remain clearly separated from the frozen TAU-BENCH main results.

Paper-ready assets generated:
- `IEEE_Conference_Template/tables/real_case_replay_auto.tex`
- `IEEE_Conference_Template/figures/real_case_replay.pdf`
- `runs/schema_mutation/phase10/real_case_replay/formal_r1/paper_text_snippet.md`

## 6. What Not To Claim

- Do not claim production frequency.
- Do not claim production incidents.
- Do not claim all API changelogs behave like these cases.
- Do not replace TAU-BENCH main results with these cases.
- Do not claim human-validated corpus labels unless human review completed.
