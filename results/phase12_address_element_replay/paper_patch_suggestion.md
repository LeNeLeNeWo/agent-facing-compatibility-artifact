# Phase 12J Paper Patch Suggestion

Do not apply this automatically. This is a suggested patch/snippet for a later paper-integration phase.

## 1. Section II.C Concrete Example Paragraph

Suggested text:

> A cleaner silent-semantics example comes from Stripe's 2026-03-25 Address Element changelog. The same `getValue()` call and address-change event still return a string-valued `state` field, but the default representation changed from the user's browser-localized format to Latin-formatted characters. A workflow that needs the localized state must explicitly request `getValue({format: 'localized'})`. In the O0 setting, the runtime call can therefore succeed without a changed-rule diagnostic while downstream state storage silently changes representation; in the visible condition, the agent is told to request the localized format.

## 2. Fig. 1 Inset Text

- Before: browser-locale state
- After: Latin state by default
- Same call/event succeeds
- No natural error channel

## 3. Finding 4 Update

Recommended integration: supplement the existing real-changelog-grounded replay cases with Address Element, or replace the weaker C1 validation replay if space is tight. Update any table denominators only in the later integration phase.

## 4. Auto Table

- Generated table: `IEEE_Conference_Template/tables/address_element_replay_auto.tex`

## 5. Current Replay Numbers

- Baseline success: 12/12 (100.0%)
- O0 silent success / hidden violation: 6/12 (50.0%) / 6/12 (50.0%)
- Visible success / hidden violation: 12/12 (100.0%) / 0/12 (0.0%)
