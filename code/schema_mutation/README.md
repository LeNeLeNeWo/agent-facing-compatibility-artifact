# Schema Mutation Testing for LLM Agents

Code for the project: *Tool Schema Evolution Breaks LLM Agents*.

See `papers/01-SCHEMA-EVOLUTION-PROPOSAL.md` and `papers/02-PILOT-DESIGN.md`.

## Layout

```
code/schema_mutation/
├── __init__.py
├── README.md            ← you are here
├── mutator.py           ← 10 mutation classes (M01-M10)
├── metrics.py           ← 4 core metrics for the pilot
└── runner.py            ← (Day-2 TODO) hal-harness wrapper
```

## Quick start

```powershell
cd c:/Users/zhaoxuyang/Desktop/learn

python -m code.schema_mutation.mutator     # smoke-test all 10 mutations
python -m code.schema_mutation.metrics     # toy-data pilot summary
```

## Mutation taxonomy

| ID  | Name                         | Schema change | Human BC | Agent BC |
|-----|------------------------------|---------------|----------|----------|
| M01 | Identifier rename            | param name    | half     | breaks   |
| M02 | Type / format change         | param type    | breaks   | breaks   |
| M03 | Requiredness change          | required[]    | breaks   | breaks   |
| M04 | Default value semantic drift | description   | **safe** | **breaks** ⚠ |
| M05 | Unit / scale change          | description   | check changelog | **breaks** ⚠ |
| M06 | Enum value rename            | enum[]        | breaks   | breaks   |
| M07 | Description paraphrase       | description   | **safe** | **breaks** ⚠ |
| M08 | Error format change          | x-error-format| half     | breaks   |
| M09 | Permission / rate change     | x-precondition| breaks   | breaks   |
| M10 | Pagination change            | x-response    | half     | breaks   |

⚠ = "human-safe but agent-breaking" — these are the heroes of our taxonomy.

## Day-2 TODO

- [ ] `runner.py` — hal-harness wrapper that takes (task, schema, model, seed)
      and produces a trajectory record consumable by `metrics.py`
- [ ] LLM-based paraphrase for M07 (currently template-based)
- [ ] Tool sandboxing layer for M08/M09/M10 (runner enforces the
      meta-level changes the schema declares via `x-error-format`,
      `x-precondition`, `x-response-shape`)

## Project conventions

- Trajectory record format: see top of `metrics.py`
- Mutation record format: see `Mutation` dataclass in `mutator.py`
- All mutations deterministic given a seed (Python `random.Random(seed)`)
