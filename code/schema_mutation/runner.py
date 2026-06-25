"""hal-harness compatible agent function for schema-mutation experiments.

This module provides ``run(input, **kwargs) -> dict`` matching hal-harness's
``agent_function`` contract (see ``agents/taubench_tool_calling/tool_calling.py``
and ``agents/taubench_example_agent/main.py`` for reference). It also runs as
``__main__`` for a 1-task hello-world without hal-eval CLI.

Wire-up:
    hal-eval --benchmark taubench_retail \
        --agent_dir <ABS_PATH>/learn/code/schema_mutation \
        --agent_function runner.run \
        --agent_name "schema-mut (mimo/mimo-v2-pro,M04)" \
        -A model_name=mimo/mimo-v2-pro \
        -A mutation_type=M04_default_drift \
        -A seed=42 \
        --max_concurrent 1

Model routing (via ``model_name`` prefix):
    mimo/<id>          → MIMO_API_KEY        / MIMO_BASE_URL
    deepseek/<id>      → DEEPSEEK_API_KEY    / DEEPSEEK_BASE_URL
    dashscope/<id>     → DASHSCOPE_API_KEY   / DASHSCOPE_BASE_URL
    siliconflow/<id>   → SILICONFLOW_API_KEY / SILICONFLOW_BASE_URL
    other              → fall through to litellm default

Mutation hook:
    Before running ToolCallingAgent we apply ``apply_mutation`` to one randomly
    selected tool's schema and monkey-patch ``isolated_env.step`` so any tool
    call against the mutated parameter names is reverse-mapped back to the real
    parameters. This mirrors hal-harness's own ``TauBenchPerturbator`` hook
    point but covers semantic mutations (M02-M07/M09/M10) which HAL's surface
    perturbator does not.

Returns dict with:
    {task_id: {
        "reward": ..., "taken_actions": [...], "task": {...},
        "schema_mutation": {
            "tool_name": ..., "mutation_type": ..., "applied": bool,
            "param_remap": {new: old, ...}, "note": ...,
        }
    }}
"""

from __future__ import annotations

import copy
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Bootstrap: make 'code.schema_mutation.*' importable + load learn/.env
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent          # .../learn/code/schema_mutation
_LEARN_ROOT = _THIS_DIR.parent.parent                # .../learn
if str(_LEARN_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEARN_ROOT))

# Load .env from learn/ (so DASHSCOPE_API_KEY etc. work no matter who calls us)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(_LEARN_ROOT / ".env")
except Exception:  # pragma: no cover
    pass

# Our mutator
from code.schema_mutation.mutator import (  # noqa: E402
    apply_mutation,
    MUTATION_TYPES,
    MUTATION_TYPES_V2,
)
from code.schema_mutation.c4_observability_modes import (  # noqa: E402
    generic_error_message,
    level_flags,
    migration_note,
    normalize_observability_level,
    policy_error_message,
    runtime_mode_for_level,
    structured_policy_error_text,
)


# ---------------------------------------------------------------------------
# Model routing
# ---------------------------------------------------------------------------

_PROVIDER_PREFIXES = ("mimo/", "deepseek/", "dashscope/", "siliconflow/", "wyzlab/", "wyzai/")
# No private provider endpoint is shipped in the anonymous artifact. Configure
# optional WYZ-compatible reruns explicitly through environment variables.
_WYZ_DEFAULT_BASE_URL = None


def _resolve_provider(model_name: str) -> tuple[str, Optional[str], Optional[str]]:
    """Return (clean_model_name, api_base, api_key) by prefix routing.

    Anything without a known prefix is returned as-is with (None, None) so
    litellm's default routing kicks in.
    """
    for pfx in _PROVIDER_PREFIXES:
        if model_name.startswith(pfx):
            tag = pfx.rstrip("/").upper()  # e.g. "MIMO"
            if tag in {"WYZLAB", "WYZAI"}:
                # Prefer the new WYZAI_* variables, fall back to the old key
                # variable, and require callers to configure the API base.
                api_key = os.getenv("WYZAI_API_KEY") or os.getenv("WYZLAB_API_KEY")
                api_base = os.getenv("WYZAI_API_BASE") or os.getenv("WYZLAB_API_BASE") or _WYZ_DEFAULT_BASE_URL
            else:
                api_key = os.getenv(f"{tag}_API_KEY")
                api_base = os.getenv(f"{tag}_BASE_URL")
            clean = model_name[len(pfx):]
            if not api_key:
                key_msg = "WYZAI_API_KEY or WYZLAB_API_KEY" if tag in {"WYZLAB", "WYZAI"} else f"{tag}_API_KEY"
                raise RuntimeError(f"{key_msg} not set in env")
            return clean, api_base, api_key
    return model_name, None, None


# ---------------------------------------------------------------------------
# Schema mutation glue (mirrors hal's TauBenchPerturbator hook pattern)
# ---------------------------------------------------------------------------

