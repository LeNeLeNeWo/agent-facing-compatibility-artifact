"""10 schema mutation classes (M01-M10) for the schema-evolution project.

A "tool schema" here follows the OpenAI function-calling / JSON Schema
convention used by τ-bench, hal-harness, and most agent frameworks:

    {
        "name": "search_flight",
        "description": "Search flights between two cities.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_city": {"type": "string",
                              "description": "Origin city (English name)."},
                "to_city":   {"type": "string",
                              "description": "Destination city."},
                "date":      {"type": "string",
                              "description": "YYYY-MM-DD format."},
                "budget":    {"type": "number",
                              "description": "Maximum budget in USD."}
            },
            "required": ["from_city", "to_city", "date"]
        }
    }

Each mutation takes such a schema and returns (mutated_schema, mutation_meta).
Where mutation_meta records the exact change for reproducibility and for
later compatibility-predictor training.

Usage:
    from code.schema_mutation.mutator import apply_mutation
    new_schema, meta = apply_mutation(orig_schema, "M01_rename", rng=...)
"""

from __future__ import annotations

import copy
import random
import re
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass
class Mutation:
    """Records what mutation was applied; used downstream for
    predictor features and reproducibility."""
    type: str                       # "M01_rename" .. "M10_pagination"
    target_path: str                # e.g. "parameters.properties.from_city"
    before: Any = None              # original value/snippet
    after: Any = None               # mutated value/snippet
    note: str = ""                  # human-readable explanation
    meta: dict = field(default_factory=dict)


