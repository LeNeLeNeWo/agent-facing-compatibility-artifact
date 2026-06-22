# Paper Mapping

| Paper concept | AFC-Gate module |
| --- | --- |
| agent-facing compatibility | `compatibility.py` |
| execution exposure | `exposure.py` |
| semantic observability | `observability.py` |
| paired protocol | `planner.py` and `replay.py` |
| AFC-Gate report | `report.py` |

The research code contains experiment runners, provider integrations, and raw
artifact processing. The open-source toolkit keeps the reusable framework and
removes provider-specific execution paths so the toy demo can run without API
calls.
