# Model Provenance Summary

Generated for Phase 7G from existing offline artifacts only. No API calls, live shards, predictor reruns, gate reruns, or raw artifact modifications were performed.

## Sources

- `ARTIFACT_MANIFEST.md`
- `runs/schema_mutation/ARTIFACT_MANIFEST_PHASE5.md`
- `runs/schema_mutation/phase5/combined_observability_review_packet.json`
- `runs/schema_mutation/phase5/phase5_summary.json`
- Existing Phase 5 status JSONL metadata under `runs/schema_mutation/phase5/status/`

## Formal Main Agent Models

| model string exactly as used | provider | role | included in frozen main table? | endpoint family | artifact run timestamps | snapshot/version ID |
|---|---|---|---|---|---|---|
| `deepseek/deepseek-v4-flash` | `deepseek` | formal agent | yes | DeepSeek-compatible provider endpoint configured outside artifact by environment | `2026-06-14T10:12:30` to `2026-06-16T10:52:18` | provider snapshot identifier not available in artifact; exact model string and run metadata are recorded |
| `dashscope/qwen-max` | `dashscope` | formal agent | yes | DashScope provider endpoint configured outside artifact by environment | `2026-06-14T02:19:41` to `2026-06-16T02:33:46` | provider snapshot identifier not available in artifact; exact model string and run metadata are recorded |
| `dashscope/kimi-k2.6` | `dashscope` | formal agent | yes | DashScope provider endpoint configured outside artifact by environment | `2026-06-14T00:48:06` to `2026-06-15T23:35:44` | provider snapshot identifier not available in artifact; exact model string and run metadata are recorded |
| `dashscope/glm-5.1` | `dashscope` | formal agent | yes | DashScope provider endpoint configured outside artifact by environment | `2026-06-13T21:43:17` to `2026-06-15T15:34:27` | provider snapshot identifier not available in artifact; exact model string and run metadata are recorded |

## User Simulator

| model string exactly as used | provider | role | included in frozen main table? | endpoint family | artifact run timestamps | snapshot/version ID |
|---|---|---|---|---|---|---|
| `dashscope/qwen-flash` | `dashscope` | user simulator | yes, as simulator for formal main runs | DashScope provider endpoint configured outside artifact by environment | recorded in formal run metadata where available | provider snapshot identifier not available in artifact; exact model string and run metadata are recorded |

## Supplementary Extension

| model string exactly as used | provider | role | included in frozen main table? | endpoint family | artifact run timestamps | snapshot/version ID |
|---|---|---|---|---|---|---|
| `wyzlab/gpt-5.5` | `wyzlab` | supplementary extension agent | no | WYZLab-compatible provider endpoint configured outside artifact by environment | `2026-06-16T15:02:48` to `2026-06-17T03:38:11` | provider snapshot identifier not available in artifact; exact model string and run metadata are recorded |

## Notes

- API keys are read from environment variables and are not stored or printed in the artifact package.
- Provider base URLs are configured outside the paper text and should not appear in the manuscript.
- Supplemental provider extensions are kept outside the frozen 1,815-cell main analysis.
