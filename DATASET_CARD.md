# Dataset Card

## Dataset Components

- TAU-BENCH-derived task/cell metadata for the frozen main experiment.
- Mutation taxonomy labels for schema-visible and schema-invisible API changes.
- Public API-evolution corpus: 151 entries from nine official providers.
- Oracle audit packet with deterministic sanity-check categories.
- Phase 10 non-obviousness control summaries.
- Real-changelog-grounded replay cases implemented as deterministic local
  wrappers.
- Supplemental Stripe Address Element public-changelog-grounded replay outputs
  from Phase 12.

## Data Fields

Typical records include task/domain identifiers, model/provider labels,
mutation class/subclass, observability condition, status, success/reward,
hidden-violation indicators, and audit metadata. Public changelog records
include provider, URL, title, date when available, taxonomy class, and short
evidence snippets.

## Intended Use

The dataset supports artifact review, offline reproduction of aggregate results,
and inspection of the experimental design. It is not intended for estimating
real-world production incident frequency.

## Limitations

The corpus is a public-changelog sample, not a production telemetry sample.
The replay cases are deterministic local wrappers grounded in changelog
evidence, not live third-party service tests. Human review packets are included,
but human-validated labels should not be claimed unless review is completed.

## Supplemental Public Changelog Example and Address Element Replay

The artifact includes an additional Stripe Address Element public-changelog-grounded replay case. This case is based on a public Stripe changelog entry in which the Address Element state field default formatting changed. The replay uses a deterministic local wrapper and does not call the live Stripe API. It should not be interpreted as a production incident or production frequency measurement.

## Privacy and Anonymity

The artifact is anonymized for review and should not contain real author
identity, local absolute paths, provider secrets, or private endpoints. TAU-BENCH
task data are benchmark/synthetic task materials; no real personal data is
claimed.