MUTATION_TYPES = [
    "M01_rename",
    "M02_type_change",
    "M03_requiredness",
    "M04_default_semantic_drift",
    "M05_unit_change",
    "M06_enum_rename",
    "M07_description_paraphrase",
    "M08_error_format",
    "M09_permission_change",
    "M10_pagination_change",
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _get_props(schema: dict) -> dict:
    """Return the parameters.properties dict of a tool schema."""
    return schema.get("parameters", {}).get("properties", {})


def _get_required(schema: dict) -> list:
    return schema.get("parameters", {}).get("required", [])


def _set_required(schema: dict, required: list) -> None:
    schema.setdefault("parameters", {})["required"] = required


# ---------------------------------------------------------------------------
# M01 · Identifier rename (synonym)
# ---------------------------------------------------------------------------

_RENAME_DICT = {
    "from_city": "origin", "to_city": "destination",
    "user_id": "uid", "user_name": "username",
    "start_time": "begin_at", "end_time": "finish_at",
    "phone_number": "phoneNumber", "email_address": "email",
    "amount": "value", "budget": "max_cost",
    "date": "scheduled_date", "status": "state",
    "id": "identifier", "name": "title",
}


def _m01_rename(schema: dict, rng: random.Random) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    props = _get_props(new)
    if not props:
        return new, Mutation("M01_rename", "", note="no parameters; skipped")

    # Pick a parameter that has a known synonym, or just use parameter[0]
    candidates = [k for k in props if k in _RENAME_DICT] or list(props)[:1]
    old_name = rng.choice(candidates)
    new_name = _RENAME_DICT.get(old_name, old_name + "_v2")

    props[new_name] = props.pop(old_name)
    req = _get_required(new)
    if old_name in req:
        req[req.index(old_name)] = new_name

    return new, Mutation(
        "M01_rename",
        f"parameters.properties.{old_name}",
        before=old_name, after=new_name,
        note=f"renamed parameter '{old_name}' -> '{new_name}'",
    )


# ---------------------------------------------------------------------------
# M02 · Type / format change
# ---------------------------------------------------------------------------

_TYPE_FLIPS = {
    "string": "integer",        # date: "YYYY-MM-DD" -> unix timestamp
    "integer": "string",
    "number": "string",
    "boolean": "string",        # true -> "true"
}


def _m02_type_change(schema: dict, rng: random.Random) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    props = _get_props(new)
    candidates = [k for k, v in props.items() if v.get("type") in _TYPE_FLIPS]
    if not candidates:
        return new, Mutation("M02_type_change", "", note="no flippable type")

    target = rng.choice(candidates)
    old_t = props[target]["type"]
    new_t = _TYPE_FLIPS[old_t]
    props[target]["type"] = new_t

    return new, Mutation(
        "M02_type_change",
        f"parameters.properties.{target}.type",
        before=old_t, after=new_t,
        note=f"flipped type of '{target}' from {old_t} to {new_t}",
    )


# ---------------------------------------------------------------------------
# M03 · Requiredness change (optional → required)
# ---------------------------------------------------------------------------

def _m03_requiredness(schema: dict, rng: random.Random) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    props = _get_props(new)
    req = _get_required(new)
    optional = [k for k in props if k not in req]
    if not optional:
        return new, Mutation("M03_requiredness", "",
                             note="no optional parameter")

    target = rng.choice(optional)
    new_req = req + [target]
    _set_required(new, new_req)

    return new, Mutation(
        "M03_requiredness",
        f"parameters.required (+{target})",
        before=req, after=new_req,
        note=f"made '{target}' required",
    )


# ---------------------------------------------------------------------------
# M04 · Default value semantic drift (description-only change)
# ---------------------------------------------------------------------------

_DEFAULT_DRIFTS = [
    ("USD", "CNY"), ("US dollars", "Chinese yuan"),
    ("UTC", "local time"), ("Beijing time", "UTC"),
    ("ascending", "descending"), ("inclusive", "exclusive"),
    ("kilometers", "miles"), ("Celsius", "Fahrenheit"),
]


def _m04_default_drift(schema: dict, rng: random.Random) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    props = _get_props(new)
    for key, prop in props.items():
        desc = prop.get("description", "")
        for old_v, new_v in _DEFAULT_DRIFTS:
            if old_v.lower() in desc.lower():
                prop["description"] = re.sub(
                    re.escape(old_v), new_v, desc, flags=re.IGNORECASE,
                )
                return new, Mutation(
                    "M04_default_semantic_drift",
                    f"parameters.properties.{key}.description",
                    before=old_v, after=new_v,
                    note=f"semantic drift in '{key}' description: "
                         f"'{old_v}' -> '{new_v}' (schema unchanged)",
                )
    # Fallback: append a misleading default note
    if props:
        target = rng.choice(list(props))
        prop = props[target]
        old_desc = prop.get("description", "")
        prop["description"] = old_desc + " (Note: default unit changed to CNY.)"
        return new, Mutation(
            "M04_default_semantic_drift",
            f"parameters.properties.{target}.description",
            before=old_desc, after=prop["description"],
            note="appended misleading default-unit note",
        )
    return new, Mutation("M04_default_semantic_drift", "",
                         note="no parameters")


# ---------------------------------------------------------------------------
# M05 · Unit / scale change (in description only)
# ---------------------------------------------------------------------------

_UNIT_FLIPS = [
    ("seconds", "milliseconds"), ("milliseconds", "microseconds"),
    ("MB", "GB"), ("KB", "MB"),
    ("bytes", "bits"), ("USD", "cents"),
]


def _m05_unit_change(schema: dict, rng: random.Random) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    props = _get_props(new)
    for key, prop in props.items():
        desc = prop.get("description", "")
        for old_u, new_u in _UNIT_FLIPS:
            if old_u in desc:
                prop["description"] = desc.replace(old_u, new_u)
                return new, Mutation(
                    "M05_unit_change",
                    f"parameters.properties.{key}.description",
                    before=old_u, after=new_u,
                    note=f"unit drift in '{key}': {old_u} -> {new_u}",
                )
    # Fallback: if no explicit unit exists, append a unit note to a numeric-like
    # parameter. Real production APIs often leave units only in docs/changelogs;
    # this fallback makes C1 applicable to τ-bench tools whose descriptions are
    # sparse.
    numeric_candidates = []
    for k, p in props.items():
        desc = str(p.get("description", "")).lower()
        key = k.lower()
        if (
            p.get("type") in ("number", "integer")
            or any(tok in key for tok in ("amount", "price", "cost", "fee", "total", "balance", "payment"))
            or any(tok in desc for tok in ("amount", "price", "cost", "fee", "total", "balance", "payment", "refund"))
        ):
            numeric_candidates.append(k)
    if numeric_candidates:
        target = rng.choice(numeric_candidates)
        prop = props[target]
        old_desc = prop.get("description", "")
        prop["description"] = (old_desc + " (Unit changed from USD to cents.)").strip()
        return new, Mutation(
            "M05_unit_change",
            f"parameters.properties.{target}.description",
            before="USD", after="cents",
            note=f"unit drift fallback in '{target}': USD -> cents",
            meta={"fallback": True},
        )
    return new, Mutation("M05_unit_change", "",
                         note="no convertible unit string found")


# ---------------------------------------------------------------------------
# M06 · Enum value rename
# ---------------------------------------------------------------------------

_ENUM_RENAMES = {
    "pending": "queued", "done": "completed",
    "active": "running", "inactive": "paused",
    "open": "available", "closed": "unavailable",
    "yes": "true", "no": "false",
}


def _m06_enum_rename(schema: dict, rng: random.Random) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    props = _get_props(new)
    for key, prop in props.items():
        enum_vals = prop.get("enum")
        if not enum_vals:
            continue
        renamed = []
        changed = False
        for v in enum_vals:
            new_v = _ENUM_RENAMES.get(str(v).lower(), v)
            if new_v != v:
                changed = True
            renamed.append(new_v)
        if changed:
            prop["enum"] = renamed
            return new, Mutation(
                "M06_enum_rename",
                f"parameters.properties.{key}.enum",
                before=enum_vals, after=renamed,
                note=f"renamed enum values for '{key}'",
            )
    return new, Mutation("M06_enum_rename", "",
                         note="no renamable enum found")


# ---------------------------------------------------------------------------
# M07 · Description paraphrase (semantically equivalent rewrite)
# ---------------------------------------------------------------------------

_PARAPHRASE_TEMPLATES = [
    "{} (Refactored documentation.)",
    "Updated description: {}",
    "{} See documentation for details.",
]


def _m07_description_paraphrase(schema: dict, rng: random.Random
                                ) -> tuple[dict, Mutation]:
    """Cheap deterministic paraphrase. Production version should use
    LLM-based paraphrase (Day-2 enhancement)."""
    new = copy.deepcopy(schema)
    props = _get_props(new)
    if not props:
        return new, Mutation("M07_description_paraphrase", "")

    target = rng.choice(list(props))
    prop = props[target]
    old_desc = prop.get("description", "")
    if not old_desc:
        return new, Mutation("M07_description_paraphrase",
                             f"parameters.properties.{target}.description",
                             note="no description to paraphrase")

    template = rng.choice(_PARAPHRASE_TEMPLATES)
    new_desc = template.format(old_desc)
    prop["description"] = new_desc

    return new, Mutation(
        "M07_description_paraphrase",
        f"parameters.properties.{target}.description",
        before=old_desc, after=new_desc,
        note=f"paraphrased description of '{target}'",
    )


# ---------------------------------------------------------------------------
# M08 · Error format change (recorded as schema metadata; runner enforces)
# ---------------------------------------------------------------------------

def _m08_error_format(schema: dict, rng: random.Random) -> tuple[dict, Mutation]:
    """We attach a non-standard 'x-error-format' hint to the schema; the
    runner is expected to wrap tool errors in this new format."""
    new = copy.deepcopy(schema)
    new["x-error-format"] = {
        "before": {"error": "<msg>"},
        "after": {"err_msg": "<msg>", "code": 400},
    }
    return new, Mutation(
        "M08_error_format", "x-error-format",
        before={"error": "<msg>"},
        after={"err_msg": "<msg>", "code": 400},
        note="error envelope changed; runner must wrap actual tool errors",
    )


# ---------------------------------------------------------------------------
# M09 · Permission / rate-limit change
# ---------------------------------------------------------------------------

def _m09_permission_change(schema: dict, rng: random.Random
                           ) -> tuple[dict, Mutation]:
    """Adds a precondition: must call `auth_token` first. Runner is expected
    to reject calls until the precondition is satisfied."""
    new = copy.deepcopy(schema)
    new["x-precondition"] = "auth_token must be obtained first"
    desc = new.get("description", "")
    new["description"] = (
        desc + " (NOTE: this tool now requires a valid auth_token "
        "obtained via the auth_token tool.)"
    )
    return new, Mutation(
        "M09_permission_change", "x-precondition",
        before=None, after="auth_token required",
        note="added auth_token precondition",
    )


# ---------------------------------------------------------------------------
# M10 · Pagination / partial response
# ---------------------------------------------------------------------------

def _m10_pagination_change(schema: dict, rng: random.Random
                           ) -> tuple[dict, Mutation]:
    """Marks the tool's return shape as paginated; runner truncates and
    appends a cursor."""
    new = copy.deepcopy(schema)
    new["x-response-shape"] = {
        "before": "results: list",
        "after": {"results": "list", "cursor": "string|null",
                  "has_more": "bool"},
    }
    return new, Mutation(
        "M10_pagination_change", "x-response-shape",
        before="flat list",
        after="{results, cursor, has_more}",
        note="response now paginated; agent must follow cursor",
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_DISPATCH = {
    "M01_rename":                  _m01_rename,
    "M02_type_change":             _m02_type_change,
    "M03_requiredness":            _m03_requiredness,
    "M04_default_semantic_drift":  _m04_default_drift,
    "M05_unit_change":             _m05_unit_change,
    "M06_enum_rename":             _m06_enum_rename,
    "M07_description_paraphrase":  _m07_description_paraphrase,
    "M08_error_format":            _m08_error_format,
    "M09_permission_change":       _m09_permission_change,
    "M10_pagination_change":       _m10_pagination_change,
}


def apply_mutation(
    tool_schema: dict,
    mutation_type: str,
    seed: Optional[int] = None,
) -> tuple[dict, Mutation]:
    """Apply a mutation by type name.

    Accepts both legacy names (M01_rename..M10_pagination_change) and
    v2 names (A1_identifier_rename..D4_rate_limit_change). The v2 names
    are recommended; legacy names are kept for backward compatibility
    with the original 10-class taxonomy.
    """
    if mutation_type in _DISPATCH:
        rng = random.Random(seed)
        return _DISPATCH[mutation_type](tool_schema, rng)
    if mutation_type in _V2_DISPATCH:
        rng = random.Random(seed)
        new_schema, mutation = _V2_DISPATCH[mutation_type](tool_schema, rng)
        # standardize Mutation.type to the v2 label
        mutation.type = mutation_type
        return new_schema, mutation
    raise ValueError(
        f"Unknown mutation_type {mutation_type!r}; "
        f"valid v1: {MUTATION_TYPES} | v2: {MUTATION_TYPES_V2}"
    )


# ===========================================================================
# V2 Taxonomy (added 2026-06-10 per ChatGPT 16th-round review)
#
# 4 大类 14 小类 + 5 attribute matrix. ICSE-flavored framing aligns with
# "traditional API compatibility ≠ agent-facing compatibility".
# ===========================================================================

MUTATION_TYPES_V2 = [
    # A. Identifier / representation-preserving (surface baseline, HAL-aligned)
    "A1_identifier_rename",
    "A2_format_change",
    "A3_paraphrase_meaning_preserving",
    # B. Schema-contract changes
    "B1_type_change",
    "B2_requiredness_change",
    "B3_enum_change",
    "B4_output_schema_change",            # NEW per ChatGPT review
    # C. Semantic-contract changes (paper core region)
    "C1_unit_scale_drift",
    "C2_currency_locale_drift",
    "C3_default_behavior_drift",          # NEW per ChatGPT review
    "C4_business_rule_drift",             # NEW per ChatGPT review
    # D. Protocol / operational changes
    "D1_error_format_change",
    "D2_permission_change",
    "D3_pagination_change",
    "D4_rate_limit_change",               # NEW (appendix-only optional)
]

# 5-attribute matrix: each mutation tagged by 5 booleans/tristates.
# Use this for Section 4.2 of the paper and for predictor features.
#   schema_visible:                static OpenAPI/JSON-schema diff sees it
#   semantics_changing:            intended behavior of API changed
#   traditional_compatible:        OpenAPI diff / typed-client / unit-test pass
#   agent_silent:                  agent likely fails silently (200 OK + wrong)
#   recoverable_via_error:         error feedback can guide agent to fix
ATTRIBUTE_MATRIX: dict[str, dict[str, str]] = {
    # values: "Y" / "N" / "P" (partial) / "?" (data-dependent)
    "A1_identifier_rename":              {"schema_visible": "Y", "semantics_changing": "N", "traditional_compatible": "P", "agent_silent": "N", "recoverable_via_error": "Y"},
    "A2_format_change":                  {"schema_visible": "Y", "semantics_changing": "N", "traditional_compatible": "P", "agent_silent": "N", "recoverable_via_error": "Y"},
    "A3_paraphrase_meaning_preserving":  {"schema_visible": "N", "semantics_changing": "N", "traditional_compatible": "Y", "agent_silent": "P", "recoverable_via_error": "?"},
    "B1_type_change":                    {"schema_visible": "Y", "semantics_changing": "P", "traditional_compatible": "N", "agent_silent": "N", "recoverable_via_error": "Y"},
    "B2_requiredness_change":            {"schema_visible": "Y", "semantics_changing": "P", "traditional_compatible": "N", "agent_silent": "N", "recoverable_via_error": "Y"},
    "B3_enum_change":                    {"schema_visible": "Y", "semantics_changing": "P", "traditional_compatible": "N", "agent_silent": "N", "recoverable_via_error": "P"},
    "B4_output_schema_change":           {"schema_visible": "Y", "semantics_changing": "P", "traditional_compatible": "P", "agent_silent": "Y", "recoverable_via_error": "N"},
    "C1_unit_scale_drift":               {"schema_visible": "N", "semantics_changing": "Y", "traditional_compatible": "Y", "agent_silent": "Y", "recoverable_via_error": "N"},
    "C2_currency_locale_drift":          {"schema_visible": "N", "semantics_changing": "Y", "traditional_compatible": "Y", "agent_silent": "Y", "recoverable_via_error": "N"},
    "C3_default_behavior_drift":         {"schema_visible": "N", "semantics_changing": "Y", "traditional_compatible": "Y", "agent_silent": "Y", "recoverable_via_error": "N"},
    "C4_business_rule_drift":            {"schema_visible": "N", "semantics_changing": "Y", "traditional_compatible": "Y", "agent_silent": "Y", "recoverable_via_error": "N"},
    "D1_error_format_change":            {"schema_visible": "P", "semantics_changing": "N", "traditional_compatible": "P", "agent_silent": "N", "recoverable_via_error": "P"},
    "D2_permission_change":              {"schema_visible": "P", "semantics_changing": "Y", "traditional_compatible": "N", "agent_silent": "N", "recoverable_via_error": "Y"},
    "D3_pagination_change":              {"schema_visible": "Y", "semantics_changing": "P", "traditional_compatible": "P", "agent_silent": "P", "recoverable_via_error": "P"},
    "D4_rate_limit_change":              {"schema_visible": "N", "semantics_changing": "N", "traditional_compatible": "Y", "agent_silent": "P", "recoverable_via_error": "Y"},
}

# Hero-region: traditional-compatible AND agent-silent AND semantics-changing
# = the "Class I" cell in the 2x2 traditional×agent compatibility matrix.
HERO_REGION = [
    m for m, attrs in ATTRIBUTE_MATRIX.items()
    if attrs["traditional_compatible"] in ("Y",)
    and attrs["agent_silent"] in ("Y",)
    and attrs["semantics_changing"] in ("Y",)
]
# Expected: C1, C2, C3, C4   ← the 4 semantic-contract mutations


# ---------------------------------------------------------------------------
# A2 · Surface format / layout change (snake_case → camelCase, etc.)
# This is the HAL-TauBenchPerturbator-aligned baseline.
# ---------------------------------------------------------------------------

def _snake_to_camel(name: str) -> str:
    if "_" not in name:
        return name
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:] if p)


