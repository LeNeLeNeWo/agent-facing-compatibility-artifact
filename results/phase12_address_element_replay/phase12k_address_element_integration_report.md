# Phase 12K Address Element Integration Report

## 1. Phase 12J Formal Status

- Phase 12J formal succeeded: yes.
- Formal cells: 36 planned / 36 completed.
- Status counts: ok=36.
- Provider errors/timeouts/failed rows: 0.
- Rule leakage rows: 0.
- Real Stripe API calls: 0.
- Deterministic oracle worked: yes.

## 2. Integration Decision

- Address Element integrated into Finding 4: yes.
- Reason: the formal replay satisfies the integration criteria: baseline old API has high success, evolved O0 silent shows a success drop and hidden violations, evolved visible feedback recovers, and integrity checks are clean.
- Caveat retained in interpretation: O0 silent is not an all-agent failure for this case; it has 6/12 success and 6/12 hidden violation because some models explicitly request the localized format without visible rule feedback.

## 3. Real Replay Totals

Old real replay totals:

| Condition | Success | Hidden violation |
| --- | ---: | ---: |
| Baseline old API | 24/24 | 0/24 |
| Evolved O0 silent | 0/23 | 23/23 |
| Evolved visible | 22/23 | 0/23 |

Address Element formal contribution:

| Condition | Success | Hidden violation |
| --- | ---: | ---: |
| Baseline old API | 12/12 | 0/12 |
| Evolved O0 silent | 6/12 | 6/12 |
| Evolved visible | 12/12 | 0/12 |

Updated Table II / grounding-control totals:

| Condition | Success | Hidden violation |
| --- | ---: | ---: |
| Baseline old API | 36/36 | 0/36 |
| Evolved O0 silent | 6/35 | 29/35 |
| Evolved visible | 34/35 | 0/35 |

- Updated real replay OK/terminal note: 106 OK rows from 108 terminal rows.
- Existing 288-cell non-obviousness control note remains: 286 OK rows.

## 4. Paper Edits

Files edited in the WSL paper directory:

- `main.tex`
- `sections/01_introduction.tex`
- `sections/02_agent_facing_compatibility.tex`
- `sections/04_results.tex`
- `sections/08_conclusion.tex`
- `tables/grounding_controls_auto.tex`

Specific updates:

- Abstract now says three public-changelog-derived before/after cases.
- Finding 4 now says three public-changelog-grounded semantic changes and names the Stripe Address Element default-formatting case.
- Table II / `tables/grounding_controls_auto.tex` now uses the combined real replay totals.
- Text under Table II now reports 36/36 baseline success, 6/35 O0 silent success with 29/35 hidden violations, and 34/35 visible success with 0/35 hidden violations.
- Section II.C now states that the Stripe Address Element changelog example is used as an additional deterministic replay case in Finding 4.
- Fig. 1 caption now says the inset example is also replayed in Finding 4.
- Conclusion now says three real-changelog-derived replays.

## 5. Compile and Checks

- Compile command: `latexmk -pdf -interaction=nonstopmode main.tex`.
- Compile status: success.
- Final PDF page count: 10.
- Undefined citations/references: none found.
- Section IX added: no.
- Appendix added/input: no.
- Fig. 1 render check: passed by page-2 PDF preview.
- Inconsistent two-vs-three replay count in active paper files: none found.
- Placeholder text: none found in active paper files.

## 6. Integrity

- Agent/API/runner executed in Phase 12K: no.
- Phase 12J rerun in Phase 12K: no.
- Phase 5 / Phase 8 / Phase 10 rerun: no.
- Frozen 1815-cell main results modified: no.
- Existing raw artifacts deleted or modified: no.
- Address Element is described as a deterministic local wrapper replay, not a live Stripe experiment.
- The paper does not claim production incident frequency or production frequency; remaining production-incident/frequency wording is negative limitation wording.

## 7. Outcome

Phase 12K integrated the Address Element replay as a third real-changelog-grounded deterministic replay case. The result is paper-ready at 10 pages, with the important caveat that the Address Element O0 silent condition shows a partial, not universal, failure pattern.
