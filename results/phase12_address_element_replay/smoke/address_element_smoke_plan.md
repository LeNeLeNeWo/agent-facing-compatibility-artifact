# Phase 12J Address Element Replay Plan

- Case: `stripe_address_element_state_format_20260325`
- Planned cells: 6
- Conditions: baseline_old_api, evolved_o0_silent, evolved_visible_feedback
- This plan uses deterministic local wrappers and does not call Stripe.

| cell | condition | model | seed | expected behavior |
| --- | --- | --- | ---: | --- |
| phase12j_stripe_address_element_state_format_20260325_baseline_old_api_deepseek_deepseek-v4-flash_seed0 | baseline_old_api | deepseek/deepseek-v4-flash | 0 | Old default returns the localized state; baseline should succeed with the schema-compatible default call. |
| phase12j_stripe_address_element_state_format_20260325_evolved_o0_silent_deepseek_deepseek-v4-flash_seed0 | evolved_o0_silent | deepseek/deepseek-v4-flash | 0 | Evolved default returns a Latin state without diagnostic; old default-call behavior should hidden-violate. |
| phase12j_stripe_address_element_state_format_20260325_evolved_visible_feedback_deepseek_deepseek-v4-flash_seed0 | evolved_visible_feedback | deepseek/deepseek-v4-flash | 0 | Changed default is visible through feedback/tool context; agent can request format='localized' and recover. |
| phase12j_stripe_address_element_state_format_20260325_baseline_old_api_dashscope_qwen-max_seed0 | baseline_old_api | dashscope/qwen-max | 0 | Old default returns the localized state; baseline should succeed with the schema-compatible default call. |
| phase12j_stripe_address_element_state_format_20260325_evolved_o0_silent_dashscope_qwen-max_seed0 | evolved_o0_silent | dashscope/qwen-max | 0 | Evolved default returns a Latin state without diagnostic; old default-call behavior should hidden-violate. |
| phase12j_stripe_address_element_state_format_20260325_evolved_visible_feedback_dashscope_qwen-max_seed0 | evolved_visible_feedback | dashscope/qwen-max | 0 | Changed default is visible through feedback/tool context; agent can request format='localized' and recover. |
