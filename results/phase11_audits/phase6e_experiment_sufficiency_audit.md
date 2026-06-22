# Phase 6E Experiment Sufficiency and Reviewer Defense Audit

Date: 2026-06-16.

Scope: offline reviewer-style audit only. No API calls, no Phase 5 shard execution, no baseline/observability/mutation reruns, no Gate/Predictor reruns, no B/D mutation execution, and no GPT/WYZ partial rows were read or merged.

## 1. Main Claims and Supporting Evidence

### Claim A: Schema/client-compatible changes can be agent-facing breaking.

Evidence:

- Strict schema/client-compatible region: `44/130 = 33.8%` agent-breaking.
- Relaxed schema/client-compatible Y+P region: `49/156 = 31.4%`.
- C4b airline case study shows unchanged schema and call signature, no visible policy error, hidden business-rule violation, and reward drop from `1.0` to `0.0`.
- Static checker explicitly misses C1-C4 schema-invisible semantic drift because it checks machine-readable schema/call-signature changes and ignores natural-language/vendor semantic fields.

Reviewer-safe framing:

- Treat `33.8%` as a controlled-suite rate, not a production base rate.
- The central claim is existence/mechanism: schema/client compatibility can be insufficient for agent clients.

### Claim B: Observability improves recoverability over silent semantic drift.

Evidence:

- Retail formal cells: `525`.
- Airline formal cells: `1290`.
- Combined formal cells: `1815`.
- Combined O0-O4 success: `0.501 / 0.843 / 0.846 / 0.851 / 0.848`.
- Combined O4-O0 uplift: `+0.347`, bootstrap CI `[0.289, 0.405]`.
- Retail O4-O0: `+0.448`, CI `[0.333, 0.562]`.
- Airline O4-O0: `+0.306`, CI `[0.233, 0.380]`.
- Non-strict monotonicity among O1-O4 is acknowledged in the packet, captions, Results, Discussion, and Threats.

Reviewer-safe framing:

- Claim that observability provides a recovery channel over silence.
- Do not claim a universal strict ranking of generic errors, policy errors, structured errors, and migration notes.

### Claim C: Execution exposure matters.

Evidence:

- Exposed airline C4b: DeepSeek `0/17` success with `17/17` oracle and hidden violations.
- Airline unused-tool negative control: `5/6` success, `0/6` oracle violations, `0/6` visible errors, `0/6` hidden violations.
- Airline audit: exposed target tool is called in all audited exposed C4b runs; no timeout or max-step cutoff explains the failures.
- Exposure-aware protocol filters to baseline-successful cells and targets mutations by used, unused, and intent-aligned exposure conditions.
- Predictor results show exposure alone is not enough, but exposure remains a necessary ingredient when combined with semantic class and observability.

Reviewer-safe framing:

- Exposure should be framed as a mechanism and test-design principle, not as a final standalone classifier.

### Claim D: Schema-only checking is insufficient; AFC-Gate is useful as a screening prototype.

Evidence:

- SchemaCheckerOnly recall: `0.000`.
- AFCGate silent-regression recall: `0.996`.
- AFCGate agent-breakage recall: `0.523`.
- AFCGate precision: `0.557`.
- AFCGate FPR: `0.134`.
- AFCGate tests run: `10` of `1987` replay/cache cells.
- AFCGate relative cost: `0.005`.
- The paper already frames AFC-Gate as a screening prototype, not deployment-ready certification.

Reviewer-safe framing:

- AFC-Gate is promising for low-cost screening of silent regressions.
- It is not a complete production compatibility gate.

## 2. Reviewer Attack Surface

### "C4b is a worst-case tautology"

- Risk level: high.
- Current defense: C4b is explicitly framed as a worst-case boundary case; the paper includes C4a counterpart, unused-tool negative control, airline replication, five-level observability gradient, audit fields ruling out timeout/max-step/unused-tool confounds, and changelog grounding for semantic drift plausibility.
- Need new experiment? no.
- Recommended action: keep the claim mechanistic. Say C4b tests the failure mode where semantic change is execution-exposed and unobservable; do not imply C4b frequency in production.

### "Only C-class data; where are B/D mutations?"