def _select_target_tool(
    tools_info: list[dict], rng: random.Random
) -> Optional[int]:
    """Pick one tool index whose schema has at least 1 parameter."""
    candidates = []
    for i, t in enumerate(tools_info):
        # tau-bench tools_info follows OpenAI function format:
        #   {"type": "function", "function": {"name": ..., "parameters": {...}}}
        # OR (older versions) flat: {"name": ..., "parameters": {...}}.
        fn = t.get("function", t)
        params = (fn.get("parameters") or {}).get("properties", {})
        if params:
            candidates.append(i)
    if not candidates:
        return None
    return rng.choice(candidates)


def _apply_to_tools_info(
    tools_info: list[dict],
    mutation_type: str,
    seed: int,
    target_tools: Optional[set[str]] = None,
    avoid_tools: Optional[set[str]] = None,
    business_rule_drift: Optional[str] = None,
    observability_level: str = "O2_policy_error",
) -> tuple[list[dict], dict, dict]:
    """Apply our mutation to a selected tool.

    By default, selects a random applicable tool. For exposure-aware testing,
    `target_tools` restricts candidates to baseline-used tools; `avoid_tools`
    implements unused-tool negative control.
    """
    rng = random.Random(seed)
    tools_info = copy.deepcopy(tools_info)
    # Try applicable tools first. Some mutations (e.g. C1 unit drift, B3 enum)
    # only apply when a tool has matching descriptions/enums; picking one random
    # tool can otherwise produce many "skipped" cases.
    candidates = []
    for i, t in enumerate(tools_info):
        fn_i = t.get("function", t)
        name_i = fn_i.get("name", "")
        if target_tools and name_i not in target_tools:
            continue
        if avoid_tools and name_i in avoid_tools:
            continue
        params_i = (fn_i.get("parameters") or {}).get("properties", {})
        if params_i:
            candidates.append(i)
    if not candidates:
        return tools_info, {}, {
            "applied": False,
            "tool_name": None,
            "mutation_type": mutation_type,
            "note": "no candidate tool with parameters after exposure filtering",
            "param_remap": {},
            "target_tools": sorted(target_tools) if target_tools else None,
            "avoid_tools": sorted(avoid_tools) if avoid_tools else None,
        }
    rng.shuffle(candidates)
    expose_migration_note = normalize_observability_level(
        observability_level
    ) == "O4_migration_note"

    # Phase 8C uses C1-C3 as runtime semantic-contract drifts rather than
    # description edits. When an explicit drift is supplied, keep the schema and
    # tool description unchanged and let the step wrapper below provide the
    # hidden oracle / visible feedback. This keeps O0 genuinely silent and
    # schema-invisible.
    if mutation_type in {
        "C1_unit_scale_drift",
        "C2_currency_locale_drift",
        "C3_default_behavior_drift",
    } and business_rule_drift:
        idx = candidates[0]
        target = tools_info[idx]
        fn = target.get("function", target)
        tool_name = fn.get("name", "<unknown>")
        return tools_info, {}, {
            "applied": True,
            "tool_name": tool_name,
            "mutation_type": mutation_type,
            "note": "runtime-only schema-invisible semantic drift",
            "param_remap": {},
            "target_path": "runtime.semantic_contract",
            "before": None,
            "after": business_rule_drift,
            "meta": {
                "runtime_only": True,
                "schema_changed": False,
                "typed_client_compatible": True,
            },
            "target_tools": sorted(target_tools) if target_tools else None,
            "avoid_tools": sorted(avoid_tools) if avoid_tools else None,
            "business_rule_drift": business_rule_drift,
        }

    chosen = None
    for idx in candidates:
        target = tools_info[idx]
        fn = target.get("function", target)
        flat_schema = {
            "name": fn.get("name", "<unknown>"),
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters", {}),
        }
        if mutation_type == "C4_business_rule_drift" and business_rule_drift:
            new_schema, mutation = _apply_c4_with_drift(
                flat_schema,
                business_rule_drift,
                expose_migration_note=expose_migration_note,
            )
        else:
            new_schema, mutation = apply_mutation(flat_schema, mutation_type, seed=seed)
        skipped = (mutation.note or "").lower().startswith("no ")
        if not skipped:
            chosen = (idx, target, fn, flat_schema, new_schema, mutation)
            break

    # If every tool skipped, return the last attempted mutation meta without changing tools.
    if chosen is None:
        return tools_info, {}, {
            "applied": False,
            "tool_name": flat_schema.get("name"),
            "mutation_type": mutation_type,
            "note": mutation.note,
            "param_remap": {},
            "target_path": mutation.target_path,
            "before": mutation.before,
            "after": mutation.after,
            "meta": mutation.meta,
            "target_tools": sorted(target_tools) if target_tools else None,
            "avoid_tools": sorted(avoid_tools) if avoid_tools else None,
        }

    idx, target, fn, flat_schema, new_schema, mutation = chosen

    # Stitch back
    fn["name"] = new_schema.get("name", fn.get("name"))
    fn["description"] = new_schema.get("description", fn.get("description"))
    fn["parameters"] = new_schema.get("parameters", fn.get("parameters"))
    if "function" in target:
        target["function"] = fn
    else:
        target.update(fn)

    # For M01_rename, mutation.before/after are old_name/new_name (str). For
    # other mutation types the rename map is empty (we just track meta).
    param_remap: dict[str, str] = {}
    if (
        mutation.type in ("M01_rename", "A1_identifier_rename")
        and isinstance(mutation.before, str)
        and isinstance(mutation.after, str)
        and mutation.before
        and mutation.after
        and mutation.before != mutation.after
    ):
        param_remap[mutation.after] = mutation.before

    # "applied" = mutation actually changed the schema (skipped notes start
    # with "no ..." or "no parameters" etc.)
    skipped = (mutation.note or "").lower().startswith("no ")
    applied = (not skipped) and bool(mutation.target_path or mutation.before)

    return tools_info, param_remap, {
        "applied": applied,
        "tool_name": flat_schema["name"],
        "mutation_type": mutation_type,
        "note": mutation.note,
        "param_remap": param_remap,
        "target_path": mutation.target_path,
        "before": mutation.before,
        "after": mutation.after,
        "meta": mutation.meta,
        "target_tools": sorted(target_tools) if target_tools else None,
        "avoid_tools": sorted(avoid_tools) if avoid_tools else None,
        "business_rule_drift": business_rule_drift,
    }