def _a2_format_change(schema: dict, rng: random.Random) -> tuple[dict, Mutation]:
    """Convert all snake_case parameter names to camelCase.

    HAL-aligned surface mutation. Schema is technically changed (new keys),
    but for typed clients with codegen this is usually backward-incompatible
    *only* through naming; semantics stay identical.
    """
    new = copy.deepcopy(schema)
    props = _get_props(new)
    if not props:
        return new, Mutation("A2_format_change", "", note="no parameters")

    rename_map: dict[str, str] = {}
    new_props: dict = {}
    for k, v in props.items():
        new_k = _snake_to_camel(k)
        rename_map[k] = new_k
        new_props[new_k] = v
    new["parameters"]["properties"] = new_props

    # Update required list
    req = _get_required(new)
    if req:
        _set_required(new, [rename_map.get(k, k) for k in req])

    n_changed = sum(1 for k, v in rename_map.items() if k != v)
    if n_changed == 0:
        return new, Mutation("A2_format_change", "",
                             note="no snake_case params to convert")

    return new, Mutation(
        "A2_format_change",
        "parameters.properties.*",
        before=list(props.keys()),
        after=list(new_props.keys()),
        note=f"snake_case → camelCase for {n_changed} params",
        meta={"rename_map": rename_map},
    )