- Risk level: medium-high.
- Current defense: taxonomy includes A/B/C/D, static checker boundary table includes B/D, changelog mapping grounds all classes, and Threats says B/D paired data remains future work.
- Need new experiment? no for the main observability claim; optional for taxonomy breadth.
- Recommended action: do not let RQ2 look like a full taxonomy prevalence result. Frame B/D as future diversity for predictor/gate validation.

### "Predictor is C-class heavy"

- Risk level: medium.
- Current defense: Threats and RQ5 already say the predictor dataset remains C-class heavy; final dataset now has hard negatives and no longer simply separates exposed C4b failures from unused controls.
- Need new experiment? no.
- Recommended action: keep predictor claims explanatory. Avoid deployment-readiness language.

### "Two TAU-BENCH domains only"

- Risk level: medium.
- Current defense: retail and airline are both formal O0-O4 gradients; airline reduces retail-specific wrapper concerns.
- Need new experiment? no.
- Recommended action: keep as external-validity threat and future work. Do not start a third domain now.

### "Models are mostly CN providers"

- Risk level: medium.
- Current defense: four formal models across DeepSeek and DashScope; model-selection threat is explicit.
- Need new experiment? no.
- Recommended action: if GPT-5.5 finishes cleanly, use it only as appendix/model-extension robustness. Do not block the main paper on it.

### "GPT/Grok incomplete"

- Risk level: low-medium.
- Current defense: artifact rules exclude GPT/WYZ/Grok partial rows unless complete and explicitly marked formal; Grok provider-side 403 anti-bot is documented as provider instability.
- Need new experiment? no.
- Recommended action: keep partial rows out of main tables. Use the GPT decision tree below when it finishes.

### "Exact prompts/system messages missing"

- Risk level: high.
- Current defense: manifest records model/user-simulator/runtime metadata and points to `code/schema_mutation/runner.py`, but exact standalone prompts/system messages are not archived.
- Need new experiment? no.
- Recommended action: must archive exact agent prompt, user-simulator prompt, and system messages before submission-quality artifact release.

### "RQ2 table still weak / n/a paired denominators"

- Risk level: medium-high.
- Current defense: table now labels retail rows as aggregate split-day6 evidence and paired denominators as `n/a`; main evidence moved to RQ3 gradient and airline paired audit.
- Need new experiment? no, unless the paper insists on RQ2 as a full taxonomy result.
- Recommended action: treat RQ2 as a taxonomy/exposure evidence slice. Consider moving or compressing the weak aggregate rows during page compression.

### "Page count too long"

- Risk level: high for formatting, low for evidence.
- Current defense: Phase 6C reports 17 pages and defers layout compression.
- Need new experiment? no.
- Recommended action: compress after artifact/prompt/TODO cleanup. Candidate moves are listed in Section 7.

### "AFCGate evaluated with synthetic/replay evidence, not production deployment"

- Risk level: medium.
- Current defense: RQ6 says AFC-Gate uses cached replay artifacts and deterministic semantic-oracle evidence and is a screening prototype.
- Need new experiment? no.
- Recommended action: keep "prototype/screening" language. Avoid CI/CD deployment claims beyond design implication.

### "33.8% may be mistaken as real-world base rate"

- Risk level: high.
- Current defense: Threats says controlled API-evolution mechanism evidence, not production frequency; changelog grounding is plausibility, not frequency.
- Need new experiment? no.
- Recommended action: add or preserve a near-table note that `44/130` is a controlled suite rate over selected mutations, not an estimate of production API-change prevalence.

## 3. Must-Fix Before Submission

- Archive exact agent prompt, user-simulator prompt, and any system messages.
- Keep GPT/Grok/WYZ partial rows out unless complete formal review packets exist.
- Keep RQ2 from appearing to carry the core empirical burden while paired denominators are `n/a`.
- Ensure the `33.8%` strict compatible breakage rate is explicitly described as a controlled-suite rate, not a real-world base rate.
- Keep artifact manifest links/paths visible and consistent.
- Update stale wording that says the exact TAU-BENCH commit remains to be recorded; Phase 6D already recorded `tau_bench==0.1.0` at commit `59a200c6d575d595120f1cb70fea53cef0632f6b`.
- Remove or resolve visible `TODO-HIGH` placeholders before any submission-quality PDF, especially prompt/archive TODOs and author/affiliation placeholders as appropriate for the submission mode.