def _wrap_step_for_remap(
    isolated_env: Any,
    target_tool_name: str,
    param_remap: dict[str, str],
):
    """Monkey-patch isolated_env.step() to reverse-map param names so the real
    backend still gets old names even though the agent sees new ones.

    Only acts when ``param_remap`` is non-empty (so M02-M10 are pass-through).
    """
    if not param_remap:
        return
    original_step = isolated_env.step

    def patched_step(action):
        try:
            if getattr(action, "name", None) == target_tool_name:
                kwargs = dict(getattr(action, "kwargs", {}) or {})
                if kwargs:
                    new_kwargs = {}
                    for k, v in kwargs.items():
                        new_kwargs[param_remap.get(k, k)] = v
                    action.kwargs = new_kwargs
        except Exception:
            pass  # never break the env loop
        return original_step(action)

    isolated_env.step = patched_step


# ---------------------------------------------------------------------------
# Intent-aligned business-rule drift (C4)
# ---------------------------------------------------------------------------

_INTENT_RULES = {
    "exchange": {
        "keywords": ("exchange",),
        "tools": ("exchange_delivered_order_items",),
        "drift": "exchange policy drift: exchanged items must match both product type and brand; cheapest alternatives are no longer allowed",
    },
    "return": {
        "keywords": ("return", "refund"),
        "tools": ("return_delivered_order_items",),
        "drift": "return policy drift: refund must go to original payment method; cross-order refund methods are no longer allowed",
    },
    "cancel": {
        "keywords": ("cancel",),
        "tools": ("cancel_pending_order", "cancel_reservation"),
        "drift": "cancellation policy drift: cancellations must be refunded to the original payment instrument and require explicit confirmation",
    },
    "address": {
        "keywords": ("address", "delivered", "suite", "shipping"),
        "tools": ("modify_pending_order_address",),
        "drift": "address policy drift: delivery address changes now require postal-code re-verification before update",
    },
    "payment": {
        "keywords": ("payment", "paypal", "credit card", "gift card"),
        "tools": ("modify_pending_order_payment", "return_delivered_order_items"),
        "drift": "payment policy drift: refunds to non-original payment methods require explicit customer confirmation and supervisor approval",
    },
    "modify_order": {
        "keywords": ("size", "material", "boots"),

        "tools": ("modify_pending_order_items",),
        "drift": "order modification policy drift: pending item modifications may change size only; product material changes are no longer allowed",
    },
    "book_flight": {
        "keywords": ("fly", "flight", "book", "reserve", "reservation", "one way", "round trip", "certificate"),
        "tools": ("book_reservation",),
        "drift": "airline booking policy drift: certificate payments can no longer be mixed with cards unless explicitly approved in the booking request",
    },
    "change_flight": {
        "keywords": ("change", "later flight", "earliest flight", "return flight", "downgrade", "upgrade", "modify reservation", "upcoming trip"),

        "tools": ("update_reservation_flights",),
        "drift": "airline change policy drift: flight changes now require an explicit fare-class eligibility check before updating the reservation",
    },

    "baggage": {
        "keywords": ("baggage", "baggages", "checked bag", "checked bags"),
        "tools": ("update_reservation_baggages",),
        "drift": "airline baggage policy drift: baggage updates now require passenger identity verification in the same request",
    },
    "passenger": {
        "keywords": ("change the passenger", "change passenger", "update passenger"),
        "tools": ("update_reservation_passengers",),
        "drift": "airline passenger policy drift: passenger updates now require birthdate verification in the same request",
    },

}



