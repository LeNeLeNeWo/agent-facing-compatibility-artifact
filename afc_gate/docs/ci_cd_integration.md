# CI/CD Integration

AFC-Gate is intended as a lightweight screening gate before or alongside schema
checks. A typical workflow stores baseline-successful trajectories and evaluates
candidate policy or API changes during review.

```yaml
name: AFC-Gate

on:
  pull_request:
    paths:
      - "api_specs/**"
      - "tool_schemas/**"
      - "policy_specs/**"

jobs:
  afc-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install AFC-Gate
        run: pip install -e ./afc_gate
      - name: Run compatibility gate
        run: afc-gate analyze --trajectories trajectories/baseline.json --changes changes/api_change.json --out afc_report.md
```

Recommended use:

- Treat high risk silent exposed changes as requiring paired replay.
- Keep schema checks in place.
- Require explicit policy errors or migration notes for business-rule changes
  that agents may rely on.
- Review trajectory samples for private data before storing them in CI.
