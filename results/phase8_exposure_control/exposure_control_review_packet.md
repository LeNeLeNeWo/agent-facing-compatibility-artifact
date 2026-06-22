# Phase 8A Exposure-Control Review Packet

## Formal Integrity
- planned_cells: 363
- matched_cells: 363
- completed_formal_latest_rows: 363
- ok: 363
- provider_error: 0
- timeout: 0
- failed: 0
- smoke_excluded: True
- retry_duplicates_handled: True
- no_wyz_gpt_grok: True
- target_unused_tool_called_count: 5
- target_unused_tool_called_rate: 0.013774104683195593

## Overall Comparison
- Exposed O0: N=363, success=182 (50.1%), hidden_violation=161 (44.4%), visible_error=0 (0.0%), target_reached=161 (44.4%)
- Unused-tool O0 control: N=363, success=280 (77.1%), hidden_violation=5 (1.4%), visible_error=0 (0.0%), target_reached=5 (1.4%)
- Success-rate difference unused - exposed: 0.270, bootstrap 95% CI [0.201, 0.336]
- Hidden-violation difference unused - exposed: -0.430, bootstrap 95% CI [-0.479, -0.377]
- Fisher exact p=4.382571788116426e-14, odds_ratio=0.29806629834254145

## By Domain
- retail: exposed success 41.0% (N=105), unused success 74.3% (N=105), exposed hidden 53.3%, unused hidden 1.0%
- airline: exposed success 53.9% (N=258), unused success 78.3% (N=258), exposed hidden 40.7%, unused hidden 1.6%

## By Model
- dashscope/glm-5.1: exposed success 50.9% (N=108), unused success 80.6% (N=108), exposed hidden 46.3%, unused hidden 0.0%
- dashscope/kimi-k2.6: exposed success 53.5% (N=99), unused success 76.8% (N=99), exposed hidden 39.4%, unused hidden 2.0%
- dashscope/qwen-max: exposed success 30.2% (N=53), unused success 50.9% (N=53), exposed hidden 54.7%, unused hidden 5.7%
- deepseek/deepseek-v4-flash: exposed success 56.3% (N=103), unused success 87.4% (N=103), exposed hidden 41.7%, unused hidden 0.0%

## Interpretation
- Does unused-tool C4b control remain high-success / low-violation compared with exposed O0? Yes.
- Does this strengthen Finding 2? Yes, across both domains and all four frozen formal models.
- Does this rule out wrapper-global destabilization? It strongly supports that interpretation: the same class of silent C4 drift is low-violation when placed on non-executed tools/rules.
