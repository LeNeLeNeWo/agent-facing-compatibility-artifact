"""4 core metrics for the schema-evolution pilot.

Each metric takes a list of trajectory records (dicts) and returns a
summary number or table.

Trajectory record shape (produced by runner.py):
    {
        "task_id":       "tau_retail_001",
        "model":         "mimo-v2-pro",
        "mutation_type": "M04_default_semantic_drift" | "" (original),
        "condition":     "A_original" | "B_mutated" | "C_recovery",
        "seed":          1,
        "success":       True | False,
        "tokens":        1234,
        "n_tool_calls":  5,
        "n_tool_errors": 1,
        "trajectory":    [...],
    }
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def binary_classification_metrics(
    y_true: list[int],
    y_pred: list[int],
    y_score: list[float] | None = None,
) -> dict[str, Any]:
    """Compute binary metrics used by predictor generalization.

    AUROC/AUPRC are returned as ``None`` when only one class is present or no
    scorer is available.
    """
    tp = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 0)
    n = len(y_true)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    out: dict[str, Any] = {
        "accuracy": (tp + tn) / n if n else None,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "n": n,
        "positive_rate": (sum(y_true) / n) if n else None,
        "auroc": None,
        "auprc": None,
    }
    if y_score is not None and len(set(y_true)) == 2:
        try:
            from sklearn.metrics import average_precision_score, roc_auc_score

            out["auroc"] = float(roc_auc_score(y_true, y_score))
            out["auprc"] = float(average_precision_score(y_true, y_score))
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# Metric 1: Success rate (per group)
# ---------------------------------------------------------------------------

def success_rate(records: list[dict], group_by: list[str] | None = None
                 ) -> dict:
    """Mean success per group. If group_by is None, returns overall."""
    if not records:
        return {}
    if group_by is None:
        n = len(records)
        s = sum(1 for r in records if r.get("success"))
        return {"_overall_": s / n if n else 0.0}

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        key = tuple(r.get(g, "") for g in group_by)
        groups[key].append(r)
    return {
        " | ".join(f"{k}={v}" for k, v in zip(group_by, key)):
            sum(1 for r in items if r.get("success")) / len(items)
        for key, items in groups.items()
    }


# ---------------------------------------------------------------------------
# Metric 2: Mutation Odds Ratio
# ---------------------------------------------------------------------------

def mutation_odds_ratio(records: list[dict], mutation_type: str,
                        model: str | None = None) -> dict:
    """For a given mutation_type:
        OR = P(fail | mutation) / P(fail | no mutation)

    Returns dict with point estimate + counts. Caller should bootstrap
    for CI.
    """
    in_mut = [r for r in records
              if r.get("mutation_type") == mutation_type
              and r.get("condition") == "B_mutated"
              and (model is None or r.get("model") == model)]
    in_orig = [r for r in records
               if r.get("condition") == "A_original"
               and (model is None or r.get("model") == model)]

    if not in_mut or not in_orig:
        return {"odds_ratio": None, "n_mut": len(in_mut),
                "n_orig": len(in_orig), "note": "insufficient data"}

    p_fail_mut = sum(1 for r in in_mut if not r.get("success")) / len(in_mut)
    p_fail_orig = sum(1 for r in in_orig if not r.get("success")) / len(in_orig)

    # OR = (p_mut/(1-p_mut)) / (p_orig/(1-p_orig)), with smoothing
    eps = 0.01
    p_m = max(min(p_fail_mut, 1 - eps), eps)
    p_o = max(min(p_fail_orig, 1 - eps), eps)
    odds = (p_m / (1 - p_m)) / (p_o / (1 - p_o))

    return {
        "odds_ratio": round(odds, 3),
        "p_fail_mutated": round(p_fail_mut, 3),
        "p_fail_original": round(p_fail_orig, 3),
        "n_mut": len(in_mut),
        "n_orig": len(in_orig),
    }


# ---------------------------------------------------------------------------
# Metric 3: Recovery Rate
# ---------------------------------------------------------------------------

def recovery_rate(records: list[dict], mutation_type: str | None = None,
                  model: str | None = None) -> dict:
    """For matched (task, seed) pairs across conditions A/B/C:
        recovery = (success_C - success_B) / max(success_A - success_B, eps)

    Interpretation: of the gap that mutation opened (A → B), how much
    does error-feedback (C) close back?
    """
    def _filter(cond: str) -> list[dict]:
        return [r for r in records
                if r.get("condition") == cond
                and (mutation_type is None
                     or r.get("mutation_type") == mutation_type
                     or cond == "A_original")
                and (model is None or r.get("model") == model)]

    a, b, c = _filter("A_original"), _filter("B_mutated"), _filter("C_recovery")
    if not (a and b and c):
        return {"recovery_rate": None,
                "note": "insufficient data across A/B/C"}

    s_a = sum(1 for r in a if r.get("success")) / len(a)
    s_b = sum(1 for r in b if r.get("success")) / len(b)
    s_c = sum(1 for r in c if r.get("success")) / len(c)

    gap = s_a - s_b
    if gap < 1e-3:
        return {"recovery_rate": None,
                "success_A": round(s_a, 3),
                "success_B": round(s_b, 3),
                "success_C": round(s_c, 3),
                "note": "no degradation gap (A ≈ B); recovery undefined"}

    return {
        "recovery_rate": round((s_c - s_b) / gap, 3),
        "success_A": round(s_a, 3),
        "success_B": round(s_b, 3),
        "success_C": round(s_c, 3),
        "n_a": len(a), "n_b": len(b), "n_c": len(c),
    }


# ---------------------------------------------------------------------------
# Metric 4: Mitigation Lift (placeholder for Month 2; pilot uses recovery)
# ---------------------------------------------------------------------------

def mitigation_lift(records: list[dict], mitigation_id: str,
                    mutation_type: str | None = None) -> dict:
    """For Month 2 full matrix: success_with_mitigation_M_i - success_mut.

    Pilot uses recovery_rate() instead since C condition = error feedback
    only (one mitigation type).
    """
    in_mit = [r for r in records
              if r.get("mitigation") == mitigation_id
              and (mutation_type is None
                   or r.get("mutation_type") == mutation_type)]
    in_mut = [r for r in records
              if r.get("condition") == "B_mutated"
              and (mutation_type is None
                   or r.get("mutation_type") == mutation_type)]
    if not in_mit or not in_mut:
        return {"lift": None, "n_mit": len(in_mit), "n_mut": len(in_mut)}
    s_mit = sum(1 for r in in_mit if r.get("success")) / len(in_mit)
    s_mut = sum(1 for r in in_mut if r.get("success")) / len(in_mut)
    return {
        "lift": round(s_mit - s_mut, 3),
        "success_with_mitigation": round(s_mit, 3),
        "success_mutated": round(s_mut, 3),
        "n_mit": len(in_mit), "n_mut": len(in_mut),
    }


# ---------------------------------------------------------------------------
# Pilot summary helper
# ---------------------------------------------------------------------------

def pilot_summary(records: list[dict], models: list[str],
                  mutation_types: list[str]) -> dict:
    """Compute the 4-number pilot summary used in the Day-7 decision gate.

    Returns dict with keys:
      - baseline_per_model        (Metric 1)
      - odds_ratio_per_mut         (Metric 2)
      - recovery_per_mut           (Metric 3)
      - mut_x_model_grid           (heatmap data)
    """
    out: dict[str, Any] = {}

    # Metric 1 (baseline)
    out["baseline_per_model"] = {
        m: round(sum(1 for r in records
                     if r.get("condition") == "A_original"
                     and r.get("model") == m
                     and r.get("success")) /
                 max(1, sum(1 for r in records
                            if r.get("condition") == "A_original"
                            and r.get("model") == m)), 3)
        for m in models
    }

    # Metric 2
    out["odds_ratio_per_mut"] = {
        mt: mutation_odds_ratio(records, mt) for mt in mutation_types
    }

    # Metric 3
    out["recovery_per_mut"] = {
        mt: recovery_rate(records, mutation_type=mt)
        for mt in mutation_types
    }

    # Heatmap: success rate at condition B (mutated), grouped by mut x model
    grid = {}
    for mt in mutation_types:
        grid[mt] = {}
        for m in models:
            cell = [r for r in records
                    if r.get("condition") == "B_mutated"
                    and r.get("mutation_type") == mt
                    and r.get("model") == m]
            grid[mt][m] = (round(sum(1 for r in cell if r.get("success"))
                                 / max(1, len(cell)), 3) if cell else None)
    out["mut_x_model_grid"] = grid

    return out


# ---------------------------------------------------------------------------
# Self-test on toy data
# ---------------------------------------------------------------------------

def _self_test() -> int:
    """Generate toy data and run all 4 metrics."""
    import random as _r
    rng = _r.Random(42)
    records = []
    for task in range(10):
        for model in ["mimo", "deepseek", "qwen-7b"]:
            for seed in range(5):
                # baseline ~70% success
                records.append(dict(
                    task_id=f"task_{task}", model=model, seed=seed,
                    condition="A_original", mutation_type="",
                    success=rng.random() < 0.7,
                ))
                # mutated: add a per-mutation-type penalty
                for mt in ["M01_rename", "M04_default_semantic_drift",
                           "M07_description_paraphrase"]:
                    penalty = (0.20 if mt == "M01_rename" else
                               0.45 if mt == "M04_default_semantic_drift" else
                               0.55)
                    records.append(dict(
                        task_id=f"task_{task}", model=model, seed=seed,
                        condition="B_mutated", mutation_type=mt,
                        success=rng.random() < (0.7 - penalty),
                    ))
                    # recovery: get back ~half the gap
                    records.append(dict(
                        task_id=f"task_{task}", model=model, seed=seed,
                        condition="C_recovery", mutation_type=mt,
                        success=rng.random() < (0.7 - penalty / 2),
                    ))

    summary = pilot_summary(
        records,
        models=["mimo", "deepseek", "qwen-7b"],
        mutation_types=["M01_rename", "M04_default_semantic_drift",
                        "M07_description_paraphrase"],
    )
    import json
    print("[SELF-TEST] pilot_summary on toy data:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
