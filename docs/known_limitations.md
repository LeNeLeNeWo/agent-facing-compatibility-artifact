# Known Limitations

- The default artifact path reproduces aggregate results from frozen summaries;
  it does not rerun LLM-agent cells.
- Live reruns require provider API keys, provider availability, and compatible
  tau-bench setup.
- Public changelog grounding is not a production frequency estimate.
- Real-changelog replay cases are deterministic local wrappers, not live
  Stripe/GitHub service calls.
- The Stripe Address Element replay is grounded in a public changelog and uses a
  deterministic local wrapper; it is not a live Stripe API experiment and does
  not estimate production incident frequency.
- Oracle review packets are human-review-ready, but the artifact does not claim
  human-validated oracle precision.
