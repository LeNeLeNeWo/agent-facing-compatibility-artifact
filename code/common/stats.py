"""Statistics utilities: bootstrap, Cohen's d, multi-comparison, verdict.

Designed for tiny pilot scale (n≈100): everything pure-numpy, no SciPy hard
dependency for the basics (we only use scipy.stats for two-sided tests).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


# ---------------------------------------------------------------------------
# Effect size & test
# ---------------------------------------------------------------------------


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    """Pooled-SD Cohen's d. Sign convention: positive means mean(a) > mean(b)."""
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if len(a_arr) < 2 or len(b_arr) < 2:
        return float("nan")
    var_a = a_arr.var(ddof=1)
    var_b = b_arr.var(ddof=1)
    pooled = math.sqrt(((len(a_arr) - 1) * var_a + (len(b_arr) - 1) * var_b)
                       / (len(a_arr) + len(b_arr) - 2)) if (len(a_arr) + len(b_arr) > 2) else 0.0
    if pooled == 0:
        return float("nan")
    return float((a_arr.mean() - b_arr.mean()) / pooled)


def bootstrap_diff_ci(
    a: Sequence[float],
    b: Sequence[float],
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Returns (delta, lo, hi) where delta = mean(a) - mean(b)."""
    rng = np.random.default_rng(seed)
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if len(a_arr) == 0 or len(b_arr) == 0:
        return float("nan"), float("nan"), float("nan")
    diffs = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sa = rng.choice(a_arr, size=len(a_arr), replace=True)
        sb = rng.choice(b_arr, size=len(b_arr), replace=True)
        diffs[i] = sa.mean() - sb.mean()
    lo, hi = np.quantile(diffs, [alpha / 2, 1 - alpha / 2])
    return float(a_arr.mean() - b_arr.mean()), float(lo), float(hi)


def perm_test_p(
    a: Sequence[float],
    b: Sequence[float],
    n_perm: int = 2000,
    seed: int = 42,
) -> float:
    """Two-sided permutation test for difference of means."""
    rng = np.random.default_rng(seed)
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if len(a_arr) == 0 or len(b_arr) == 0:
        return float("nan")
    obs = abs(a_arr.mean() - b_arr.mean())
    pooled = np.concatenate([a_arr, b_arr])
    n_a = len(a_arr)
    extreme = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        diff = abs(pooled[:n_a].mean() - pooled[n_a:].mean())
        if diff >= obs:
            extreme += 1
    return float((extreme + 1) / (n_perm + 1))


# ---------------------------------------------------------------------------
# High-level compare()
# ---------------------------------------------------------------------------


@dataclass
class CompareResult:
    name_a: str
    name_b: str
    n_a: int
    n_b: int
    mean_a: float
    mean_b: float
    delta: float
    ci_lo: float
    ci_hi: float
    cohens_d: float
    p_value: float

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def compare(
    a: Sequence[float],
    b: Sequence[float],
    *,
    name_a: str = "A",
    name_b: str = "B",
    n_boot: int = 1000,
    n_perm: int = 1000,
    seed: int = 42,
) -> CompareResult:
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    delta, lo, hi = bootstrap_diff_ci(a_arr, b_arr, n_boot=n_boot, seed=seed)
    return CompareResult(
        name_a=name_a,
        name_b=name_b,
        n_a=len(a_arr),
        n_b=len(b_arr),
        mean_a=float(a_arr.mean()) if len(a_arr) else float("nan"),
        mean_b=float(b_arr.mean()) if len(b_arr) else float("nan"),
        delta=delta,
        ci_lo=lo,
        ci_hi=hi,
        cohens_d=cohens_d(a_arr, b_arr),
        p_value=perm_test_p(a_arr, b_arr, n_perm=n_perm, seed=seed),
    )


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def verdict(result: CompareResult, *, alpha: float = 0.05, d_threshold: float = 0.2) -> str:
    """根据 CI 是否含 0、p 值、effect size 给出语义化裁定。

    返回值之一：
        "STRONG SIGNAL (A > B)"  / "STRONG SIGNAL (A < B)"
        "WEAK SIGNAL (A > B)"    / "WEAK SIGNAL (A < B)"
        "NULL"
    """
    if not math.isfinite(result.delta):
        return "INVALID"
    sig = (result.ci_lo > 0 or result.ci_hi < 0) and result.p_value < alpha
    if not sig:
        return "NULL"
    direction = "A > B" if result.delta > 0 else "A < B"
    strong = abs(result.cohens_d) >= d_threshold
    return f"{'STRONG' if strong else 'WEAK'} SIGNAL ({direction})"


# ---------------------------------------------------------------------------
# Multi-comparison Holm-Bonferroni
# ---------------------------------------------------------------------------


def holm_bonferroni(p_values: Sequence[float], alpha: float = 0.05) -> list[bool]:
    """Returns rejection booleans aligned with input order."""
    p = list(p_values)
    n = len(p)
    order = sorted(range(n), key=lambda i: p[i])
    rej = [False] * n
    for rank, idx in enumerate(order):
        threshold = alpha / (n - rank)
        if p[idx] <= threshold:
            rej[idx] = True
        else:
            break
    return rej
