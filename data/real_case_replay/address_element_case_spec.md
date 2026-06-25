# Stripe Address Element State-Format Replay Case

- Case id: `stripe_address_element_state_format_20260325`
- Provider: Stripe
- Source: https://docs.stripe.com/changelog/dahlia/2026-03-25/address-element-getvalue-and-change-event-formatting
- Source title: Changes the Address Element state field to default to Latin-formatted characters
- Source date: 2026-03-25
- Classification: C2_locale_formatting_and_C3_default_behavior
- Supplemental status: public-changelog replay case; this does not modify the frozen 151-entry corpus count.

## Before Semantics

The Address Element getValue() method and billing/shipping address change event returned the state value in a format matching the user's browser locale.

## After Semantics

The state property defaults to Latin-formatted characters. To retrieve the localized value, integrations must explicitly call getValue({format: 'localized'}). The address change event returns a Latin-formatted state.

## Silent-Semantics Fit

The same call/event still succeeds and returns a string-valued state field; the change is in default output representation rather than schema validity or call acceptability.

An agent replaying an existing integration can observe a normal state string without any diagnostic saying that the default representation changed.

## Deterministic Oracle

The downstream task requires the localized state value '東京都'. Success requires the final stored/reported state to use that value; using the Latin value 'Tokyo' under evolved silent semantics is a hidden violation.

## Boundary

This is a deterministic local wrapper replay. It is not a live Stripe experiment, not a production incident, and not a production-frequency estimate.
