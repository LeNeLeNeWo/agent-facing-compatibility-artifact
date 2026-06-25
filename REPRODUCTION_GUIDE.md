# Reproduction Guide

## Level 0: Inspect Artifact

No execution required. Review:

- `docs/taxonomy.md`
- `data/manifests/`
- `results/main_results/`
- `results/phase10_nonobviousness/`
- `results/phase10_real_case_replay/`
- `results/phase12_address_element_replay/`
- `figures/pdf/`
- `tables/generated_tex/`
- `results/phase11_audits/`

## Level 1: Offline Reproduction

No API keys are required. These commands check frozen summaries, generated
assets, number reconciliation, cluster-bootstrap audit presence, secret scan,
and artifact integrity:

```bash
bash scripts/reproduce_main_results.sh
bash scripts/reproduce_figures.sh
bash scripts/reproduce_audits.sh
python -m pytest tests/
```

The commands do not run agents and do not call provider APIs.

The supplemental Address Element replay artifacts are frozen outputs under
`results/phase12_address_element_replay/`. They can be inspected offline; the
artifact does not call the live Stripe API.

## Level 2: Optional Live Rerun

Live reruns require provider API keys, compatible base URLs, and a tau-bench
environment. They are optional and are not needed to check the reported frozen
results. Reviewers should not rerun expensive API experiments by default.
