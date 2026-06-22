"""Generalization splits for predictor evaluation."""

from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from typing import Any


SPLITS = [
    "random_split",
    "leave_task_out",
    "leave_tool_out",
    "leave_policy_out",
    "leave_model_out",
    "leave_env_out",
]


def split_key(row: dict[str, Any], split: str) -> str:
    if split == "leave_task_out":
        return str(row.get("task_id", "unknown"))
    if split == "leave_tool_out":
        return str(row.get("target_tool", "unknown"))
    if split == "leave_policy_out":
        return str(row.get("target_policy", "unknown"))
    if split == "leave_model_out":
        return str(row.get("model", "unknown"))
    if split == "leave_env_out":
        return str(row.get("env", "unknown"))
    raise ValueError(f"not a grouped split: {split}")


def grouped_folds(rows: list[dict[str, Any]], split: str) -> list[tuple[list[int], list[int], str]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        groups[split_key(row, split)].append(i)
    folds = []
    for key, test_idx in sorted(groups.items()):
        train_idx = [i for i in range(len(rows)) if i not in set(test_idx)]
        folds.append((train_idx, test_idx, key))
    return folds


def random_folds(rows: list[dict[str, Any]], seed: int = 7, folds: int = 5) -> list[tuple[list[int], list[int], str]]:
    indices = list(range(len(rows)))
    indices.sort(key=lambda i: _stable_hash((rows[i].get("sample_id"), seed)))
    rng = random.Random(seed)
    rng.shuffle(indices)
    k = max(2, min(folds, len(indices)))
    buckets = [indices[i::k] for i in range(k)]
    out = []
    all_idx = set(indices)
    for j, test_idx in enumerate(buckets):
        if not test_idx:
            continue
        test_set = set(test_idx)
        train_idx = sorted(all_idx - test_set)
        out.append((train_idx, sorted(test_idx), f"fold_{j}"))
    return out


def make_folds(rows: list[dict[str, Any]], split: str, seed: int = 7) -> list[tuple[list[int], list[int], str]]:
    if split == "random_split":
        return random_folds(rows, seed=seed)
    if split in SPLITS:
        return grouped_folds(rows, split)
    raise ValueError(f"unknown split: {split}")


def _stable_hash(parts: tuple[Any, ...]) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
