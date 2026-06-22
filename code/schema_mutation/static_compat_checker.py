"""Static schema/typed-client compatibility baseline for mutation classes.

This approximates what schema-diff or generated-client checks would catch before
running an LLM agent. It intentionally ignores natural-language descriptions and
vendor extension fields such as x-business-rule-change.
"""

from __future__ import annotations

import argparse
import collections
import copy
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.schema_mutation.mutator import ATTRIBUTE_MATRIX, MUTATION_TYPES_V2  # noqa: E402
from code.schema_mutation.runner import _apply_to_tools_info  # noqa: E402
from code.schema_mutation.gate_policies import classify_static_compat  # noqa: E402


def static_compat_for_mutation(mutation_type: str | None) -> dict[str, Any]:
    """Cheap mutation-class compatibility estimate for gate evaluation.

    This is intentionally conservative and does not inspect natural-language
    descriptions or x-business-rule-change. It is suitable for the
    SchemaCheckerOnly baseline and as one AFC-Gate feature.
    """
    res = classify_static_compat(mutation_type)
    return {
        "mutation_type": mutation_type,
        "schema_checker_pass": res.schema_checker_pass,
        "typed_client_checker_pass": res.typed_client_checker_pass,
        "reasons": list(res.reasons),
    }


def _sig(tool: dict[str, Any]) -> dict[str, Any]:
    fn = tool.get("function", tool)
    params = fn.get("parameters", {}) or {}
    props = params.get("properties", {}) or {}
    return {
        "name": fn.get("name"),
        "required": sorted(params.get("required", []) or []),
        "props": {
            k: {
                "type": v.get("type"),
                "enum": tuple(v.get("enum", []) or []),
                "items_type": (v.get("items") or {}).get("type"),
            }
            for k, v in sorted(props.items())
        },
    }


def _nonsemantic_schema(tool: dict[str, Any]) -> dict[str, Any]:
    fn = tool.get("function", tool)
    return {
        "name": fn.get("name"),
        "parameters": _sig(tool),
    }


def _compare(before: dict[str, Any], after: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    b_sig = _sig(before)
    a_sig = _sig(after)
    reasons = []
    if b_sig["name"] != a_sig["name"]:
        reasons.append("function_name")
    if set(b_sig["props"]) != set(a_sig["props"]):
        reasons.append("param_names")
    if b_sig["required"] != a_sig["required"]:
        reasons.append("required")
    common = set(b_sig["props"]) & set(a_sig["props"])
    for p in sorted(common):
        if b_sig["props"][p] != a_sig["props"][p]:
            reasons.append(f"param_contract:{p}")
    schema_checker_detects = _nonsemantic_schema(before) != _nonsemantic_schema(after)
    typed_client_breaks = bool(reasons)
    return schema_checker_detects, typed_client_breaks, reasons


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task", type=int, default=0)
    p.add_argument("--seeds", default="0,1,2")
    p.add_argument("--mutations", default=",".join(MUTATION_TYPES_V2))
    p.add_argument("--out", default="runs/schema_mutation/day10_static_compat_checker.jsonl")
    args = p.parse_args()

    from tau_bench.envs import get_env

    env = get_env("retail", "llm", "dashscope/qwen-flash", "test", "dashscope", args.task)
    tools_info = env.tools_info
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    mutations = [x.strip() for x in args.mutations.split(",") if x.strip()]
    out = Path(args.out)
    if not out.is_absolute():
        out = _REPO_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for mutation in mutations:
        for seed in seeds:
            before_tools = copy.deepcopy(tools_info)
            after_tools, _, meta = _apply_to_tools_info(before_tools, mutation, seed)
            tool_name = meta.get("tool_name")
            before = next((t for t in tools_info if (t.get("function", t)).get("name") == tool_name), None)
            after = next((t for t in after_tools if (t.get("function", t)).get("name") == tool_name), None)
            if before is None or after is None:
                continue
            schema_detects, typed_breaks, reasons = _compare(before, after)
            rows.append(
                {
                    "mutation_type": mutation,
                    "seed": seed,
                    "tool_name": tool_name,
                    "mutation_applied": meta.get("applied"),
                    "schema_checker_detects": schema_detects,
                    "typed_client_breaks": typed_breaks,
                    "reasons": reasons,
                    "attrs": ATTRIBUTE_MATRIX.get(mutation, {}),
                    "mutation_note": meta.get("note"),
                }
            )

    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_mut: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        by_mut[r["mutation_type"]].append(r)
    print(f"written={out} records={len(rows)}")
    print("mutation\tn\tschema_detect_rate\ttyped_break_rate\treasons")
    for mt in mutations:
        rs = by_mut.get(mt, [])
        if not rs:
            continue
        sd = sum(1 for r in rs if r["schema_checker_detects"]) / len(rs)
        tb = sum(1 for r in rs if r["typed_client_breaks"]) / len(rs)
        reasons = sorted({reason for r in rs for reason in r["reasons"]})
        print(f"{mt}\t{len(rs)}\t{sd:.3f}\t{tb:.3f}\t{','.join(reasons) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