## 4. Optional Experiments

### GPT-5.5 Formal Airline Extension

Decision:

- Optional, not a blocker.
- If complete and clean, include as appendix/model-extension evidence.
- If partial or provider-error contaminated, exclude from formal tables and record provider limitation.

### B/D Class Mutation Supplement

Decision:

- Optional, not a blocker for the current main claim.
- It would improve taxonomy and predictor diversity.
- It is not required because the main experiment is now a strong semantic-observability study, not a full A/B/C/D prevalence study.

### Third Domain

Decision:

- Defer.
- It is expensive, could dilute the story, and is better framed as external-validity future work.

### More Formal Tests

Decision:

- Existing bootstrap CIs are enough for the main observability claim.
- Additional exact/permutation or clustered bootstrap robustness checks would be useful if cheap and offline, but they are not a blocker.

## 5. What To Do With GPT-5.5 When It Finishes

### Case A: GPT baseline plus observability complete, clean, and no provider errors.

- Generate a GPT review packet.
- Do not overwrite the existing `1815` formal main-result denominator.
- Add an appendix table or one robustness sentence.
- Optionally rerun a combined summary as supplementary only, clearly separated from the main 1815-cell result.

### Case B: GPT complete but non-monotone or weaker.

- Include as appendix if clean.
- Interpret as model heterogeneity.
- Do not weaken or rewrite the main observability claim unless GPT reverses the O0 vs observable gap entirely.

### Case C: GPT partial or provider errors.

- Exclude from formal tables.
- Record provider-side instability.
- Make no main-paper change.

## 6. Recommendation on B/D Data

Recommendation: defer; small pilot only if extra time remains after prompt archiving, TODO cleanup, and page-compression planning.

Rationale:

- The current main claim is semantic observability under schema/client-compatible drift.
- B/D would improve taxonomy breadth and predictor diversity, but would not be the most direct support for the current ICSE/FSE/ASE story.
- Starting B/D now risks reopening experimental scope and schedule without fixing the biggest reviewer risks.

Minimal contingency pilot, not to execute in Phase 6E:

- Models: `deepseek/deepseek-v4-flash` and `dashscope/qwen-max`.
- Environment: retail only, using already established task machinery.
- Tasks: 5 baseline-good tasks if available after baseline filtering.
- Seeds: `0,1`.
- Mutation classes: `B1_type_change`, `B3_enum_change`, `D2_permission_change`, `D4_rate_limit_change`.
- Protocols: `used_tool` and `unused_tool`.
- Expected mutation cells before baseline filtering: `2 models * 5 tasks * 2 seeds * 4 mutations * 2 protocols = 160`.
- Table supported: a small appendix supplement for taxonomy breadth and static-checker/gate diversity, not a replacement for the main observability gradient.

## 7. Recommendation on Page Compression

Do not compress before the non-layout blockers are resolved. Before page compression:

- Archive exact prompts/system messages.
- Decide the final status of GPT/WYZ/Grok rows.
- Make RQ2 clearly secondary or move weak aggregate rows to appendix.
- Ensure the controlled-suite nature of `33.8%` is unmistakable.
- Resolve visible high-priority TODOs.

Compression candidates:

- Move the old C4a/C4b binary table/figure to appendix or summarize it in one paragraph.
- Move the old predictor pilot table to appendix; keep only the new predictor generalization table in the main text.
- Compress the two case-study tables into one smaller table or move the trajectory excerpt to appendix.
- Merge Tables VI/VII if space pressure is severe, or keep Table VI main and put per-model Table VII in appendix.
- Move artifact reproduction notes to appendix/artifact manifest.
- Shorten Related Work by merging benchmark/tool-misuse/observability contrasts.

## 8. Final Go/No-Go Assessment

Main experiment sufficiency: sufficient.

Biggest remaining blocker: exact prompt/system-message archival and visible high-priority TODO cleanup, not additional experiments.

Recommended next action: archive prompts/system messages, do a tiny wording pass for controlled-suite/base-rate/RQ2 framing, then start page compression.

Submission-quality blocker:

- No new experiment blocks a submission-quality draft.
- A submission-quality artifact/PDF is still blocked if exact prompts/system messages remain unarchived or visible TODO-HIGH placeholders remain in the compiled paper.
