# API Evolution Annotation Sheet

This sheet converts the Phase 10A automatically labeled public-changelog corpus into a human-review queue. The automatic labels are candidates only.

- Entries: 151
- Providers: 9 (Anthropic, GitHub, Google Cloud, OpenAI, Shopify, Slack, Square, Stripe, Twilio)
- C-class candidates: 61
- Taxonomy distribution: A=11, B=22, C=61, D=18, mixed=39

## Fields

- `auto_*` columns are machine-generated labels from Phase 10A.
- `human_*` columns are intentionally blank for reviewer annotation.
- `accept_for_paper_example` should be marked only after source evidence and semantic interpretation are manually checked.

## Preview

| entry_id | provider | date | auto_taxonomy_class | auto_c_subclass | auto_schema_visible | url |
| --- | --- | --- | --- | --- | --- | --- |
| anthropic_00ba2e322aee | Anthropic | 2026-04-01 | C | none | false | https://docs.anthropic.com/docs/en/managed-agents/memory |
| anthropic_709b7ed01d6b | Anthropic | 2026-04-01 | mixed | none | true | https://docs.anthropic.com/docs/en/managed-agents/multi-agent |
| anthropic_1efd34b3c1c5 | Anthropic | unknown | mixed | C3_default_behavior | true | https://docs.anthropic.com/en/release-notes/api |
| anthropic_b0f447baa1f4 | Anthropic | unknown | mixed | C3_default_behavior | true | https://docs.anthropic.com/docs/en/managed-agents/vaults |
| anthropic_be753b1a8ca7 | Anthropic | unknown | A | none | unknown | https://docs.anthropic.com/docs/en/build-with-claude/extended-thinking#controlling-thinking-display |
| anthropic_bdcafb9317dd | Anthropic | unknown | C | none | false | https://docs.anthropic.com/docs/en/agents-and-tools/mcp-tunnels/overview |
| anthropic_56d8a804f4e1 | Anthropic | unknown | C | C4_business_rule | false | https://docs.anthropic.com/docs/en/test-and-evaluate/strengthen-guardrails/handle-streaming-refusals |
| anthropic_8cd8a700d1f8 | Anthropic | unknown | C | C3_default_behavior | false | https://docs.anthropic.com/docs/en/managed-agents/self-hosted-sandboxes |
| anthropic_99c862f23cdf | Anthropic | unknown | D | none | unknown | https://docs.anthropic.com/docs/en/managed-agents/webhooks |
| anthropic_7575e78f6524 | Anthropic | unknown | mixed | C4_business_rule | true | https://docs.anthropic.com/docs/en/agents-and-tools/tool-use/code-execution-tool |
| anthropic_56c5b3ffa9bc | Anthropic | unknown | C | none | false | https://docs.anthropic.com/docs/en/agents-and-tools/tool-use/web-search-tool |
| anthropic_1176ccc97271 | Anthropic | unknown | C | none | false | https://anthropic.com/glasswing |
| anthropic_4b3f93bb5a8f | Anthropic | unknown | D | none | unknown | https://docs.anthropic.com/docs/en/manage-claude/rate-limits-api |
| anthropic_9eaa79c092d8 | Anthropic | unknown | mixed | none | unknown | https://docs.anthropic.com/docs/en/about-claude/models/overview#latest-models-comparison |
| anthropic_5eca0bc8da5d | Anthropic | unknown | mixed | C3_default_behavior | true | https://docs.anthropic.com/docs/en/managed-agents/webhooks |
| anthropic_2491922fc0f3 | Anthropic | unknown | C | C3_default_behavior | false | https://docs.anthropic.com/en/release-notes/api |
| github_40027443ef32 | GitHub | Fri, 19 Jun 2026 16:23:29 +0000 | C | C4_business_rule | false | https://github.blog/changelog/2026-06-19-ai-credits-consumed-per-user-now-in-the-copilot-usage-metrics-api |
| github_d4a036546a5f | GitHub | Thu, 18 Jun 2026 14:06:18 +0000 | C | none | false | https://github.blog/changelog/2026-06-18-control-who-and-what-triggers-github-actions-workflows |
| github_dc8b0356afef | GitHub | Thu, 18 Jun 2026 14:06:55 +0000 | C | C3_default_behavior | false | https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout |
| github_c1d0f8516586 | GitHub | Thu, 18 Jun 2026 15:32:44 +0000 | C | none | false | https://github.blog/changelog/2026-06-18-actions-build-custom-images-from-custom-images |
