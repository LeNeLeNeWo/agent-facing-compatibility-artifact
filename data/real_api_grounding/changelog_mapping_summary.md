# Changelog Grounding for Mutation Realism

This is a lightweight plausibility grounding artifact. It does not estimate production frequencies and does not claim that any listed API change caused an agent failure.

## Rubric
- A. Surface / representation: naming changes, date/time format changes, field representation changes, documentation wording changes, description edits.
- B. Schema-contract: required field added/removed, parameter type changed, enum value added/removed/renamed, response field added/removed/renamed, endpoint signature changed.
- C. Semantic-contract: unit/scale behavior changed, currency/locale behavior changed, default behavior changed, eligibility/business policy changed, refund/cancel/payment/fare/access rule changed, behavior changed while schema may remain stable.
- D. Protocol / operational: pagination behavior changed, rate limit changed, authentication/permission changed, error format changed, timeout/retry behavior changed, operational quota / availability behavior changed.

## Summary
- total changelog items: 22
- count by source: {'Anthropic': 2, 'GitHub': 1, 'Google Calendar': 2, 'Microsoft Graph': 1, 'OpenAI': 1, 'OpenAPI': 1, 'PayPal': 3, 'Shopify': 3, 'Slack': 2, 'Square': 4, 'Twilio SendGrid': 1, 'Twilio TaskRouter': 1}
- count by taxonomy class: {'A': 2, 'B': 5, 'C': 6, 'D': 9}
- count by mutation type: {'A2_format_change': 1, 'A3_documentation_semantics_change': 1, 'B3_enum_value_change': 1, 'B4_output_shape_change': 4, 'C3_default_behavior_drift': 3, 'C4_business_rule_drift': 3, 'D2_permission_change': 2, 'D3_pagination_change': 2, 'D4_rate_limit_change': 3, 'D5_error_validation_change': 1, 'D6_retry_timeout_change': 1}
- schema-visible: 5
- schema-invisible: 17
- semantic-change: 9
- likely agent relevant: 22
- confidence distribution: {'high': 11, 'low': 2, 'medium': 9}
- needs manual review: 11

## Examples Per Class
### A. Surface / representation
- PayPal: BILLTOZIP field correction (A2_format_change, medium)
- OpenAPI: Clarify nullable semantics (A3_documentation_semantics_change, low)
### B. Schema-contract
- Shopify: Deprecated multiLocation field removed (B4_output_shape_change, high)
- Shopify: StringConnection includes nodes field (B4_output_shape_change, high)
- Square: Customer cards field retired (B4_output_shape_change, high)
- Google Calendar: Events from Gmail use fromGmail event type (B3_enum_value_change, medium)
### C. Semantic-contract
- OpenAI: GPT-5.5 API release notes (C3_default_behavior_drift, medium)
- Anthropic: Default top_p changed (C3_default_behavior_drift, low)
- Shopify: Cart tax and duties calculation moved to checkout (C3_default_behavior_drift, medium)
- Square: App Marketplace seller eligibility requirement (C4_business_rule_drift, high)
### D. Protocol / operational
- Anthropic: Sampling parameter validation for Opus 4.8 (D5_error_validation_change, medium)
- Twilio SendGrid: Email Activity API rate limit change (D4_rate_limit_change, high)
- Twilio TaskRouter: TaskRouter endpoint rate limit correction (D4_rate_limit_change, high)
- Microsoft Graph: Lesser privileged permissions for user APIs (D2_permission_change, medium)

## Manual Review Queue
- openai_2026_04_24_reasoning_default
- anthropic_2026_05_28_sampling_error
- anthropic_top_p_default
- microsoft_graph_lesser_permissions
- shopify_2025_01_cart_tax_checkout
- square_2025_01_23_node_autopagination
- google_calendar_2024_05_30_fromgmail
- paypal_2023_01_15_billtozip_format
- paypal_2023_01_15_transactionid_response
- paypal_ach_new_accounts
- openapi_nullable_clarification
