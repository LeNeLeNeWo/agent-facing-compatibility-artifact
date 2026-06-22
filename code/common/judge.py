"""Lightweight LLM-as-Judge for QA / open-ended scoring.

Used by pilots ① ⑤ ⑥ to score correctness when string match is too strict.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from .llm_client import MimoClient


_JUDGE_SYSTEM = """You are a strict evaluator. You will be given a question, the gold answer, and a candidate answer.
You must decide whether the candidate is correct.

Output STRICTLY a JSON object on a single line, with this schema:
{"correct": 0 or 1, "reason": "<one short sentence>"}

Rules:
- "correct"=1 only if the candidate semantically matches the gold answer.
- Numeric answers: equivalent if they reduce to the same number (ignore formatting).
- Short factoid answers: case- and whitespace-insensitive equivalence.
- If the candidate contains the correct answer plus extra non-conflicting info, treat as correct.
- Do not output anything outside the JSON.
"""


def _strip_to_json(text: str) -> Optional[str]:
    m = re.search(r"\{.*?\}", text, re.DOTALL)
    return m.group(0) if m else None


def judge_one(
    question: str,
    gold: str,
    candidate: str,
    *,
    client: Optional[MimoClient] = None,
) -> tuple[int, str]:
    """Returns (correct ∈ {0,1}, reason)."""
    cli = client or MimoClient()
    prompt = (
        f"Question: {question}\n"
        f"Gold answer: {gold}\n"
        f"Candidate answer: {candidate}\n\n"
        f"Output the JSON now."
    )
    resp = cli.chat(prompt, system=_JUDGE_SYSTEM, temperature=0.0, max_tokens=120)
    raw = _strip_to_json(resp) or "{}"
    try:
        obj = json.loads(raw)
        return int(bool(obj.get("correct", 0))), str(obj.get("reason", ""))
    except json.JSONDecodeError:
        # 极端 fallback：粗暴 substring 匹配
        gold_norm = gold.strip().lower()
        cand_norm = candidate.strip().lower()
        return int(gold_norm in cand_norm), "fallback_substring"


def quick_match(gold: str, candidate: str) -> int:
    """No-LLM quick scoring for numeric/short answers; faster sanity-check."""
    g = gold.strip().lower()
    c = (candidate or "").strip().lower()
    # 取候选的最后一个数字（常见的 "...the answer is 42" 模式）
    nums = re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", c)
    g_nums = re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", g)
    if g_nums:
        return int(bool(nums and nums[-1] == g_nums[-1]))
    return int(g in c)
