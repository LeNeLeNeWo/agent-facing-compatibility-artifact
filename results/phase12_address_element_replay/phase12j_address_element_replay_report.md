# Phase 12J Address Element Replay Report

## 1. Executive Summary

- Case spec created: True.
- Smoke ran: True.
- Formal ran: True.
- Active analyzed cells: 36 / planned 36.
- Status counts: ok=36
- Headline replay pattern: baseline success 12/12, O0 silent hidden violation 6/12, visible success 12/12.
- Supports adding as formal replay: True (Baseline succeeds, silent evolved condition hidden-violates, and visible condition recovers.)

## 2. Case Spec

- Case id: `stripe_address_element_state_format_20260325`
- Provider: Stripe.
- Source URL: https://docs.stripe.com/changelog/dahlia/2026-03-25/address-element-getvalue-and-change-event-formatting
- Classification: C2 locale-formatting semantic drift + C3 default-behavior drift.
- This is supplemental and does not change the frozen 151-entry corpus count.

## 3. Smoke Results

- Planned/run: 6/6.
- Status counts: ok=6
- Baseline success: 2/2.
- O0 hidden violation: 2/2.
- Visible success: 2/2.
- Note: the smoke directory retains an earlier superseded 6-row attempt in raw/status logs. That attempt exposed an internal representation marker in the agent-visible O0 tool response. The runner was corrected so O0 returns only the normal `state` string; the smoke summary above uses the latest corrected terminal row per cell, and the formal run below was executed only after this correction.

## 4. Formal Results

- Planned/run: 36/36.
- Status counts: ok=36

| condition | ok N | success | hidden violation | visible rule exposed |
| --- | ---: | ---: | ---: | ---: |
| baseline_old_api | 12 | 12/12 (100.0%) | 0/12 (0.0%) | 0/12 (0.0%) |
| evolved_o0_silent | 12 | 6/12 (50.0%) | 6/12 (50.0%) | 0/12 (0.0%) |
| evolved_visible_feedback | 12 | 12/12 (100.0%) | 0/12 (0.0%) | 12/12 (100.0%) |

## 5. Suitability

- Fig. 1 inset suitability: strong as a concrete silent-semantics mechanism example because the same call/event succeeds, the same string field remains present, and there is no natural runtime error channel. The formal replay should be described carefully: O0 silent produced hidden violations in 6/12 cells, while some models recovered by explicitly requesting the localized format.
- Finding 4 recommendation: supplement existing replays, or replace the weaker validation-semantics replay if the paper needs a cleaner headline example. Do not claim that all agents fail under O0 for this case.

## 6. Integrity

- Real Stripe API call attempted: False.
- No Phase 5/8/10C rerun was performed by this stage.
- Frozen 1815-cell main results were not modified by this stage.
- Rule leakage rows: 0.
- Fake rows: 0.
- Provider_error/timeout/failed rows are not counted as agent failures.
- This is not a production incident and not a production-frequency estimate.

## 7. Outputs

- Case spec JSON: `runs/schema_mutation/phase12/address_element_replay/address_element_case_spec.json`
- Case spec MD: `runs/schema_mutation/phase12/address_element_replay/address_element_case_spec.md`
- Supplemental changelog case: `runs/schema_mutation/phase12/address_element_replay/supplemental_public_changelog_case.jsonl`
- Smoke summary: `runs/schema_mutation/phase12/address_element_replay/smoke/address_element_smoke_summary.md`
- Formal summary: `runs/schema_mutation/phase12/address_element_replay/formal/address_element_formal_summary.md`
- Paper patch suggestion: `runs/schema_mutation/phase12/address_element_replay/paper_patch_suggestion.md`
- Auto table: `IEEE_Conference_Template/tables/address_element_replay_auto.tex`
- WSL paper table copy: `<HOME>/ICSE 2027/schema_mutation_paper_package_20260612_194214/IEEE_Conference_Template/tables/address_element_replay_auto.tex`

## 8. Recommended Next Action

Integrate as a small Finding 4/Fig. 1 support case in a separate paper-editing phase, with explicit wording that it is a real-changelog-grounded deterministic replay.