# ---------------------------------------------------------------------------
# B4 · Output schema change (rename / nest / missing field in tool RESPONSE)
# ---------------------------------------------------------------------------

_OUTPUT_SCHEMA_DRIFTS = [
    {
        "kind": "rename",
        "before": {"id": "string", "name": "string", "amount": "number"},
        "after":  {"identifier": "string", "name": "string", "amount": "number"},
        "summary": "output field 'id' renamed to 'identifier'",
    },
    {
        "kind": "nest",
        "before": {"id": "string", "amount": "number", "currency": "string"},
        "after":  {"id": "string", "money": {"amount": "number", "currency": "string"}},
        "summary": "output 'amount'+'currency' nested under 'money'",
    },
    {
        "kind": "missing",
        "before": {"id": "string", "name": "string", "phone": "string"},
        "after":  {"id": "string", "name": "string"},
        "summary": "output field 'phone' removed",
    },
    {
        "kind": "extra",
        "before": {"id": "string", "name": "string"},
        "after":  {"id": "string", "name": "string", "internal_flags": "object"},
        "summary": "output gained 'internal_flags' (may confuse field-greedy agent)",
    },
]


def _b4_output_schema_change(schema: dict, rng: random.Random
                              ) -> tuple[dict, Mutation]:
    """Mark the tool's expected output shape as changed.

    The runner is responsible for translating actual tool responses to the
    'after' shape so the agent sees the new format. We attach metadata here.
    """
    new = copy.deepcopy(schema)
    drift = rng.choice(_OUTPUT_SCHEMA_DRIFTS)
    new["x-output-schema-change"] = drift
    return new, Mutation(
        "B4_output_schema_change",
        "x-output-schema-change",
        before=drift["before"],
        after=drift["after"],
        note=f"output schema {drift['kind']}: {drift['summary']}",
        meta={"kind": drift["kind"]},
    )


