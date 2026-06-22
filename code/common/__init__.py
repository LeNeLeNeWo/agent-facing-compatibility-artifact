"""Shared infrastructure for all 6 thesis-idea pilots.

Modules:
    llm_client: MimoClient (OpenAI-compatible) with retry & batching.
    tasks:      Lightweight task loaders (HotpotQA / GSM8K / synthetic).
    stats:      Bootstrap, Cohen's d, multi-comparison, verdict utility.
    judge:      LLM-as-Judge wrapper.
    runner:     Generic concurrent runner with on-disk cache.
"""
import sys as _sys

# Reconfigure stdout/stderr to UTF-8 on Windows (default GBK can't print Δ R² · etc.)
for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

__version__ = "0.1.0"