def _infer_task_intent(instruction: str) -> str:
    text = (instruction or "").lower()
    # Priority matters for mixed tasks: specific update intents before generic flight/booking words.
    for intent in (
        "exchange", "modify_order", "passenger", "cancel", "change_flight",
        "book_flight", "baggage", "return", "address", "payment",
    ):





        if any(k in text for k in _INTENT_RULES[intent]["keywords"]):
            return intent
    return "generic"


def _intent_drift(intent: str) -> str:
    if intent in _INTENT_RULES:
        return _INTENT_RULES[intent]["drift"]
    return "business rule drift: task-specific eligibility and confirmation requirements changed without a schema update"


def _intent_for_tool(tool_name: str) -> Optional[str]:
    for intent, spec in _INTENT_RULES.items():
        if tool_name in spec["tools"]:
            return intent
    return None


def _intent_tool_filter(intent: str, tools_info: list[dict], used_tools: Optional[set[str]]) -> Optional[set[str]]:
    if intent not in _INTENT_RULES:
        return used_tools
    patterns = _INTENT_RULES[intent]["tools"]
    available = []
    for t in tools_info:
        fn = t.get("function", t)
        name = fn.get("name", "")
        if any(p in name for p in patterns):
            available.append(name)
    if used_tools:
        exposed = [name for name in available if name in used_tools]
        if exposed:
            return set(exposed)
        return used_tools
    return set(available) if available else None


def _apply_c4_with_drift(
    schema: dict,
    drift: str,
    *,
    expose_migration_note: bool = False,
):
    """Apply an intent-aligned C4 drift with a concrete policy sentence.

    For the observability-gradient experiment, O0-O3 must keep the semantic
    change schema-invisible. Only O4 exposes a migration note before the agent
    acts.
    """
    import copy as _copy
    from code.schema_mutation.mutator import Mutation

    new = _copy.deepcopy(schema)
    new["x-business-rule-change"] = drift
    if expose_migration_note:
        desc = new.get("description", "")
        note = migration_note(new.get("name"), drift)
        new["description"] = (desc + " " + note).strip()
    return new, Mutation(
        "C4_business_rule_drift",
        "x-business-rule-change",
        before=None,
        after=drift,
        note=f"intent-aligned business rule drift: {drift}",
        meta={
            "intent_aligned": True,
            "drift": drift,
            "migration_note_visible": expose_migration_note,
        },
    )


def _business_rule_error(intent: str, action_name: str) -> Optional[str]:
    """Return an error message if this action violates the mutated v2 policy.

    This is the runtime half of C4. Without this, C4 is only a description
    perturbation; with this wrapper, the backend behavior actually changes.
    """
    if intent == "exchange" and "exchange" in action_name:
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Exchange requests now require "
            "the replacement item to match both product type and brand. Cheapest "
            "or cross-brand alternatives are no longer eligible."
        )
    if intent == "return" and "return" in action_name:
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Returns must be refunded to "
            "the original payment method. Cross-order or alternative refund "
            "payment methods are no longer allowed."
        )
    if intent == "cancel" and "cancel" in action_name:
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Cancellations must be "
            "refunded to the original payment instrument and require explicit "
            "customer confirmation under API v2."
        )

    if intent == "address" and "address" in action_name and "modify" in action_name:
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Address changes now require "
            "postal-code re-verification in the same tool call before update."
        )
    if intent == "payment" and "payment" in action_name:
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Non-original payment changes "
            "require explicit customer confirmation and supervisor approval."
        )
    if intent == "modify_order" and "modify_pending_order_items" in action_name:
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Pending item modifications "
            "may change size only; product material or model changes are no longer allowed."
        )
    if intent == "book_flight" and action_name == "book_reservation":
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Certificate payments can no "
            "longer be mixed with cards unless explicitly approved in the booking request."
        )
    if intent == "change_flight" and action_name == "update_reservation_flights":
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Flight changes now require "
            "an explicit fare-class eligibility check before updating the reservation."
        )
    if intent == "baggage" and action_name == "update_reservation_baggages":
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Baggage updates now require "
            "passenger identity verification in the same request."
        )
    if intent == "passenger" and action_name == "update_reservation_passengers":
        return (
            "Error: PolicyUpdate.BusinessRuleDrift: Passenger updates now require "
            "birthdate verification in the same request."
        )
    return None