# ---------------------------------------------------------------------------
# C3 · Default behavior drift (e.g. default sort order, default page size,
# default cancellation policy). Schema unchanged; behavior changed.
# ---------------------------------------------------------------------------

_DEFAULT_BEHAVIOR_DRIFTS = [
    "default sort order changed from 'newest first' to 'highest priority first'",
    "default page size changed from 10 to 50 (may overflow agent context)",
    "default filter changed from 'active items' to 'all items including archived'",
    "default cancellation policy changed from 'soft cancel (recoverable)' to 'hard delete'",
    "default search radius changed from 'city' to 'metropolitan area'",
]


def _c3_default_behavior_drift(schema: dict, rng: random.Random
                                ) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    drift = rng.choice(_DEFAULT_BEHAVIOR_DRIFTS)
    new["x-default-behavior-change"] = drift
    desc = new.get("description", "")
    new["description"] = desc + f" (NOTE: behavioral default changed; {drift})"
    return new, Mutation(
        "C3_default_behavior_drift",
        "x-default-behavior-change",
        before=None, after=drift,
        note=f"default behavior drift (schema unchanged): {drift}",
    )


# ---------------------------------------------------------------------------
# C4 · Business-rule drift (refund eligibility, booking policy, permission
# boundary changed at the policy level, not the schema level)
# ---------------------------------------------------------------------------

