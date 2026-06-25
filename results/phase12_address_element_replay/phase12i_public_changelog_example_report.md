# Phase 12I Public Changelog Example Report

## 1. Reference Added

Added bibliography entry:

- `stripe2026addressstateformat`

Source:

- `https://docs.stripe.com/changelog/dahlia/2026-03-25/address-element-getvalue-and-change-event-formatting`

The entry is a normal BibTeX `@misc` entry in `IEEE_Conference_Template/references.bib`.

## 2. Fig. 1 Changes

Fig. 1 remains the same mechanism figure:

- developer-visible channels;
- propagation gap;
- agent-runtime channels.

Added a compact inset titled:

- `Concrete public changelog example`

Inset content:

- Stripe Address Element `state`;
- Before: browser-locale format;
- After: Latin format by default;
- Same call/event succeeds; output semantics changed.

Updated figure source:

- `IEEE_Conference_Template/figures/phase12f_sources/fig1_compliant_semantic_failure.tex`

Updated figure outputs:

- `IEEE_Conference_Template/figures/fig1_compliant_semantic_failure.pdf`
- `IEEE_Conference_Template/figures/fig1_compliant_semantic_failure.png`

## 3. Caption Update

The Fig. 1 caption now cites `stripe2026addressstateformat` and states that the inset is a public Stripe changelog example.

The previous phrase `absent from both runtime channels` was removed. The caption now uses:

- `absent from the agent-runtime channels`

## 4. Section II.C Update

Added a compact illustrative paragraph:

- Stripe's 2026 Address Element changelog changes the default `state` output from browser-localized to Latin-formatted.
- The same `getValue()` call/event continues to return a string.
- The call need not fail; the semantic/default-formatting rule changes unless propagated into the agent's runtime context.
- The example is explicitly labeled as illustrative and not one of the formal replay cells.

## 5. Boundary Preservation

The paper does not claim that this Stripe Address Element example is:

- a Phase 10F formal replay case;
- a live Stripe API experiment;
- a production incident;
- a production-frequency estimate.

Finding 4 / Table II remain unchanged in role: they report deterministic local wrapper replay evidence from the Phase 10 artifacts.

## 6. Compile and Page Count

Compile command:

```bash
cd "<HOME>/ICSE 2027/schema_mutation_paper_package_20260612_194214/IEEE_Conference_Template"
latexmk -pdf -interaction=nonstopmode main.tex
```

Result:

- Compile status: succeeded.
- Final PDF page count: 10.
- Undefined citations/references: none reported.
- Appendix / Section IX: not present.
- Fig. 1 render: checked via Poppler PNG render; inset is readable and not clipped.

## 7. Warnings

Remaining warnings are layout-level and pre-existing in character:

- underfull boxes;
- one small taxonomy/table overfull warning;
- PDF inclusion version warning for included figure assets;
- underfull lines in the new Stripe bibliography URL.

No warning blocks compilation.

## 8. Execution Safety

No experiments, agent/API calls, or runner scripts were executed. Frozen raw results were not modified.

