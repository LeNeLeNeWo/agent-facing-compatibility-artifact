"""Legacy minimal exposure-aware breakage predictor for paired mutation results.

This is a paper-pilot analysis, not a production ML model. It compares whether
API-diff-only features are less predictive than exposure/semantic-aware features.

Phase 3 uses ``build_prediction_dataset.py`` and
``evaluate_predictor_generalization.py`` instead. Those scripts add hard
negatives, observability and trajectory features, leakage checks, and
leave-task/tool/policy/model generalization splits.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any, Iterable

from code.schema_mutation.compatibility_labels import _mutation_v2
from code.schema_mutation.mutator import ATTRIBUTE_MATRIX


FeatureSet = tuple[str, ...]


FEATURE_SETS: dict[str, FeatureSet] = {
    "majority": (),
    "mutation_class_only": ("mutation_type_v2",),
    "schema_diff_only": ("schema_visible", "traditional_compatible"),
    "semantic_only": ("semantics_changing", "agent_silent", "recoverable_via_error"),
    "exposure_only": ("target_policy", "c4_runtime_mode", "intent_aligned", "tool_family"),
    "schema_plus_exposure": (
        "schema_visible",
        "traditional_compatible",
        "target_policy",
        "c4_runtime_mode",
        "intent_aligned",
        "tool_family",
    ),
    "semantic_plus_exposure": (
        "semantics_changing",
        "agent_silent",
        "recoverable_via_error",
        "target_policy",
        "c4_runtime_mode",
        "intent_aligned",
        "tool_family",
    ),
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _tool_family(name: Any) -> str:
    s = str(name or "unknown")
    for key in ("exchange", "return", "cancel", "modify", "payment", "address", "order", "product", "user"):
        if key in s:
            return key
    return s.split("_")[0] if s else "unknown"


def _truth(row: dict[str, Any]) -> int:
    if row.get("agent_bucket") == "agent_breaking":
        return 1
    return 1 if float(row.get("delta") or 0.0) > 0 else 0


def _value(row: dict[str, Any], feature: str) -> str:
    mt = _mutation_v2(row.get("mutation_type_v2") or row.get("mutation_type"))
    attrs = row.get("attrs") or ATTRIBUTE_MATRIX.get(mt, {})
    if feature == "mutation_type_v2":
        return mt
    if feature in attrs:
        return str(attrs.get(feature, "?"))
    if feature == "tool_family":
        return _tool_family(row.get("mutation_tool"))
    if feature == "intent_aligned":
        meta = row.get("mutation_meta") or {}
        return str(row.get("intent_aligned") or meta.get("intent_aligned") or row.get("target_policy") in {"intent_aligned", "random_intent_aligned", "unused_intent_aligned"})
    return str(row.get(feature, "?"))


def _key(row: dict[str, Any], features: FeatureSet) -> tuple[str, ...]:
    return tuple(_value(row, f) for f in features)


def _majority(rows: Iterable[dict[str, Any]]) -> int:
    ys = [_truth(r) for r in rows]
    if not ys:
        return 0
    return 1 if sum(ys) >= len(ys) / 2 else 0


def _fit_predict(train: list[dict[str, Any]], test: list[dict[str, Any]], features: FeatureSet) -> list[int]:
    default = _majority(train)
    if not features:
        return [default for _ in test]
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in train:
        groups[_key(r, features)].append(r)
    preds = []
    for r in test:
        rows = groups.get(_key(r, features))
        preds.append(_majority(rows) if rows else default)
    return preds


def _metrics(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    tp = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(y_true, y_pred) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, y_pred) if y == 1 and p == 0)
    n = len(y_true) or 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "acc": (tp + tn) / n,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "balanced_acc": (recall + specificity) / 2,
        "tp": float(tp),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
    }


def evaluate(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    tasks = sorted({r.get("task_index") for r in rows})
    out: dict[str, dict[str, float]] = {}
    for name, features in FEATURE_SETS.items():
        y_true: list[int] = []
        y_pred: list[int] = []
        for task in tasks:
            train = [r for r in rows if r.get("task_index") != task]
            test = [r for r in rows if r.get("task_index") == task]
            if not train or not test:
                continue
            y_true.extend(_truth(r) for r in test)
            y_pred.extend(_fit_predict(train, test, features))
        out[name] = _metrics(y_true, y_pred)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl", nargs="+", help="paired/labeled JSONL files")
    p.add_argument("--out", default=None, help="optional JSON metrics output")
    args = p.parse_args()

    rows: list[dict[str, Any]] = []
    for path_s in args.jsonl:
        rows.extend(_load_jsonl(Path(path_s)))
    rows = [r for r in rows if (r.get("mutation_type") or r.get("mutation_type_v2"))]

    metrics = evaluate(rows)
    print(f"records={len(rows)} tasks={len(set(r.get('task_index') for r in rows))}")
    print("model\tacc\tbal_acc\tprecision\trecall\tf1\ttp\ttn\tfp\tfn")
    for name, m in metrics.items():
        print(
            f"{name}\t{m['acc']:.3f}\t{m['balanced_acc']:.3f}\t{m['precision']:.3f}\t"
            f"{m['recall']:.3f}\t{m['f1']:.3f}\t{int(m['tp'])}\t{int(m['tn'])}\t{int(m['fp'])}\t{int(m['fn'])}"
        )

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"written={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
