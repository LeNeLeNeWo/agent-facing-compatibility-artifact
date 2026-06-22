"""Phase 10E real-changelog-grounded replay smoke runner.

This stage builds deterministic local wrappers from Phase 10A real changelog
candidates. It does not call real Stripe/GitHub APIs. The only external calls
are optional LLM agent calls to the configured model providers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


ROOT = Path(__file__).resolve().parents[2]
PHASE10 = ROOT / "runs" / "schema_mutation" / "phase10"
GROUNDING = PHASE10 / "real_api_grounding"
REPLAY = PHASE10 / "real_case_replay"
SMOKE = REPLAY / "smoke"
STATUS_DIRNAME = "status"
RAW_DIRNAME = "raw"
LOG_DIRNAME = "logs"
META_DIRNAME = "metadata"

CORPUS = GROUNDING / "api_evolution_corpus.jsonl"
CANDIDATES = GROUNDING / "real_change_case_candidates.json"
AUDIT_JSON = REPLAY / "real_case_audit.json"
AUDIT_MD = REPLAY / "real_case_audit.md"
DEFAULT_PLAN = SMOKE / "real_case_smoke_plan.jsonl"
DEFAULT_PLAN_MD = SMOKE / "real_case_smoke_plan.md"

DEFAULT_MODELS = ["deepseek/deepseek-v4-flash", "dashscope/qwen-max"]
CONDITIONS = ["baseline_old_api", "evolved_o0_silent", "evolved_visible_feedback"]
STOP_LIMITS = {"provider_error": 3, "timeout": 3, "failed": 3}
TERMINAL_STATUSES = {"ok", "provider_error", "timeout", "failed", "not_run"}
EXPERIMENTS = {
    "real_changelog_grounded_replay_smoke",
    "real_changelog_grounded_replay_formal",
}

PROVIDER_DEFAULTS = {
    "deepseek": {
        "key": "DEEPSEEK_API_KEY",
        "base": "DEEPSEEK_BASE_URL",
        "base_alias": "DEEPSEEK_API_BASE",
        "default_base": "https://api.deepseek.com/v1",
    },
    "dashscope": {
        "key": "DASHSCOPE_API_KEY",
        "base": "DASHSCOPE_BASE_URL",
        "base_alias": "DASHSCOPE_API_BASE",
        "default_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
}

PROVIDER_ERROR_PATTERNS = (
    "api_key",
    "api key",
    "unauthorized",
    "forbidden",
    "quota",
    "billing",
    "balance",
    "insufficient",
    "connection",
    "connect",
    "urlopen",
    "socket",
    "winerror 10013",
    "access permission",
    "provider",
    "base_url",
    "base url",
    "401",
    "403",
)

CASE_IDS = [
    "real_c3_default_behavior_8b11a458888a",
    "real_c1_unit_scale_0a2066fde082",
    "real_c4_business_rule_323e42cd6611",
]


def load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env", override=False)
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def sanitize_error(text: str) -> str:
    text = re.sub(r"https?://[^\s)]+", "[redacted-url]", text)
    for key, value in os.environ.items():
        if "KEY" in key or "TOKEN" in key or "SECRET" in key:
            if value and len(value) >= 6:
                text = text.replace(value, "[redacted-secret]")
    return text[:1200]


def classify_error(text: str) -> str:
    low = text.lower()
    if "timeout" in low or "timed out" in low:
        return "timeout"
    if any(pattern in low for pattern in PROVIDER_ERROR_PATTERNS):
        return "provider_error"
    return "failed"


def provider_and_model(model_id: str) -> tuple[str, str]:
    if "/" not in model_id:
        return "", model_id
    provider, model = model_id.split("/", 1)
    return provider, model


def provider_config(model_id: str) -> tuple[str, str, str, str]:
    provider, model = provider_and_model(model_id)
    cfg = PROVIDER_DEFAULTS.get(provider)
    if cfg is None:
        raise RuntimeError(f"unsupported provider prefix for Phase 10E smoke: {provider!r}")
    key = os.getenv(cfg["key"])
    if not key:
        raise RuntimeError(f"{cfg['key']} is not set")
    base_url = os.getenv(cfg["base"]) or os.getenv(cfg["base_alias"]) or cfg["default_base"]
    return provider, model, key, base_url


def make_client(model_id: str, timeout_s: int) -> tuple[Any, str, str]:
    if OpenAI is None:
        raise RuntimeError("openai package is unavailable")
    provider, model, key, base_url = provider_config(model_id)
    client = OpenAI(api_key=key, base_url=base_url, timeout=timeout_s, max_retries=0)
    return client, provider, model


def chat_once_urllib(
    model_id: str,
    messages: list[dict[str, str]],
    timeout_s: int,
    max_tokens: int,
) -> tuple[str, dict[str, int]]:
    _provider, clean_model, key, base_url = provider_config(model_id)
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": clean_model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTPError {exc.code}: {detail[:600]}") from exc
    choice = data.get("choices", [{}])[0]
    message = choice.get("message") or {}
    text = message.get("content") or ""
    usage = data.get("usage") or {}
    return text, {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
    }


def chat_once(model_id: str, messages: list[dict[str, str]], timeout_s: int, max_tokens: int) -> tuple[str, dict[str, int]]:
    if OpenAI is None:
        return chat_once_urllib(model_id, messages, timeout_s=timeout_s, max_tokens=max_tokens)
    client, _provider, clean_model = make_client(model_id, timeout_s)
    resp = client.chat.completions.create(
        model=clean_model,
        messages=messages,
        temperature=0.0,
        max_tokens=max_tokens,
    )
    msg = resp.choices[0].message
    text = msg.content or ""
    usage = {
        "prompt_tokens": int(getattr(resp.usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(resp.usage, "completion_tokens", 0) or 0),
    }
    return text, usage


def candidate_rows() -> list[dict[str, Any]]:
    if not CANDIDATES.exists():
        return []
    data = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    return [r for r in data if r.get("case_id") in CASE_IDS]


def corpus_by_url() -> dict[str, dict[str, Any]]:
    return {str(r.get("url")): r for r in read_jsonl(CORPUS)}


def tool_schemas() -> dict[str, dict[str, Any]]:
    return {
        "real_c1_unit_scale_0a2066fde082": {
            "name": "record_billing_meter_event",
            "description": "Record usage for a billing meter event in the local replay wrapper.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "meter_name": {"type": "string"},
                    "value": {"type": "integer", "description": "Integer usage value."},
                    "idempotency_key": {"type": "string"},
                },
                "required": ["customer_id", "meter_name", "value"],
                "additionalProperties": False,
            },
        },
        "real_c4_business_rule_323e42cd6611": {
            "name": "create_payment_link",
            "description": "Create a payment link in the local replay wrapper.",
            "parameters": {
                "type": "object",
                "properties": {
                    "price_id": {"type": "string"},
                    "amount": {"type": "integer", "description": "Amount in cents."},
                    "currency": {"type": "string"},
                    "allowed_card_brands": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["visa", "mastercard", "amex", "discover"]},
                        "description": "Optional list of accepted card brands.",
                    },
                },
                "required": ["price_id", "amount", "currency"],
                "additionalProperties": False,
            },
        },
    }


def wrapper_templates() -> dict[str, dict[str, Any]]:
    schemas = tool_schemas()
    return {
        "real_c1_unit_scale_0a2066fde082": {
            "selected_for_smoke": True,
            "selection_reason": "The title gives a concrete validation boundary (>15 digits), enabling a deterministic local oracle.",
            "old_semantics": "The old replay wrapper accepts a billing meter event integer value and records the requested total.",
            "new_semantics": "The new replay wrapper treats billing meter event values with more than 15 decimal digits as invalid; large totals must be split across valid events.",
            "tool_schema": schemas["real_c1_unit_scale_0a2066fde082"],
            "baseline_task": (
                "Record a total billing-meter usage value of 1234567890123456 for customer cus_phase10_c1 "
                "on meter api_request_units. Preserve the exact total. You may make one or more tool calls."
            ),
            "evolved_o0_behavior": (
                "The same schema is exposed. A too-large event appears to be accepted at the tool layer, "
                "but the final deterministic oracle flags the changed validation rule."
            ),
            "visible_feedback_behavior": (
                "The wrapper returns a structured validation error or migration note explaining that event values "
                "must be at most 15 digits and should be split."
            ),
            "oracle_rule": "Success requires total recorded usage to equal 1234567890123456; under new semantics every individual event value must be <= 999999999999999.",
            "target_total": 1234567890123456,
            "max_event_value": 999999999999999,
        },
        "real_c4_business_rule_323e42cd6611": {
            "selected_for_smoke": True,
            "selection_reason": "The title gives a concrete changed payment policy (card-brand restrictions), enabling a deterministic local oracle.",
            "old_semantics": "The old replay wrapper creates a Payment Link with default card-brand acceptance when the optional restriction field is omitted.",
            "new_semantics": "The new replay wrapper requires the Payment Link to respect configured card-brand restrictions for this merchant.",
            "tool_schema": schemas["real_c4_business_rule_323e42cd6611"],
            "baseline_task": (
                "Create a USD payment link for price price_real_replay_c4 with amount 4900. "
                "Use default card-brand settings unless API feedback tells you otherwise."
            ),
            "evolved_o0_behavior": (
                "The same schema is exposed. A link created without explicit allowed-card restrictions appears "
                "to be created, but the hidden oracle flags unsupported card-brand acceptance."
            ),
            "visible_feedback_behavior": (
                "The wrapper returns a structured policy error or migration note explaining that this merchant's "
                "Payment Links may accept only visa and mastercard."
            ),
            "oracle_rule": "Under new semantics the created Payment Link must restrict accepted card brands to visa and mastercard only.",
            "required_brands": ["visa", "mastercard"],
        },
        "real_c3_default_behavior_8b11a458888a": {
            "selected_for_smoke": False,
            "selection_reason": (
                "Not selected for this smoke. The local Phase 10A evidence names a safer default and includes a "
                "truncated snippet, but it does not specify the exact before/after default needed for a faithful deterministic wrapper."
            ),
            "old_semantics": "Insufficiently specified in local evidence for deterministic replay without further human review.",
            "new_semantics": "Insufficiently specified in local evidence for deterministic replay without further human review.",
            "tool_schema": None,
            "baseline_task": None,
            "evolved_o0_behavior": None,
            "visible_feedback_behavior": None,
            "oracle_rule": None,
        },
    }


def build_cases_and_audit() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = candidate_rows()
    corpus = corpus_by_url()
    templates = wrapper_templates()
    cases: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for cand in candidates:
        case_id = str(cand.get("case_id"))
        entry = corpus.get(str(cand.get("source_url")), {})
        template = templates.get(case_id, {})
        selected = bool(template.get("selected_for_smoke"))
        evidence = str(entry.get("evidence_snippet") or cand.get("after_semantics") or "")
        official_url = str(cand.get("source_url") or entry.get("url") or "")
        provider = str(cand.get("provider") or entry.get("provider") or "")
        taxonomy = str(cand.get("real_change_type") or entry.get("taxonomy_class") or "")
        subclass = str(entry.get("c_subclass") or cand.get("why_schema_invisible_or_semantic") or "")
        case = {
            "case_id": case_id,
            "provider": provider,
            "taxonomy_class": taxonomy,
            "taxonomy_subclass": subclass,
            "official_source_url": official_url,
            "title": str(entry.get("title") or cand.get("after_semantics") or ""),
            "short_evidence": evidence,
            "old_semantics": template.get("old_semantics"),
            "new_semantics": template.get("new_semantics"),
            "tool_schema": template.get("tool_schema"),
            "baseline_task": template.get("baseline_task"),
            "evolved_o0_behavior": template.get("evolved_o0_behavior"),
            "visible_feedback_behavior": template.get("visible_feedback_behavior"),
            "oracle_rule": template.get("oracle_rule"),
            "selected_for_smoke": selected,
            "selection_reason": template.get("selection_reason"),
            "source_entry_id": entry.get("entry_id"),
            "needs_human_review": bool(entry.get("needs_human_review", True)),
            "replay_parameters": {k: v for k, v in template.items() if k not in {
                "selected_for_smoke",
                "selection_reason",
                "old_semantics",
                "new_semantics",
                "tool_schema",
                "baseline_task",
                "evolved_o0_behavior",
                "visible_feedback_behavior",
                "oracle_rule",
            }},
        }
        cases.append(case)
        before_clear = selected
        after_clear = selected or ("default" in case["title"].lower() and bool(evidence))
        audit_rows.append(
            {
                "case_id": case_id,
                "provider": provider,
                "taxonomy_class": taxonomy,
                "official_source_url_exists": bool(official_url),
                "official_source_url": official_url,
                "evidence_snippet_exists": bool(evidence),
                "before_semantics_clear_enough": before_clear,
                "after_semantics_clear_enough": after_clear,
                "semantic_change_class_clear_enough": taxonomy in {"C1", "C3", "C4"},
                "deterministic_wrapper_possible": selected,
                "deterministic_oracle_possible": selected,
                "agent_task_possible": selected,
                "suitable_for_smoke": selected,
                "selected_for_smoke": selected,
                "risks": (
                    "Requires human review before paper use; replay is grounded in changelog title/evidence and is not a production incident. "
                    + ("" if selected else "Exact before/after semantics are under-specified in local evidence.")
                ).strip(),
                "selection_reason": template.get("selection_reason"),
                "short_evidence": evidence,
            }
        )
    return cases, audit_rows


def write_audit(cases: list[dict[str, Any]], audit_rows: list[dict[str, Any]]) -> None:
    data = {
        "phase": "phase10e",
        "audit_rows": audit_rows,
        "selected_case_ids": [c["case_id"] for c in cases if c.get("selected_for_smoke")],
        "not_selected_case_ids": [c["case_id"] for c in cases if not c.get("selected_for_smoke")],
        "notes": [
            "This is real-changelog-grounded replay, not a real production incident replay.",
            "No real Stripe/GitHub API call is made by the wrapper.",
        ],
    }
    write_json(AUDIT_JSON, data)
    lines = [
        "# Phase 10E Real Case Audit",
        "",
        "- Scope: real-changelog-grounded deterministic replay smoke.",
        "- No real Stripe/GitHub API calls are used.",
        "- Selected cases: " + ", ".join(data["selected_case_ids"]),
        "- Not selected: " + ", ".join(data["not_selected_case_ids"]),
        "",
        "| case | provider | class | evidence | before/after clear | wrapper | oracle | smoke | risks |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in audit_rows:
        clear = f"{row['before_semantics_clear_enough']}/{row['after_semantics_clear_enough']}"
        lines.append(
            f"| {row['case_id']} | {row['provider']} | {row['taxonomy_class']} | "
            f"{row['evidence_snippet_exists']} | {clear} | {row['deterministic_wrapper_possible']} | "
            f"{row['deterministic_oracle_possible']} | {row['suitable_for_smoke']} | {row['risks']} |"
        )
    lines.extend(["", "## Wrapper Cases", ""])
    for case in cases:
        lines.extend(
            [
                f"### {case['case_id']}",
                "",
                f"- Source: {case['official_source_url']}",
                f"- Evidence: {case['short_evidence']}",
                f"- Selected: {case['selected_for_smoke']}",
                f"- Reason: {case['selection_reason']}",
                f"- Old semantics: {case['old_semantics']}",
                f"- New semantics: {case['new_semantics']}",
                f"- Oracle: {case['oracle_rule']}",
                "",
            ]
        )
    AUDIT_MD.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def model_provider(model: str) -> str:
    return provider_and_model(model)[0]


def build_plan(cases: list[dict[str, Any]], models: list[str], seed: int) -> list[dict[str, Any]]:
    selected = [c for c in cases if c.get("selected_for_smoke")]
    rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        for case in selected:
            for model in models:
                model_slug = re.sub(r"[^A-Za-z0-9]+", "-", model).strip("-")
                cell_key = f"phase10e::{case['case_id']}::{condition}::{model_slug}::s{seed}"
                rows.append(
                    {
                        "phase": "phase10e",
                        "experiment": "real_changelog_grounded_replay_smoke",
                        "cell_key": cell_key,
                        "case_id": case["case_id"],
                        "provider": case["provider"],
                        "taxonomy_class": case["taxonomy_class"],
                        "taxonomy_subclass": case["taxonomy_subclass"],
                        "official_source_url": case["official_source_url"],
                        "short_evidence": case["short_evidence"],
                        "old_semantics": case["old_semantics"],
                        "new_semantics": case["new_semantics"],
                        "tool_schema": case["tool_schema"],
                        "baseline_task": case["baseline_task"],
                        "evolved_o0_behavior": case["evolved_o0_behavior"],
                        "visible_feedback_behavior": case["visible_feedback_behavior"],
                        "oracle_rule": case["oracle_rule"],
                        "condition": condition,
                        "model": model,
                        "llm_provider": model_provider(model),
                        "seed": seed,
                        "schema_changed": False,
                        "real_third_party_api_allowed": False,
                        "fake_run": False,
                        "baseline_success_expected": True,
                        "selected_for_smoke": True,
                        "max_turns": 6,
                    }
                )
    return rows


def write_plan(plan_path: Path, plan_rows: list[dict[str, Any]]) -> None:
    write_jsonl(plan_path, plan_rows)
    md_path = plan_path.with_suffix(".md")
    if plan_path == DEFAULT_PLAN:
        md_path = DEFAULT_PLAN_MD
    by_condition = Counter(r["condition"] for r in plan_rows)
    by_case = Counter(r["case_id"] for r in plan_rows)
    by_model = Counter(r["model"] for r in plan_rows)
    lines = [
        "# Phase 10E Real-Case Replay Smoke Plan",
        "",
        f"- Planned cells: {len(plan_rows)}",
        "- Conditions: " + ", ".join(f"{k}={v}" for k, v in sorted(by_condition.items())),
        "- Cases: " + ", ".join(f"{k}={v}" for k, v in sorted(by_case.items())),
        "- Models: " + ", ".join(f"{k}={v}" for k, v in sorted(by_model.items())),
        "- Real third-party API calls: disabled; wrappers are local deterministic replay.",
        "",
        "| cell | case | condition | model |",
        "| --- | --- | --- | --- |",
    ]
    for row in plan_rows:
        lines.append(f"| {row['cell_key']} | {row['case_id']} | {row['condition']} | {row['model']} |")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    decoder = json.JSONDecoder()
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("no JSON object found in model response")
    obj, _idx = decoder.raw_decode(cleaned[start:])
    if not isinstance(obj, dict):
        raise ValueError("model response JSON is not an object")
    return obj


def public_case_metadata(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": cell["case_id"],
        "provider": cell["provider"],
        "taxonomy_class": cell["taxonomy_class"],
        "source_url": cell["official_source_url"],
        "title_or_evidence": cell["short_evidence"],
    }


def initial_messages(cell: dict[str, Any]) -> list[dict[str, str]]:
    condition = cell["condition"]
    schema = cell["tool_schema"]
    condition_note = {
        "baseline_old_api": (
            "This local wrapper follows the old API behavior for the task. Optional fields should be used only "
            "when needed by the visible schema or tool feedback."
        ),
        "evolved_o0_silent": (
            "This local wrapper exposes the same schema and ordinary tool-layer responses. Use only visible "
            "schema and tool responses; do not assume hidden provider-side changes."
        ),
        "evolved_visible_feedback": (
            "This local wrapper may return structured validation or policy feedback. If it does, use that "
            "visible feedback to revise your next tool call."
        ),
    }[condition]
    system = (
        "You are an API-using agent in a deterministic local replay. "
        "Do not call external provider APIs. Use only the listed local tool. "
        "Return exactly one JSON object per turn and no prose. "
        "Allowed forms are "
        '{"action":"<tool_name>","arguments":{...}} or {"action":"finish","final_answer":"..."}. '
        "After a tool error, revise the arguments using the visible error details."
    )
    user = (
        f"{condition_note}\n\n"
        f"Local tool schema:\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        f"Task:\n{cell['baseline_task']}\n\n"
        "Return the next JSON action."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def o0_leakage_terms(cell: dict[str, Any]) -> list[str]:
    if cell["case_id"] == "real_c1_unit_scale_0a2066fde082":
        return ["15 digits", "999999999999999", "split across valid events", "more than 15"]
    if cell["case_id"] == "real_c4_business_rule_323e42cd6611":
        return ["visa and mastercard only", "card-brand restrictions", "may accept only visa", "required_brands"]
    return []


def detect_rule_leakage(cell: dict[str, Any]) -> list[str]:
    if cell["condition"] not in {"evolved_o0_silent", "baseline_old_api"}:
        return []
    text = "\n".join(m["content"] for m in initial_messages(cell)).lower()
    return [term for term in o0_leakage_terms(cell) if term.lower() in text]


class LocalReplayWrapper:
    def __init__(self, cell: dict[str, Any]):
        self.cell = cell
        self.condition = str(cell["condition"])
        self.case_id = str(cell["case_id"])
        self.state: dict[str, Any] = {
            "events": [],
            "payment_links": [],
            "tool_errors": [],
            "migration_notes": [],
        }

    @property
    def is_new(self) -> bool:
        return self.condition in {"evolved_o0_silent", "evolved_visible_feedback"}

    @property
    def is_visible(self) -> bool:
        return self.condition == "evolved_visible_feedback"

    def call(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.case_id == "real_c1_unit_scale_0a2066fde082":
            return self._record_billing_meter_event(action, args)
        if self.case_id == "real_c4_business_rule_323e42cd6611":
            return self._create_payment_link(action, args)
        raise RuntimeError(f"unsupported case_id: {self.case_id}")

    def _record_billing_meter_event(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        expected = self.cell["tool_schema"]["name"]
        if action != expected:
            return self._tool_error("unknown_tool", f"Use local tool {expected}.", visible_rule=False)
        required = {"customer_id", "meter_name", "value"}
        if not required.issubset(args):
            return self._tool_error("schema_error", f"Missing required fields: {sorted(required - set(args))}", visible_rule=False)
        try:
            value = int(args["value"])
        except Exception:
            return self._tool_error("schema_error", "value must be an integer", visible_rule=False)
        max_value = int(self.cell.get("max_event_value") or 999999999999999)
        if self.is_visible and value > max_value:
            return self._tool_error(
                "billing_meter_event_value_too_large",
                "Billing meter event values with more than 15 digits are rejected; split the total into multiple events no larger than 999999999999999.",
                visible_rule=True,
            )
        event = {
            "customer_id": str(args["customer_id"]),
            "meter_name": str(args["meter_name"]),
            "value": value,
            "idempotency_key": str(args.get("idempotency_key") or f"event_{len(self.state['events']) + 1}"),
        }
        self.state["events"].append(event)
        response: dict[str, Any] = {
            "status": "ok",
            "event_id": f"evt_phase10e_{len(self.state['events'])}",
            "recorded_value": value,
        }
        if self.is_visible:
            response["migration_note"] = "Billing meter event values must be at most 15 digits in this replay wrapper."
            self.state["migration_notes"].append(response["migration_note"])
        return response

    def _create_payment_link(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        expected = self.cell["tool_schema"]["name"]
        if action != expected:
            return self._tool_error("unknown_tool", f"Use local tool {expected}.", visible_rule=False)
        required = {"price_id", "amount", "currency"}
        if not required.issubset(args):
            return self._tool_error("schema_error", f"Missing required fields: {sorted(required - set(args))}", visible_rule=False)
        required_brands = list(self.cell.get("required_brands") or ["visa", "mastercard"])
        brands = args.get("allowed_card_brands")
        if brands is None:
            accepted_brands = ["visa", "mastercard", "amex", "discover"]
        elif isinstance(brands, list):
            accepted_brands = [str(b).lower() for b in brands]
        else:
            return self._tool_error("schema_error", "allowed_card_brands must be a list when supplied", visible_rule=False)
        unsupported = sorted(set(accepted_brands) - set(required_brands))
        missing_restriction = brands is None
        if self.is_visible and (missing_restriction or unsupported):
            return self._tool_error(
                "payment_link_card_brand_restriction",
                "This merchant's Payment Links may accept only visa and mastercard; set allowed_card_brands to ['visa', 'mastercard'].",
                visible_rule=True,
            )
        link = {
            "payment_link_id": f"plink_phase10e_{len(self.state['payment_links']) + 1}",
            "price_id": str(args["price_id"]),
            "amount": int(args["amount"]),
            "currency": str(args["currency"]).lower(),
            "accepted_card_brands": accepted_brands,
        }
        self.state["payment_links"].append(link)
        response = {"status": "ok", **link}
        if self.is_visible:
            response["migration_note"] = "Payment Links for this merchant may accept only visa and mastercard."
            self.state["migration_notes"].append(response["migration_note"])
        return response

    def _tool_error(self, code: str, message: str, *, visible_rule: bool) -> dict[str, Any]:
        err = {"status": "error", "error_code": code, "message": message, "visible_rule": visible_rule}
        self.state["tool_errors"].append(err)
        return err

    def oracle(self) -> dict[str, Any]:
        if self.case_id == "real_c1_unit_scale_0a2066fde082":
            return self._oracle_c1()
        if self.case_id == "real_c4_business_rule_323e42cd6611":
            return self._oracle_c4()
        raise RuntimeError(f"unsupported case_id: {self.case_id}")

    def _oracle_c1(self) -> dict[str, Any]:
        target = int(self.cell.get("target_total") or 1234567890123456)
        max_value = int(self.cell.get("max_event_value") or 999999999999999)
        events = list(self.state["events"])
        total = sum(int(e["value"]) for e in events)
        old_ok = total == target
        values_valid = all(int(e["value"]) <= max_value for e in events)
        new_ok = old_ok and values_valid
        hidden = self.is_new and old_ok and not values_valid and not self.is_visible
        return {
            "deterministic_oracle_ok": True,
            "old_success": old_ok,
            "new_success": new_ok,
            "success": old_ok if self.condition == "baseline_old_api" else new_ok,
            "hidden_business_rule_violation": hidden,
            "violation_reason": None if not hidden else "billing meter event value exceeds 15-digit validation boundary",
            "total_recorded": total,
            "event_count": len(events),
            "values_valid_under_new_semantics": values_valid,
        }

    def _oracle_c4(self) -> dict[str, Any]:
        required_brands = set(self.cell.get("required_brands") or ["visa", "mastercard"])
        links = list(self.state["payment_links"])
        latest = links[-1] if links else None
        old_ok = bool(latest and latest["price_id"] == "price_real_replay_c4" and latest["amount"] == 4900 and latest["currency"] == "usd")
        if latest:
            accepted = set(latest.get("accepted_card_brands") or [])
            brands_valid = accepted == required_brands
        else:
            accepted = set()
            brands_valid = False
        new_ok = old_ok and brands_valid
        hidden = self.is_new and old_ok and not brands_valid and not self.is_visible
        return {
            "deterministic_oracle_ok": True,
            "old_success": old_ok,
            "new_success": new_ok,
            "success": old_ok if self.condition == "baseline_old_api" else new_ok,
            "hidden_business_rule_violation": hidden,
            "violation_reason": None if not hidden else "payment link accepts unsupported card brands under changed restriction",
            "payment_link_count": len(links),
            "accepted_card_brands": sorted(accepted),
            "brands_valid_under_new_semantics": brands_valid,
        }


def base_status(cell: dict[str, Any], status: str = "pending") -> dict[str, Any]:
    return {
        "phase": "phase10e",
        "experiment": cell.get("experiment") or "real_changelog_grounded_replay_smoke",
        "cell_key": cell.get("cell_key"),
        "case_id": cell.get("case_id"),
        "provider": cell.get("provider"),
        "taxonomy_class": cell.get("taxonomy_class"),
        "condition": cell.get("condition"),
        "model": cell.get("model"),
        "llm_provider": cell.get("llm_provider"),
        "seed": cell.get("seed"),
        "status": status,
        "reward": None,
        "mutation_success": None,
        "hidden_business_rule_violation": False,
        "visible_policy_error": False,
        "migration_note_visible": False,
        "visible_rule_exposed": False,
        "recovery_attempted": False,
        "recovery_success": False,
        "deterministic_oracle_ok": False,
        "num_actions": 0,
        "num_llm_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "elapsed_s": 0.0,
        "failure_mode": None,
        "error_message": None,
        "fake_run": False,
        "real_third_party_api_call_attempted": False,
        "rule_leakage_detected": False,
    }


def run_cell(cell: dict[str, Any], timeout_s: int, max_tokens: int) -> tuple[dict[str, Any], dict[str, Any] | None]:
    status = base_status(cell)
    t0 = time.time()
    leakage = detect_rule_leakage(cell)
    if leakage:
        status.update(
            {
                "status": "failed",
                "failure_mode": "rule_leakage",
                "error_message": "O0/baseline prompt leaked changed-rule terms: " + ", ".join(leakage),
                "rule_leakage_detected": True,
                "elapsed_s": round(time.time() - t0, 2),
            }
        )
        return status, None

    wrapper = LocalReplayWrapper(cell)
    messages = initial_messages(cell)
    assistant_outputs: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0}
    visible_errors = 0
    visible_rule_exposed = False
    status["migration_note_visible"] = False

    try:
        for _turn in range(int(cell.get("max_turns") or 6)):
            text, usage = chat_once(str(cell["model"]), messages, timeout_s=timeout_s, max_tokens=max_tokens)
            assistant_outputs.append(text)
            usage_totals["prompt_tokens"] += usage["prompt_tokens"]
            usage_totals["completion_tokens"] += usage["completion_tokens"]
            action_obj = extract_json_object(text)
            action = str(action_obj.get("action") or "")
            arguments = action_obj.get("arguments") or {}
            if action == "finish":
                break
            if not isinstance(arguments, dict):
                raise ValueError("action arguments must be a JSON object")
            result = wrapper.call(action, arguments)
            call_record = {"action": action, "arguments": arguments, "result": result}
            tool_calls.append(call_record)
            if result.get("status") == "error":
                visible_errors += 1
                if result.get("visible_rule"):
                    visible_rule_exposed = True
            if result.get("migration_note"):
                visible_rule_exposed = True
                status["migration_note_visible"] = True
            oracle_now = wrapper.oracle()
            if result.get("status") == "ok" and oracle_now.get("success"):
                break
            if result.get("status") == "ok" and cell["condition"] in {"baseline_old_api", "evolved_o0_silent"}:
                break
            messages.append({"role": "assistant", "content": text})
            messages.append(
                {
                    "role": "user",
                    "content": "Local tool response:\n"
                    + json.dumps(result, ensure_ascii=False, sort_keys=True)
                    + "\nReturn the next JSON action.",
                }
            )
        oracle = wrapper.oracle()
        success = bool(oracle.get("success"))
        hidden = bool(oracle.get("hidden_business_rule_violation"))
        status.update(
            {
                "status": "ok",
                "reward": 1.0 if success else 0.0,
                "mutation_success": success,
                "hidden_business_rule_violation": hidden,
                "visible_policy_error": visible_errors > 0,
                "visible_rule_exposed": visible_rule_exposed,
                "recovery_attempted": visible_errors > 0 and len(tool_calls) > visible_errors,
                "recovery_success": visible_errors > 0 and success,
                "deterministic_oracle_ok": bool(oracle.get("deterministic_oracle_ok")),
                "num_actions": len(tool_calls),
                "num_llm_calls": len(assistant_outputs),
                "prompt_tokens": usage_totals["prompt_tokens"],
                "completion_tokens": usage_totals["completion_tokens"],
                "elapsed_s": round(time.time() - t0, 2),
                "failure_mode": None if success else ("hidden_violation" if hidden else "oracle_failure"),
            }
        )
        raw = {
            "cell": cell,
            "public_case_metadata": public_case_metadata(cell),
            "assistant_outputs": assistant_outputs,
            "tool_calls": tool_calls,
            "final_state": wrapper.state,
            "oracle": oracle,
            "status": status,
            "initial_messages": messages[:2],
        }
        return status, raw
    except Exception as exc:  # noqa: BLE001
        err = sanitize_error(f"{type(exc).__name__}: {exc}")
        status.update(
            {
                "status": classify_error(err),
                "elapsed_s": round(time.time() - t0, 2),
                "error_message": err,
                "failure_mode": "runner_or_provider_error",
                "num_actions": len(tool_calls),
                "num_llm_calls": len(assistant_outputs),
                "prompt_tokens": usage_totals["prompt_tokens"],
                "completion_tokens": usage_totals["completion_tokens"],
            }
        )
        raw = {
            "cell": cell,
            "public_case_metadata": public_case_metadata(cell),
            "assistant_outputs": assistant_outputs,
            "tool_calls": tool_calls,
            "final_state": wrapper.state,
            "status": status,
            "error": err,
            "initial_messages": messages[:2],
        }
        return status, raw


def read_existing_status(output_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    status_dir = output_dir / STATUS_DIRNAME
    for path in sorted(status_dir.glob("*.jsonl")):
        for row in read_jsonl(path):
            if row.get("cell_key") and row.get("status") in TERMINAL_STATUSES:
                rows[str(row["cell_key"])] = row
    return rows


def validate_plan(rows: list[dict[str, Any]], max_cells: int = 24) -> list[str]:
    issues: list[str] = []
    if not rows:
        issues.append("plan is empty")
    if len(rows) > max_cells:
        issues.append(f"more than {max_cells} cells planned: {len(rows)}")
    for row in rows:
        key = row.get("cell_key")
        if row.get("phase") not in {"phase10e", "phase10f_r1"}:
            issues.append(f"{key}: unexpected phase")
        if row.get("experiment") not in EXPERIMENTS:
            issues.append(f"{key}: unexpected experiment")
        if row.get("fake_run"):
            issues.append(f"{key}: fake_run appears")
        if row.get("real_third_party_api_allowed"):
            issues.append(f"{key}: real third-party API call is allowed")
        if row.get("baseline_success_expected") is not True:
            issues.append(f"{key}: baseline_success_expected is not true")
        if row.get("condition") in {"baseline_old_api", "evolved_o0_silent"}:
            leaks = detect_rule_leakage(row)
            if leaks:
                issues.append(f"{key}: O0/baseline prompt leaks changed rule terms: {', '.join(leaks)}")
        if row.get("condition") == "evolved_visible_feedback" and not row.get("visible_feedback_behavior"):
            issues.append(f"{key}: visible_feedback condition does not define visible feedback")
    return issues


def stop_reason(status_rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], stop_limits: dict[str, int] | None = None) -> str | None:
    counts = Counter(str(r.get("status")) for r in status_rows)
    limits = stop_limits or STOP_LIMITS
    for status, limit in limits.items():
        if counts.get(status, 0) >= limit:
            return f"stop rule: {status}>={limit}"
    if any(r.get("fake_run") for r in status_rows):
        return "stop rule: fake_run appears"
    if any(r.get("real_third_party_api_call_attempted") for r in status_rows):
        return "stop rule: real third-party API call attempted"
    if any(r.get("rule_leakage_detected") for r in status_rows):
        return "stop rule: O0/baseline prompt rule leakage detected"
    baseline_rows = [r for r in status_rows if r.get("condition") == "baseline_old_api"]
    baseline_ok_rows = [r for r in baseline_rows if r.get("status") == "ok"]
    if len(baseline_ok_rows) >= 2:
        successes = sum(1 for r in baseline_ok_rows if r.get("mutation_success") is True)
        if successes == 0:
            return "stop rule: baseline_old_api success rate is 0 after at least 2 ok baseline attempts"
    return None


def run_plan(
    plan_path: Path,
    output_dir: Path,
    skip_existing: bool,
    timeout_s: int,
    max_tokens: int,
    max_cells: int = 24,
    stop_limits: dict[str, int] | None = None,
) -> dict[str, Any]:
    rows = read_jsonl(plan_path)
    issues = validate_plan(rows, max_cells=max_cells)
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = output_dir / META_DIRNAME
    output_stem = "real_case_formal" if "formal" in output_dir.name.lower() else "real_case_smoke"
    status_path = output_dir / STATUS_DIRNAME / f"{output_stem}_status.jsonl"
    raw_path = output_dir / RAW_DIRNAME / f"{output_stem}_raw.jsonl"
    log_path = output_dir / LOG_DIRNAME / f"{output_stem}_run.log"
    if issues:
        metadata = {
            "phase": "phase10e",
            "status": "preflight_stopped",
            "preflight_issues": issues,
            "planned_cells": len(rows),
            "completed_cells": 0,
            "stop_reason": "preflight validation failed",
        }
        write_json(meta_dir / "real_case_smoke_run_metadata.json", metadata)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("Preflight stopped:\n" + "\n".join(issues) + "\n", encoding="utf-8")
        return metadata

    existing = read_existing_status(output_dir) if skip_existing else {}
    all_statuses = list(existing.values())
    started = time.time()
    for row in rows:
        if skip_existing and row["cell_key"] in existing:
            continue
        reason = stop_reason(all_statuses, rows, stop_limits=stop_limits)
        if reason:
            break
        status, raw = run_cell(row, timeout_s=timeout_s, max_tokens=max_tokens)
        append_jsonl(status_path, status)
        if raw is not None:
            append_jsonl(raw_path, raw)
        all_statuses.append(status)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(
                f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {status['cell_key']} "
                f"status={status['status']} success={status['mutation_success']} "
                f"hidden={status['hidden_business_rule_violation']} visible={status['visible_rule_exposed']}\n"
            )
        reason = stop_reason(all_statuses, rows, stop_limits=stop_limits)
        if reason:
            break
    final_reason = stop_reason(all_statuses, rows, stop_limits=stop_limits)
    completed_keys = {r.get("cell_key") for r in all_statuses if r.get("cell_key")}
    metadata = {
        "phase": "phase10e",
        "status": "completed" if len(completed_keys) >= len(rows) and final_reason is None else "partial_or_stopped",
        "planned_cells": len(rows),
        "completed_cells": len(completed_keys),
        "status_counts": dict(Counter(str(r.get("status")) for r in all_statuses)),
        "stop_reason": final_reason,
        "elapsed_s": round(time.time() - started, 2),
        "plan": display_path(plan_path),
        "output_dir": display_path(output_dir),
    }
    write_json(meta_dir / "real_case_smoke_run_metadata.json", metadata)
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-dir", type=Path, default=SMOKE)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=90)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--max-cells", type=int, default=24)
    parser.add_argument("--provider-error-limit", type=int, default=3)
    parser.add_argument("--timeout-limit", type=int, default=3)
    parser.add_argument("--failed-limit", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env()
    if args.max_workers != 1:
        raise SystemExit("Phase 10E smoke runner currently supports --max-workers 1 only")
    models = [m.strip() for m in str(args.models).split(",") if m.strip()]
    cases, audit_rows = build_cases_and_audit()
    write_audit(cases, audit_rows)
    if not args.plan.exists():
        rows = build_plan(cases, models=models, seed=args.seed)
        write_plan(args.plan, rows)
    else:
        rows = read_jsonl(args.plan)
    if args.prepare_only:
        print(
            json.dumps(
                {
                    "phase": "phase10e",
                    "prepared": True,
                    "audit": str(AUDIT_JSON),
                    "plan": str(args.plan),
                    "planned_cells": len(rows),
                    "selected_cases": [c["case_id"] for c in cases if c.get("selected_for_smoke")],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    metadata = run_plan(
        args.plan,
        args.output_dir,
        args.skip_existing,
        timeout_s=args.timeout_s,
        max_tokens=args.max_tokens,
        max_cells=args.max_cells,
        stop_limits={
            "provider_error": args.provider_error_limit,
            "timeout": args.timeout_limit,
            "failed": args.failed_limit,
        },
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