def _wrap_step_for_business_rules(
    isolated_env: Any,
    intent: Optional[str],
    enabled: bool,
    target_tool_name: Optional[str] = None,
    mode: str = "visible",
    observability_level: str | None = None,
    business_rule_drift: str | None = None,
) -> None:
    """Patch env.step so C4 is a real runtime semantic change.

    Modes are normalized to O0-O4. For O0 the backend response is unchanged
    and a hidden oracle forces reward to zero. For O1-O4 the call is rejected
    with increasingly actionable feedback.
    """
    if not enabled or not intent:
        return

    from tau_bench.types import EnvInfo, EnvResponse

    normalized_level = normalize_observability_level(observability_level, mode)
    normalized_mode = runtime_mode_for_level(normalized_level)

    original_step = isolated_env.step

    def patched_step(action):
        action_name = getattr(action, "name", "")
        if target_tool_name and action_name != target_tool_name:
            return original_step(action)
        msg = _business_rule_error(intent, action_name)
        if not msg and target_tool_name and action_name == target_tool_name and business_rule_drift:
            msg = business_rule_drift
        if msg:
            drift = business_rule_drift or msg
            isolated_env._schema_mut_policy_violation = True
            isolated_env._schema_mut_observability_level = normalized_level
            isolated_env._schema_mut_business_rule_drift = drift
            isolated_env._schema_mut_policy_action = action.name
            isolated_env._schema_mut_policy_action_index = len(isolated_env.actions)
            isolated_env._schema_mut_policy_mode = normalized_mode
            flags = level_flags(normalized_level, violated=True)
            isolated_env._schema_mut_generic_error_visible = flags["generic_error_visible"]
            isolated_env._schema_mut_visible_policy_error = flags["visible_policy_error"]
            isolated_env._schema_mut_structured_policy_error_visible = flags["structured_policy_error_visible"]
            isolated_env._schema_mut_migration_note_visible = flags["migration_note_visible"]
            isolated_env._schema_mut_force_zero = normalized_level == "O0_silent"
            if normalized_mode == "silent":
                isolated_env._schema_mut_policy_error = None
                return original_step(action)

            isolated_env.actions.append(action)
            info = EnvInfo(task=isolated_env.task, source=action.name)
            if normalized_level == "O1_generic_error":
                visible_msg = generic_error_message()
            elif normalized_level == "O2_policy_error":
                visible_msg = policy_error_message(drift)
            else:
                visible_msg = structured_policy_error_text(
                    intent=intent,
                    action_name=action_name,
                    drift=drift,
                )
            isolated_env._schema_mut_policy_error = visible_msg
            return EnvResponse(observation=visible_msg, reward=0, done=False, info=info)
        return original_step(action)

    isolated_env.step = patched_step



# ---------------------------------------------------------------------------
# litellm wiring (subset of hal-harness/agents/taubench_tool_calling pattern)
# ---------------------------------------------------------------------------

def _setup_litellm_routing(
    model_name: str, api_base: Optional[str], api_key: Optional[str]
) -> None:
    """Monkey-patch LiteLLM routing for OpenAI-compatible custom endpoints.

    Important: ``tau_bench.agents.tool_calling_agent`` does
    ``from litellm import completion`` at module import time. In a long-lived
    batch process, that module may already be imported from a previous cell, so
    reassigning ``litellm.completion`` alone is not enough. We also update the
    module-level aliases in tau-bench if present.
    """
    import sys as _sys
    import litellm

    litellm.drop_params = True

    # Keep the true original functions once, otherwise wrappers stack across
    # cells and a qwen wrapper can accidentally capture later deepseek calls.
    if not hasattr(litellm, "_schema_mut_original_completion"):
        litellm._schema_mut_original_completion = litellm.completion
    if not hasattr(litellm, "_schema_mut_original_acompletion"):
        litellm._schema_mut_original_acompletion = litellm.acompletion

    original_completion = litellm._schema_mut_original_completion
    original_acompletion = litellm._schema_mut_original_acompletion

    def _inject(completion_kwargs: dict) -> dict:
        completion_kwargs.setdefault("timeout", int(os.getenv("SCHEMA_MUTATION_LLM_TIMEOUT", "90")))
        # Only inject for the agent model. User simulator models such as
        # dashscope/qwen-flash use native LiteLLM provider routing.
        if api_base and api_key and completion_kwargs.get("model") == model_name:

            completion_kwargs["api_base"] = api_base
            completion_kwargs["api_key"] = api_key
            extra_headers = completion_kwargs.get("extra_headers", {}) or {}
            extra_headers.setdefault("HTTP-Referer", "https://github.com/zhaoxuyang/learn")
            extra_headers.setdefault("X-Title", "schema-mut runner")
            completion_kwargs["extra_headers"] = extra_headers
        return completion_kwargs

    def completion_with_routing(*args, **completion_kwargs):
        completion_kwargs = _inject(completion_kwargs)
        resp = original_completion(*args, **completion_kwargs)
        if hasattr(resp, "_hidden_params") and resp._hidden_params.get(
            "response_cost"
        ) is None:
            resp._hidden_params["response_cost"] = 0.0
        return resp

    async def acompletion_with_routing(*args, **completion_kwargs):
        completion_kwargs = _inject(completion_kwargs)
        resp = await original_acompletion(*args, **completion_kwargs)
        if hasattr(resp, "_hidden_params") and resp._hidden_params.get(
            "response_cost"
        ) is None:
            resp._hidden_params["response_cost"] = 0.0
        return resp

    litellm.completion = completion_with_routing
    litellm.acompletion = acompletion_with_routing

    # Refresh already-imported tau-bench module-level aliases.
    for mod_name in (
        "tau_bench.agents.tool_calling_agent",
        "tau_bench.envs.user",
    ):
        mod = _sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "completion"):
            mod.completion = completion_with_routing


