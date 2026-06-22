# Phase 10B API Evolution Annotation Guidelines

## Scope

Review only public official source URLs and the short evidence snippets in the sheet. The automatic labels are candidates, not validated labels.

## A/B/C/D Taxonomy

- A surface/representation change: names, formats, descriptions, examples, or representation details change without a clear schema-contract or semantic-contract change.
- B schema-contract change: request/response types, requiredness, enum values, field presence, or typed client compatibility changes.
- C semantic-contract change: endpoint, field names, JSON types, and call signature can stay stable while task semantics change.
- D protocol/operational change: authentication, permissions, pagination, rate limits, error envelope, transport, or operational protocol changes dominate the compatibility risk.
- mixed: use when the entry clearly combines multiple classes and one class is not dominant.
- unclear: use when the official evidence is insufficient.

## C Subclasses

- C1 unit/scale drift: numeric interpretation, units, precision, scale, thresholds, or validation ranges change while schema shape remains stable.
- C2 currency/locale drift: currency, locale, timezone, language, regional behavior, or formatting semantics change.
- C3 default behavior drift: omitted or optional inputs keep the same schema but produce a changed default outcome.
- C4 business-rule drift: eligibility, payment, refund, policy, workflow, approval, restriction, or domain rule changes while the call surface can remain stable.
- none/unclear: use when the entry is C-like but the subclass is not supported by the evidence.

## Visibility Labels

- schema-invisible means the official change could plausibly preserve endpoint, field names, JSON types, and typed call signature while changing behavior.
- schema-visible means a conventional schema or typed-client check should plausibly detect the change.
- runtime-visible means the evolved API exposes an error, diagnostic, migration note, or other visible signal during the task.
- runtime-invisible means the task can appear locally successful and the changed rule is only detected by final-state/oracle validation.
- unknown is preferred when the changelog does not clearly state runtime behavior.

## Confidence

- high-confidence C-class requires official evidence for a semantic behavior change and a plausible unchanged call surface.
- medium-confidence means the semantic interpretation is plausible but a reviewer must inspect more context.
- low-confidence means the automatic label is weak and should not be used as a paper example without stronger evidence.

## Conservative Review Rules

- If uncertain, mark `unclear`; do not force a taxonomy label.
- Use only official source URLs and short evidence snippets.
- Do not infer production frequency, incident rate, or user impact from this corpus.
- The corpus supports a claim about public changelog grounding, not production base rates.
