# Compliant Semantic Failures: Testing Agent-Facing Compatibility of Evolving Tool APIs

This repository is an anonymized artifact package for double-blind review. It
contains the code, frozen summaries, review packets, public API-evolution
grounding data, generated figures/tables, AFC-Gate prototype, and offline
audits needed to inspect and reproduce the reported aggregate results without
rerunning expensive LLM-agent experiments.

## Artifact Contents

- `code/`: mutation generation, exposure mapping, paired analysis,
  observability summaries, unused-tool controls, C1-C4 semantic generalization,
  cluster/statistical audits, number reconciliation, and figure/table scripts.
- `data/`: manifests, normalized paired inputs, review packets, real API
  grounding corpus, oracle audit packet, non-obviousness control data, and
  real-changelog replay plans.
- `results/`: frozen main results, Phase 5 observability summaries, Phase 8
  exposure and semantic-generalization controls, Phase 10 grounding/control
  outputs, the supplemental Phase 12 Address Element replay, Phase 11/12
  audits, and AFC-Gate demo outputs.
- `figures/` and `tables/`: generated paper-ready PDFs and LaTeX tables.
- `afc_gate/`: artifact implementation of the AFC-Gate prototype, with toy
  example input/output and tests. It is not a separately evaluated production
  system.
- `scripts/` and `tests/`: offline reproduction, integrity, and secret-scan
  utilities.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/reproduce_audits.sh
python -m pytest tests/
```

## Reproduction Levels

- **Level 0: Inspect artifact.** No execution required. Inspect taxonomy,
  manifests, summaries, plots, generated tables, and audit reports.
- **Level 1: Offline reproduction.** No API keys required. Re-run integrity,
  number, figure/table, and secret-scan checks from frozen summaries.
- **Level 2: Optional live rerun.** Requires provider API keys and a tau-bench
  environment. This is optional and is not needed to validate the reported
  frozen results.

## Expected Outputs

The offline checks should confirm the headline counts recorded in
`docs/reproduction_headlines.json`, including 1815 formal main cells, 151 public
API entries, 61 C-class candidates, non-obviousness control rates, and the
real-changelog-grounded replay results.

## Supplemental Public Changelog Example and Address Element Replay

The artifact includes an additional Stripe Address Element public-changelog-grounded replay case. This case is based on a public Stripe changelog entry in which the Address Element state field default formatting changed. The replay uses a deterministic local wrapper and does not call the live Stripe API. It is reported as a supplemental Phase 12 replay and is also folded into the paper's combined real-changelog replay totals.

## Known Limitations

- Frozen API-based experiments are not rerun by default.
- Live reruns require provider keys and may drift with provider/model changes.
- The public changelog corpus is not a production incident frequency estimate.
- Deterministic local wrappers are real-changelog-grounded replays, not live
  third-party service tests.
- The oracle audit is a deterministic sanity check and human-review-ready
  packet, not a human kappa study.

## Anonymous Review Note

This artifact is anonymized for double-blind review. It omits author-identifying
metadata, local absolute paths, provider secrets, and private endpoints.