def _append_phase10_nonobviousness_prompt(
    isolated_env: Any,
    *,
    variant: str | None,
    business_rule_drift: str | None,
) -> str | None:
    """Apply Phase 10-only prompt variants without affecting normal runs."""
    if not variant or variant == "standard":
        return None
    current = str(getattr(isolated_env, "wiki", "") or "")
    if variant == "reflection_scaffold":
        scaffold = (
            "\n\nPhase 10 planning scaffold: before committing irreversible tool "
            "actions, check whether the plan depends on unstated assumptions about "
            "units, currency, defaults, eligibility, payment behavior, or policy "
            "constraints. Use only visible tool responses and task evidence to revise "
            "the plan; do not assume a changed external rule unless the API exposes it."
        )
        setattr(isolated_env, "wiki", current + scaffold)
        return "reflection_scaffold"
    if variant == "rule_visible_preamble":
        drift = business_rule_drift or "A semantic API rule has changed; follow the visible migration note."
        scaffold = (
            "\n\nPhase 10 upper-bound migration note: the evolved API rule is: "
            f"{drift} Adjust the workflow before making the affected tool call."
        )
        setattr(isolated_env, "wiki", current + scaffold)
        return "rule_visible_preamble"
    raise ValueError(f"unknown Phase 10 prompt variant: {variant}")


# ---------------------------------------------------------------------------
# Public agent function
# ---------------------------------------------------------------------------

