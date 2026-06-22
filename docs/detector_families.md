# Detector Families

- SchemaCheckerOnly: static schema/client compatibility check.
- RandomReplayGate: randomly selected replay cells.
- UsedToolReplayGate: replay over tools observed in a baseline trajectory.
- IntentAlignedReplayGate: replay over task-intent-aligned tools.
- AFCGate: artifact implementation combining schema checks and targeted replay
  heuristics.
- ExhaustiveReplayOracle: high-cost reference replay over all available cells.

AFC-Gate is an artifact implementation and should not be described as a
separately evaluated production system.