_BUSINESS_RULE_DRIFTS = [
    "refund eligibility: any time → only within 24h of purchase",
    "booking confirmation: immediate → requires explicit second confirmation",
    "permission boundary: read-only → can also delete (caller must check)",
    "order modification: full edit → only quantity adjustable",
    "promo code stacking: combinable → exclusive (only one allowed)",
]


def _c4_business_rule_drift(schema: dict, rng: random.Random
                             ) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    drift = rng.choice(_BUSINESS_RULE_DRIFTS)
    new["x-business-rule-change"] = drift
    desc = new.get("description", "")
    new["description"] = desc + f" (POLICY UPDATE: {drift})"
    return new, Mutation(
        "C4_business_rule_drift",
        "x-business-rule-change",
        before=None, after=drift,
        note=f"business rule drift (schema unchanged): {drift}",
    )


# ---------------------------------------------------------------------------
# D4 · Rate limit / timeout / partial response (appendix-only optional)
# ---------------------------------------------------------------------------

def _d4_rate_limit_change(schema: dict, rng: random.Random
                           ) -> tuple[dict, Mutation]:
    new = copy.deepcopy(schema)
    new["x-rate-limit-change"] = {"before": "100/min", "after": "10/min"}
    new["x-timeout-change"] = {"before": "30s", "after": "5s"}
    return new, Mutation(
        "D4_rate_limit_change",
        "x-rate-limit-change",
        before="100/min, 30s timeout",
        after="10/min, 5s timeout",
        note="rate limit tightened 100→10/min; timeout tightened 30s→5s",
    )