def run(input: dict[str, dict], **kwargs) -> dict[str, Any]:
    """hal-harness agent_function. See module docstring for kwargs.

    Required kwargs:
        model_name: e.g. "mimo/mimo-v2-pro", "dashscope/qwen3.7-max-2026-06-08",
                    "siliconflow/<REDACTED_ORGANIZATION>/Hunyuan-A13B-Instruct"
    Optional kwargs:
        mutation_type: one of MUTATION_TYPES (default: no mutation = baseline)
        seed:          int (default 0)
        temperature:   float (default 0.0)
        env_user_model:    tau-bench user simulator model (default: dashscope/qwen-flash)
        env_user_provider: tau-bench user simulator provider (default: dashscope)
    """
    # HAL validates `-A model_name=...` against an internal pricing dict and
    # exits for custom providers. Accept `agent_model_name` as an alias to avoid
    # that validation path while preserving model_name support for direct use.
    raw_model = kwargs.get("agent_model_name") or kwargs.get("model_name")
    assert raw_model, "model_name or agent_model_name is required"
    model_name, api_base, api_key = _resolve_provider(raw_model)

    mutation_type = kwargs.get("mutation_type")
    seed = int(kwargs.get("seed", 0))
    temperature = float(kwargs.get("temperature", 0.0))
    max_num_steps = int(kwargs.get("max_num_steps", 30))

    # tau-bench user simulator. HAL benchmark hard-codes gpt-4o/openai, but
    # tau-bench itself routes user simulator through LiteLLM, so DashScope works
    # if we override these here.
    env_user_model = kwargs.get(
        "env_user_model",
        os.getenv("SCHEMA_MUTATION_USER_MODEL", "dashscope/qwen-flash"),
    )
    env_user_provider = kwargs.get(
        "env_user_provider",
        os.getenv("SCHEMA_MUTATION_USER_PROVIDER", "dashscope"),
    )

    valid_mutations = set(MUTATION_TYPES) | set(MUTATION_TYPES_V2)
    if mutation_type and mutation_type not in valid_mutations:
        raise ValueError(
            f"unknown mutation_type {mutation_type!r}; "
            f"valid v1: {MUTATION_TYPES}; v2: {MUTATION_TYPES_V2}"
        )

    task_id = list(input.keys())[0]
    task_cfg = input[task_id]

    # 1. Set up litellm routing
    _setup_litellm_routing(model_name, api_base, api_key)

    # 2. Build tau-bench env
    from tau_bench.envs import get_env
    from tau_bench.agents.tool_calling_agent import ToolCallingAgent

    isolated_env = get_env(
        task_cfg["env"],
        task_cfg["user_strategy"],
        env_user_model,
        task_cfg["task_split"],
        env_user_provider,
        task_cfg["task_index"],
    )
    phase10_nonobviousness = kwargs.get("phase10_nonobviousness") in (True, "true", "True", "1")
    agent_prompt_variant = str(kwargs.get("agent_prompt_variant") or "standard")

    # 3. Apply schema mutation to tools_info (if requested)
    tools_info = isolated_env.tools_info
    mutation_meta: dict[str, Any] = {
        "applied": False,
        "mutation_type": mutation_type,
        "tool_name": None,
        "param_remap": {},
        "note": "baseline (no mutation)",
    }
    def _csv_set(value: Any) -> Optional[set[str]]:
        if value is None:
            return None
        if isinstance(value, set):
            return value
        if isinstance(value, (list, tuple)):
            return {str(x).strip() for x in value if str(x).strip()}
        return {x.strip() for x in str(value).split(",") if x.strip()}

    target_tools = _csv_set(kwargs.get("target_tools"))
    avoid_tools = _csv_set(kwargs.get("avoid_tools"))
    explicit_business_rule_intent = kwargs.get("business_rule_intent")
    business_rule_drift = kwargs.get("business_rule_drift")
    task_intent = None
    if explicit_business_rule_intent:
        task_intent = str(explicit_business_rule_intent)
        if business_rule_drift is None:
            business_rule_drift = _intent_drift(task_intent)
    c4_runtime_mode = str(kwargs.get("c4_runtime_mode", "visible"))
    observability_level = normalize_observability_level(
        kwargs.get("observability_level"),
        c4_runtime_mode,
    )
    if kwargs.get("intent_aligned") in (True, "true", "True", "1"):
        instruction = getattr(isolated_env.task, "instruction", "") or ""
        task_intent = _infer_task_intent(instruction)
        business_rule_drift = _intent_drift(task_intent)
        if mutation_type == "C4_business_rule_drift":
            target_tools = _intent_tool_filter(task_intent, tools_info, target_tools)

    if mutation_type:
        tools_info, param_remap, mutation_meta = _apply_to_tools_info(
            tools_info,
            mutation_type,
            seed,
            target_tools=target_tools,
            avoid_tools=avoid_tools,
            business_rule_drift=business_rule_drift,
            observability_level=observability_level,
        )
        if task_intent:
            mutation_meta["task_intent"] = task_intent
        # Reverse-map for runtime
        if mutation_meta.get("tool_name") and param_remap:
            _wrap_step_for_remap(
                isolated_env, mutation_meta["tool_name"], param_remap
            )
        # C-class semantic drifts used in the main observability and Phase 8C
        # experiments must change runtime semantics, not just tool descriptions.
        runtime_semantic_drift = bool(
            mutation_type in {
                "C1_unit_scale_drift",
                "C2_currency_locale_drift",
                "C3_default_behavior_drift",
                "C4_business_rule_drift",
            }
            and (
                kwargs.get("intent_aligned") in (True, "true", "True", "1")
                or explicit_business_rule_intent
                or business_rule_drift
            )
        )
        if runtime_semantic_drift:
            _wrap_step_for_business_rules(
                isolated_env,
                task_intent,
                enabled=True,
                target_tool_name=mutation_meta.get("tool_name"),
                mode=c4_runtime_mode,
                observability_level=observability_level,
                business_rule_drift=business_rule_drift,
            )
            mutation_meta["runtime_semantics_changed"] = True
            mutation_meta["c4_runtime_mode"] = c4_runtime_mode
            mutation_meta["observability_level"] = observability_level

    scaffold_type = None
    if phase10_nonobviousness:
        scaffold_type = _append_phase10_nonobviousness_prompt(
            isolated_env,
            variant=agent_prompt_variant,
            business_rule_drift=business_rule_drift,
        )

    # 4. Run agent
    agent = ToolCallingAgent(
        tools_info=tools_info,
        wiki=isolated_env.wiki,
        model=model_name,
        provider="openai",  # always 'openai' since we route via api_base
        temperature=temperature,
    )
    t0 = time.time()
    output = agent.solve(
        isolated_env,
        task_index=task_cfg["task_index"],
        max_num_steps=max_num_steps,
    )

    elapsed = time.time() - t0

    oracle_rule_violation = bool(
        getattr(isolated_env, "_schema_mut_policy_violation", False)
    )
    policy_mode = getattr(isolated_env, "_schema_mut_policy_mode", None)
    result_observability_level = getattr(
        isolated_env, "_schema_mut_observability_level", observability_level
    )
    flags = level_flags(result_observability_level, oracle_rule_violation)
    visible_policy_error = bool(
        getattr(
            isolated_env,
            "_schema_mut_visible_policy_error",
            flags["visible_policy_error"],
        )
    )
    generic_error_visible = bool(
        getattr(
            isolated_env,
            "_schema_mut_generic_error_visible",
            flags["generic_error_visible"],
        )
    )
    structured_policy_error_visible = bool(
        getattr(
            isolated_env,
            "_schema_mut_structured_policy_error_visible",
            flags["structured_policy_error_visible"],
        )
    )
    migration_note_visible = bool(
        getattr(
            isolated_env,
            "_schema_mut_migration_note_visible",
            flags["migration_note_visible"],
        )
    )
    hidden_business_rule_violation = bool(flags["hidden_business_rule_violation"])
    final_reward = float(

        getattr(isolated_env, "reward", getattr(output, "reward", 0.0)) or 0.0
    )
    if getattr(isolated_env, "_schema_mut_force_zero", False):
        final_reward = 0.0
    violation_index = getattr(isolated_env, "_schema_mut_policy_action_index", None)
    recovery_attempted = False
    if oracle_rule_violation and violation_index is not None:
        # Conservative heuristic: only count recovery when the agent receives an
        # observable signal and then takes at least one subsequent action.
        recovery_attempted = bool(
            (visible_policy_error or migration_note_visible)
            and len(isolated_env.actions) > int(violation_index) + 1
        )
    recovery_success = bool(recovery_attempted and final_reward > 0)

    if final_reward > 0:
        failure_mode = "agent_compatible"
    elif hidden_business_rule_violation:
        failure_mode = "silent_failure"
    elif migration_note_visible and oracle_rule_violation:
        failure_mode = "migration_note_ignored"
    elif structured_policy_error_visible and oracle_rule_violation:
        failure_mode = "structured_recovery_failure"
    elif generic_error_visible and oracle_rule_violation:
        failure_mode = "generic_error_unrecovered"
    elif visible_policy_error and oracle_rule_violation:
        failure_mode = "policy_recovery_failure"
    elif mutation_type:
        failure_mode = "mutation_task_failure"
    else:
        failure_mode = "baseline_task_failure"

    # 5. Pack result in hal-harness expected shape
    result = {
        task_id: {
            "reward": final_reward,

            "taken_actions": [a.model_dump() for a in isolated_env.actions],
            "task": isolated_env.task.model_dump(),
            "schema_mutation": mutation_meta,
            "wallclock_s": round(elapsed, 2),
            "raw_model_name": raw_model,
            "observability_level": result_observability_level,
            "c4_runtime_mode": c4_runtime_mode,
            "target_policy": kwargs.get("target_policy"),
            "phase10_nonobviousness": phase10_nonobviousness,
            "agent_prompt_variant": agent_prompt_variant,
            "scaffold_type": scaffold_type,
            "target_tool": mutation_meta.get("tool_name"),
            "intent_aligned": bool(task_intent),
            "oracle_rule_violation": oracle_rule_violation,
            "visible_policy_error": visible_policy_error,
            "generic_error_visible": generic_error_visible,
            "structured_policy_error_visible": structured_policy_error_visible,
            "migration_note_visible": migration_note_visible,
            "hidden_business_rule_violation": hidden_business_rule_violation,
            "recovery_attempted": recovery_attempted,
            "recovery_success": recovery_success,
            "final_reward": final_reward,
            "failure_mode": failure_mode,
            "oracle_rule_error": getattr(
                isolated_env, "_schema_mut_policy_error", None
            ),
            "oracle_rule_action": getattr(
                isolated_env, "_schema_mut_policy_action", None
            ),
            "oracle_rule_mode": policy_mode,
            "oracle_force_zero": getattr(
                isolated_env, "_schema_mut_force_zero", False
            ),
            "runtime_policy_violation": oracle_rule_violation,
            "runtime_policy_error": getattr(
                isolated_env, "_schema_mut_policy_error", None
            ),
            "runtime_policy_action": getattr(
                isolated_env, "_schema_mut_policy_action", None
            ),
            "runtime_policy_mode": policy_mode,
            "runtime_policy_force_zero": getattr(
                isolated_env, "_schema_mut_force_zero", False
            ),



        }
    }
    return result


