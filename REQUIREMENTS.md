# Requirements

## Offline Review

- Python 3.10 or newer
- `pytest`

The offline tests read JSON/Markdown/LaTeX/PDF artifacts and do not need API
keys.

## Optional Analysis Regeneration

Some analysis scripts use `numpy`, `scipy`, `pandas`, and `matplotlib`.

## Optional Live Rerun

Live reruns require `openai`, `python-dotenv`, provider credentials, and a
working tau-bench installation. They are intentionally excluded from the default
review path.