# ---------------------------------------------------------------------------
# V2 Dispatcher — maps v2 names to functions (some reused from legacy _mXX)
# ---------------------------------------------------------------------------

_V2_DISPATCH = {
    # A. Identifier / representation
    "A1_identifier_rename":              _m01_rename,
    "A2_format_change":                  _a2_format_change,
    "A3_paraphrase_meaning_preserving":  _m07_description_paraphrase,
    # B. Schema-contract
    "B1_type_change":                    _m02_type_change,
    "B2_requiredness_change":            _m03_requiredness,
    "B3_enum_change":                    _m06_enum_rename,
    "B4_output_schema_change":           _b4_output_schema_change,
    # C. Semantic-contract (paper hero region)
    "C1_unit_scale_drift":               _m05_unit_change,
    "C2_currency_locale_drift":          _m04_default_drift,
    "C3_default_behavior_drift":         _c3_default_behavior_drift,
    "C4_business_rule_drift":            _c4_business_rule_drift,
    # D. Protocol / operational
    "D1_error_format_change":            _m08_error_format,
    "D2_permission_change":              _m09_permission_change,
    "D3_pagination_change":              _m10_pagination_change,
    "D4_rate_limit_change":              _d4_rate_limit_change,
}


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def get_attributes(mutation_type_v2: str) -> dict[str, str]:
    """Return the 5-attribute tags for a v2 mutation type."""
    if mutation_type_v2 not in ATTRIBUTE_MATRIX:
        raise ValueError(f"unknown v2 mutation: {mutation_type_v2}")
    return ATTRIBUTE_MATRIX[mutation_type_v2]


def is_hero_region(mutation_type_v2: str) -> bool:
    """Hero region = traditional-compatible AND agent-silent AND
    semantics-changing. Members are C1/C2/C3/C4."""
    return mutation_type_v2 in HERO_REGION



# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> int:
    """Smoke test: apply each of M01-M10 (legacy) AND A1-D4 (v2) to a
    sample tool schema."""
    sample = {
        "name": "search_flight",
        "description": "Search flights between two cities.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_city": {"type": "string",
                              "description": "Origin city (English name)."},
                "to_city":   {"type": "string",
                              "description": "Destination city."},
                "date":      {"type": "string",
                              "description": "YYYY-MM-DD format."},
                "budget":    {"type": "number",
                              "description": "Maximum budget in USD."},
                "status":    {"type": "string",
                              "description": "Filter by status.",
                              "enum": ["pending", "done"]},
            },
            "required": ["from_city", "to_city", "date"],
        },
    }
    print(f"[SELF-TEST V1] applying {len(MUTATION_TYPES)} legacy mutations...\n")
    ok_v1 = 0
    for mt in MUTATION_TYPES:
        try:
            new, mut = apply_mutation(sample, mt, seed=42)
            print(f"  {mt:36s}  →  {mut.note[:80]}")
            ok_v1 += 1
        except Exception as e:  # noqa: BLE001
            print(f"  {mt:36s}  →  FAILED: {e}")
    print(f"\n[SELF-TEST V1] {ok_v1}/{len(MUTATION_TYPES)} passed.\n")

    print(f"[SELF-TEST V2] applying {len(MUTATION_TYPES_V2)} v2 mutations...\n")
    ok_v2 = 0
    hero_count = 0
    for mt in MUTATION_TYPES_V2:
        try:
            new, mut = apply_mutation(sample, mt, seed=42)
            attrs = get_attributes(mt)
            attr_str = " ".join(f"{k[:4]}={v}" for k, v in attrs.items())
            hero_mark = "  [HERO]" if is_hero_region(mt) else ""
            print(f"  {mt:36s}{hero_mark}")
            print(f"    note: {mut.note[:90]}")
            print(f"    attrs: {attr_str}")
            if is_hero_region(mt):
                hero_count += 1
            ok_v2 += 1
        except Exception as e:  # noqa: BLE001
            print(f"  {mt:36s}  →  FAILED: {e}")
    print(f"\n[SELF-TEST V2] {ok_v2}/{len(MUTATION_TYPES_V2)} passed; "
          f"{hero_count} hero-region mutations (expected: 4 = C1-C4).")

    total_ok = (ok_v1 == len(MUTATION_TYPES)) and (ok_v2 == len(MUTATION_TYPES_V2))
    return 0 if total_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