# ---------------------------------------------------------------------------
# __main__: 1-task hello world (no hal-eval CLI)
# ---------------------------------------------------------------------------

def _hello_world(model_name: str, mutation_type: Optional[str] = None,
                 task_index: int = 0) -> None:
    """Run a single τ-retail task end-to-end. Prints reward + mutation meta."""
    cfg = {
        "env": "retail",
            "user_strategy": "llm",
            "user_model": "dashscope/qwen-flash",  # overridden by run() kwargs/env
            "task_split": "test",
            "user_provider": "dashscope",
        "task_index": task_index,
    }
    out = run({f"task_{task_index}": cfg},
              model_name=model_name,
              mutation_type=mutation_type,
              seed=42,
              temperature=0.0)
    rec = out[f"task_{task_index}"]
    print("=" * 60)
    print(f"model:    {rec['raw_model_name']}")
    print(f"mutation: {mutation_type or 'NONE (baseline)'}")
    print(f"reward:   {rec['reward']}")
    print(f"actions:  {len(rec['taken_actions'])}")
    print(f"time:     {rec['wallclock_s']}s")
    print(f"schema_mutation: {rec['schema_mutation']}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--model_name", default="mimo/mimo-v2-pro",
                   help="prefix routes: mimo/ deepseek/ dashscope/ siliconflow/")
    p.add_argument("--mutation_type", default=None,
                   help=f"one of {MUTATION_TYPES} or omit for baseline")
    p.add_argument("--task_index", type=int, default=0)
    args = p.parse_args()

    _hello_world(args.model_name, args.mutation_type, args.task_index)
