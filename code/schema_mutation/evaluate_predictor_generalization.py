"""Evaluate predictor feature families under deconfounded generalization splits."""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.schema_mutation.metrics import binary_classification_metrics  # noqa: E402
from code.schema_mutation.predictor_features import (  # noqa: E402
    LEAKAGE_FIELDS,
    feature_value,
    legal_feature_families,
)
from code.schema_mutation.predictor_splits import SPLITS, make_folds  # noqa: E402

RUNS = _REPO_ROOT / "runs" / "schema_mutation"
PAPER = _REPO_ROOT / "IEEE_Conference_Template"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _label(row: dict[str, Any]) -> int:
    return 1 if row.get("agent_breaking") else 0


def _as_features(row: dict[str, Any], features: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in features:
        if f in LEAKAGE_FIELDS:
            raise ValueError(f"leakage field in predictor features: {f}")
        v = feature_value(row, f)
        out[f] = "unknown" if v is None else v
    return out


def _majority_predict(train_y: list[int], n: int) -> tuple[list[int], list[float]]:
    pos = sum(train_y)
    pred = 1 if pos >= len(train_y) / 2 else 0
    score = pos / len(train_y) if train_y else 0.0
    return [pred] * n, [score] * n


def _fit_predict(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    features: list[str],
    sklearn_available: bool,
) -> tuple[list[int], list[float]]:
    train_y = [_label(r) for r in train_rows]
    if not features or not sklearn_available:
        return _majority_predict(train_y, len(test_rows))
    try:
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline

        clf = make_pipeline(
            DictVectorizer(sparse=True),
            LogisticRegression(max_iter=1000, class_weight="balanced"),
        )
        clf.fit([_as_features(r, features) for r in train_rows], train_y)
        test_x = [_as_features(r, features) for r in test_rows]
        preds = [int(x) for x in clf.predict(test_x)]
        if hasattr(clf[-1], "predict_proba"):
            scores = [float(x[1]) for x in clf.predict_proba(test_x)]
        else:
            scores = [float(x) for x in preds]
        return preds, scores
    except Exception as exc:
        print(f"[warn] sklearn fit failed; falling back to majority: {type(exc).__name__}: {exc}")
        return _majority_predict(train_y, len(test_rows))


def _eval_family_split(
    rows: list[dict[str, Any]],
    family: str,
    features: list[str],
    split: str,
    sklearn_available: bool,
    seed: int,
) -> dict[str, Any]:
    y_true_all: list[int] = []
    y_pred_all: list[int] = []
    y_score_all: list[float] = []
    skipped: list[dict[str, str]] = []
    folds_used = 0
    for train_idx, test_idx, key in make_folds(rows, split, seed=seed):
        train = [rows[i] for i in train_idx]
        test = [rows[i] for i in test_idx]
        train_y = [_label(r) for r in train]
        test_y = [_label(r) for r in test]
        if not train or not test:
            skipped.append({"fold": key, "reason": "empty_train_or_test"})
            continue
        if len(set(train_y)) < 2 and family != "majority":
            skipped.append({"fold": key, "reason": "train_has_single_class"})
            continue
        if len(set(test_y)) < 2:
            skipped.append({"fold": key, "reason": "test_has_single_class"})
            continue
        pred, score = _fit_predict(train, test, features, sklearn_available)
        y_true_all.extend(test_y)
        y_pred_all.extend(pred)
        y_score_all.extend(score)
        folds_used += 1

    metrics = binary_classification_metrics(y_true_all, y_pred_all, y_score_all if y_score_all else None)
    return {
        "feature_family": family,
        "split": split,
        **metrics,
        "folds": folds_used,
        "skipped_folds": skipped,
        "skipped_fold_count": len(skipped),
    }


def evaluate(rows: list[dict[str, Any]], seed: int = 7) -> dict[str, Any]:
    families = legal_feature_families()
    try:
        import sklearn  # noqa: F401

        sklearn_available = True
    except Exception:
        sklearn_available = False

    results: list[dict[str, Any]] = []
    for family, features in families.items():
        for split in SPLITS:
            if split == "leave_env_out" and len({r.get("env") for r in rows}) < 2:
                results.append(
                    {
                        "feature_family": family,
                        "split": split,
                        "accuracy": None,
                        "precision": None,
                        "recall": None,
                        "f1": None,
                        "auroc": None,
                        "auprc": None,
                        "tp": 0,
                        "tn": 0,
                        "fp": 0,
                        "fn": 0,
                        "n": 0,
                        "positive_rate": None,
                        "folds": 0,
                        "skipped_folds": [{"fold": "all", "reason": "not_enough_envs"}],
                        "skipped_fold_count": 1,
                    }
                )
                continue
            results.append(_eval_family_split(rows, family, features, split, sklearn_available, seed))
    return {
        "sklearn_available": sklearn_available,
        "feature_families": families,
        "results": results,
    }


def _fmt(x: Any) -> str:
    if x is None:
        return "NA"
    if isinstance(x, float):
        return f"{x:.3f}"
    return str(x)


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    rows = payload["results"]
    lines = [
        "# Predictor Generalization Summary",
        "",
        f"Samples: {payload['dataset']['samples']}",
        f"Positive rate: {_fmt(payload['dataset']['positive_rate'])}",
        f"sklearn available: {payload['sklearn_available']}",
        "",
        "| Feature family | Random F1 | Leave-task F1 | Leave-tool F1 | Leave-policy F1 | Leave-model F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    by = {(r["feature_family"], r["split"]): r for r in rows}
    for fam in payload["feature_families"]:
        lines.append(
            f"| {fam} | {_fmt(by[(fam, 'random_split')]['f1'])} | "
            f"{_fmt(by[(fam, 'leave_task_out')]['f1'])} | "
            f"{_fmt(by[(fam, 'leave_tool_out')]['f1'])} | "
            f"{_fmt(by[(fam, 'leave_policy_out')]['f1'])} | "
            f"{_fmt(by[(fam, 'leave_model_out')]['f1'])} |"
        )
    warnings = payload.get("warnings") or []
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {w}" for w in warnings)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _latex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
    )


def _write_tex(path: Path, payload: dict[str, Any]) -> None:
    rows = payload["results"]
    by = {(r["feature_family"], r["split"]): r for r in rows}
    lines = [
        "% Auto-generated by code/schema_mutation/evaluate_predictor_generalization.py",
        "\\begin{table*}[t]",
        "\\caption{Predictor generalization under deconfounded feature families.}",
        "\\label{tab:predictor-generalization}",
        "\\centering",
        "\\footnotesize",
        "\\begin{tabular}{lccccc}",
        "\\toprule",
        "Feature family & Random F1 & Leave-task F1 & Leave-tool F1 & Leave-policy F1 & Leave-model F1 \\\\",
        "\\midrule",
    ]
    for fam in payload["feature_families"]:
        lines.append(
            f"{_latex_escape(fam)} & {_fmt(by[(fam, 'random_split')]['f1'])} & "
            f"{_fmt(by[(fam, 'leave_task_out')]['f1'])} & "
            f"{_fmt(by[(fam, 'leave_tool_out')]['f1'])} & "
            f"{_fmt(by[(fam, 'leave_policy_out')]['f1'])} & "
            f"{_fmt(by[(fam, 'leave_model_out')]['f1'])} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_appendix_tex(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "% Auto-generated by code/schema_mutation/evaluate_predictor_generalization.py",
        "\\begin{table*}[t]",
        "\\caption{Detailed predictor generalization metrics by split.}",
        "\\label{tab:predictor-generalization-appendix}",
        "\\centering",
        "\\scriptsize",
        "\\begin{tabular}{llrrrrrrrr}",
        "\\toprule",
        "Feature family & Split & Acc & Prec. & Rec. & F1 & AUROC & AUPRC & N & Folds \\\\",
        "\\midrule",
    ]
    for r in payload["results"]:
        lines.append(
            f"{_latex_escape(r['feature_family'])} & {_latex_escape(r['split'])} & "
            f"{_fmt(r['accuracy'])} & {_fmt(r['precision'])} & {_fmt(r['recall'])} & "
            f"{_fmt(r['f1'])} & {_fmt(r['auroc'])} & {_fmt(r['auprc'])} & "
            f"{r['n']} & {r['folds']} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_plot(path: Path, payload: dict[str, Any]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable; skipping plot: {exc}")
        return
    splits = ["random_split", "leave_task_out", "leave_tool_out", "leave_policy_out", "leave_model_out"]
    families = list(payload["feature_families"].keys())
    by = {(r["feature_family"], r["split"]): r for r in payload["results"]}
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    markers = ["o", "s", "^", "D", "x", "+", "*", "v", "p"]
    xs = list(range(len(splits)))
    for i, fam in enumerate(families):
        ys = [by[(fam, split)].get("f1") for split in splits]
        ys = [float("nan") if y is None else y for y in ys]
        ax.plot(xs, ys, marker=markers[i % len(markers)], color=str(0.1 + 0.75 * i / max(len(families) - 1, 1)), linewidth=1.0, label=fam)
    ax.set_xticks(xs)
    ax.set_xticklabels(["Random", "Task", "Tool", "Policy", "Model"], rotation=20)
    ax.set_ylabel("F1")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(True, axis="y", color="0.85", linewidth=0.6)
    ax.legend(fontsize=6, frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _dataset_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    pos = sum(_label(r) for r in rows)
    return {
        "samples": n,
        "positives": pos,
        "negatives": n - pos,
        "positive_rate": pos / n if n else None,
        "hard_negatives": sum(1 for r in rows if r.get("negative_type") == "hard_negative"),
        "easy_negatives": sum(1 for r in rows if r.get("negative_type") == "easy_negative"),
    }


def _warnings(rows: list[dict[str, Any]], payload: dict[str, Any]) -> list[str]:
    warnings = []
    hard = sum(1 for r in rows if r.get("negative_type") == "hard_negative")
    if hard < 10:
        warnings.append("hard negatives are sparse; predictor evidence remains preliminary")
    if not payload["sklearn_available"]:
        warnings.append("sklearn unavailable; metrics use majority fallback")
    for result in payload["results"]:
        if result["skipped_fold_count"]:
            warnings.append(
                f"{result['feature_family']}:{result['split']} skipped {result['skipped_fold_count']} fold(s)"
            )
    return warnings


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="runs/schema_mutation/predictor_dataset.jsonl")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="accepted for workflow symmetry; output files are overwritten")
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    dataset = Path(args.dataset)
    if not dataset.is_absolute():
        dataset = _REPO_ROOT / dataset
    rows = _read_jsonl(dataset) if dataset.exists() else []
    families = legal_feature_families()
    if args.dry_run:
        print("[predictor-generalization] dry-run")
        print(f"dataset={dataset}")
        print(f"samples={len(rows)}")
        print(f"feature_families={','.join(families)}")
        print(f"splits={','.join(SPLITS)}")
        return 0

    if not rows:
        raise SystemExit(f"dataset missing or empty: {dataset}")
    payload = evaluate(rows, seed=args.seed)
    payload["dataset_path"] = str(dataset)
    payload["dataset"] = _dataset_summary(rows)
    payload["warnings"] = _warnings(rows, payload)

    RUNS.mkdir(parents=True, exist_ok=True)
    table_dir = PAPER / "tables"
    fig_dir = PAPER / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_json = RUNS / "predictor_generalization_summary.json"
    out_md = RUNS / "predictor_generalization_summary.md"
    out_tex = table_dir / "predictor_generalization_auto.tex"
    out_appendix_tex = table_dir / "predictor_generalization_appendix_auto.tex"
    out_pdf = fig_dir / "predictor_split_f1.pdf"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_md(out_md, payload)
    _write_tex(out_tex, payload)
    _write_appendix_tex(out_appendix_tex, payload)
    _write_plot(out_pdf, payload)

    print(f"samples={payload['dataset']['samples']} positives={payload['dataset']['positives']} hard_negatives={payload['dataset']['hard_negatives']}")
    for warning in payload["warnings"][:20]:
        print(f"[warn] {warning}")
    if len(payload["warnings"]) > 20:
        print(f"[warn] ... {len(payload['warnings']) - 20} more warnings")
    print(f"summary_json={out_json}")
    print(f"summary_md={out_md}")
    print(f"summary_tex={out_tex}")
    print(f"appendix_tex={out_appendix_tex}")
    if out_pdf.exists():
        print(f"summary_pdf={out_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
