"""Generate lightweight changelog grounding artifacts for mutation realism.

This script intentionally does not claim that public API changes caused real
agent failures. It only maps short, official changelog/release-note excerpts to
the paper's mutation taxonomy to support plausibility grounding.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = REPO_ROOT / "runs" / "schema_mutation" / "changelog_realism"
TABLE_DIR = REPO_ROOT / "IEEE_Conference_Template" / "tables"

RUBRIC = {
    "A": {
        "name": "Surface / representation",
        "rules": [
            "naming changes",
            "date/time format changes",
            "field representation changes",
            "documentation wording changes",
            "description edits",
        ],
    },
    "B": {
        "name": "Schema-contract",
        "rules": [
            "required field added/removed",
            "parameter type changed",
            "enum value added/removed/renamed",
            "response field added/removed/renamed",
            "endpoint signature changed",
        ],
    },
    "C": {
        "name": "Semantic-contract",
        "rules": [
            "unit/scale behavior changed",
            "currency/locale behavior changed",
            "default behavior changed",
            "eligibility/business policy changed",
            "refund/cancel/payment/fare/access rule changed",
            "behavior changed while schema may remain stable",
        ],
    },
    "D": {
        "name": "Protocol / operational",
        "rules": [
            "pagination behavior changed",
            "rate limit changed",
            "authentication/permission changed",
            "error format changed",
            "timeout/retry behavior changed",
            "operational quota / availability behavior changed",
        ],
    },
}


def curated_items() -> list[dict[str, Any]]:
    """Return manually curated mappings from fetched official changelogs.

    The excerpt field is deliberately short. Ambiguous mappings are flagged for
    manual review instead of being treated as finished annotation.
    """
    return [
        {
            "item_id": "openai_2026_04_24_reasoning_default",
            "source": "OpenAI",
            "url": "https://developers.openai.com/api/docs/changelog",
            "date": "2026-04-24",
            "title": "GPT-5.5 API release notes",
            "raw_text_excerpt": "Reasoning effort now defaults to medium.",
            "change_summary": "A model parameter default changed while the request shape can remain unchanged.",
            "taxonomy_class": "C",
            "mutation_type": "C3_default_behavior_drift",
            "schema_visible": False,
            "semantic_change": True,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "Default-setting changes can alter behavior without requiring schema edits.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "anthropic_2026_05_28_sampling_error",
            "source": "Anthropic",
            "url": "https://platform.claude.com/docs/en/release-notes/overview",
            "date": "2026-05-28",
            "title": "Sampling parameter validation for Opus 4.8",
            "raw_text_excerpt": "non-default sampling parameters return a 400 error.",
            "change_summary": "Requests accepted by prior behavior can become rejected for a model.",
            "taxonomy_class": "D",
            "mutation_type": "D5_error_validation_change",
            "schema_visible": False,
            "semantic_change": True,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "The visible request schema may be stable, but runtime validation/error behavior changes.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "anthropic_top_p_default",
            "source": "Anthropic",
            "url": "https://platform.claude.com/docs/en/release-notes/overview",
            "date": "unknown",
            "title": "Default top_p changed",
            "raw_text_excerpt": "default top_p changed from 0.999 to 0.99.",
            "change_summary": "A sampling default changed while API calls can omit the parameter.",
            "taxonomy_class": "C",
            "mutation_type": "C3_default_behavior_drift",
            "schema_visible": False,
            "semantic_change": True,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "low",
            "rationale": "Default changes are semantically relevant, but the exact release-note date needs manual confirmation.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "twilio_sendgrid_2025_12_09_rate_limit",
            "source": "Twilio SendGrid",
            "url": "https://www.twilio.com/en-us/changelog/rate-limit-change-for-the-twilio-sendgrid-email-activity-api",
            "date": "2025-12-09",
            "title": "Email Activity API rate limit change",
            "raw_text_excerpt": "API rate limit will be reduced to 6 requests/minute.",
            "change_summary": "An endpoint's rate limit and 429 behavior changed.",
            "taxonomy_class": "D",
            "mutation_type": "D4_rate_limit_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Rate-limit changes are operational/protocol compatibility changes.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "twilio_taskrouter_2024_10_24_rate_limit",
            "source": "Twilio TaskRouter",
            "url": "https://www.twilio.com/en-us/changelog/taskrouter-endpoint-rate-limit-correction",
            "date": "2024-10-24",
            "title": "TaskRouter endpoint rate limit correction",
            "raw_text_excerpt": "requests will be throttled and return 429.",
            "change_summary": "Previously unthrottled or incorrectly documented endpoints reintroduced limits.",
            "taxonomy_class": "D",
            "mutation_type": "D4_rate_limit_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Runtime throttling affects client behavior without changing endpoint schemas.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "microsoft_graph_lesser_permissions",
            "source": "Microsoft Graph",
            "url": "https://learn.microsoft.com/en-us/graph/whats-new-earlier",
            "date": "unknown",
            "title": "Lesser privileged permissions for user APIs",
            "raw_text_excerpt": "move from Directory.AccessAsUser.All to lesser privileged permissions.",
            "change_summary": "Permission guidance and access requirements changed for API use.",
            "taxonomy_class": "D",
            "mutation_type": "D2_permission_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "Permission changes are operational compatibility changes and can affect agent credentials.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "shopify_2025_01_multilocation_removed",
            "source": "Shopify",
            "url": "https://shopify.dev/docs/api/release-notes/2025-01",
            "date": "2025-01",
            "title": "Deprecated multiLocation field removed",
            "raw_text_excerpt": "removed the deprecated multiLocation field.",
            "change_summary": "A response field was removed and a replacement field is recommended.",
            "taxonomy_class": "B",
            "mutation_type": "B4_output_shape_change",
            "schema_visible": True,
            "semantic_change": False,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Removing a response field is a schema-contract change.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "shopify_2025_01_cart_tax_checkout",
            "source": "Shopify",
            "url": "https://shopify.dev/docs/api/release-notes/2025-01",
            "date": "2025-01",
            "title": "Cart tax and duties calculation moved to checkout",
            "raw_text_excerpt": "Tax and duties are now calculated at checkout.",
            "change_summary": "A commerce calculation behavior moved to a later workflow stage.",
            "taxonomy_class": "C",
            "mutation_type": "C3_default_behavior_drift",
            "schema_visible": False,
            "semantic_change": True,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "Timing of business calculation can change outcomes without a direct request-shape change.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "shopify_2025_01_stringconnection_nodes",
            "source": "Shopify",
            "url": "https://shopify.dev/docs/api/release-notes/2025-01",
            "date": "2025-01",
            "title": "StringConnection includes nodes field",
            "raw_text_excerpt": "StringConnection now includes a nodes field.",
            "change_summary": "A connection response shape gained an additional field.",
            "taxonomy_class": "B",
            "mutation_type": "B4_output_shape_change",
            "schema_visible": True,
            "semantic_change": False,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Response field additions are schema-contract changes, even if often backward compatible.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "slack_2025_05_29_rate_limit",
            "source": "Slack",
            "url": "https://docs.slack.dev/changelog/2025/05/29/rate-limit-changes-for-non-marketplace-apps/",
            "date": "2025-05-29",
            "title": "Rate limit changes for non-Marketplace apps",
            "raw_text_excerpt": "new rate limits for conversations.history and conversations.replies.",
            "change_summary": "Selected endpoints moved to stricter limits for a class of apps.",
            "taxonomy_class": "D",
            "mutation_type": "D4_rate_limit_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Rate limit and app eligibility changes are operational changes.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "slack_2025_05_29_limit_param",
            "source": "Slack",
            "url": "https://docs.slack.dev/changelog/2025/05/29/rate-limit-changes-for-non-marketplace-apps/",
            "date": "2025-05-29",
            "title": "Conversation methods limit parameter changed",
            "raw_text_excerpt": "maximum and default limit value is now 15.",
            "change_summary": "Pagination/page-size behavior changed for affected methods.",
            "taxonomy_class": "D",
            "mutation_type": "D3_pagination_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Default and maximum page-size changes affect traversal behavior.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "github_2025_05_15_models_read",
            "source": "GitHub",
            "url": "https://github.blog/changelog/2025-05-15-modelsread-now-required-for-github-models-access/",
            "date": "2025-05-15",
            "title": "models:read now required for GitHub Models access",
            "raw_text_excerpt": "all tokens now require the models:read permission.",
            "change_summary": "A new permission requirement was added for model access.",
            "taxonomy_class": "D",
            "mutation_type": "D2_permission_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Permission changes can break otherwise valid API calls.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "square_2025_01_23_customer_cards_retired",
            "source": "Square",
            "url": "https://developer.squareup.com/docs/changelog/connect-logs/2025-01-23",
            "date": "2025-01-23",
            "title": "Customer cards field retired",
            "raw_text_excerpt": "the Customer cards field is retired.",
            "change_summary": "A customer response field was retired in favor of card-listing APIs.",
            "taxonomy_class": "B",
            "mutation_type": "B4_output_shape_change",
            "schema_visible": True,
            "semantic_change": False,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Field retirement maps directly to output schema evolution.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "square_2025_01_23_node_autopagination",
            "source": "Square",
            "url": "https://developer.squareup.com/docs/changelog/connect-logs/2025-01-23",
            "date": "2025-01-23",
            "title": "Node SDK auto-pagination support",
            "raw_text_excerpt": "Node.js SDK includes support for auto-pagination.",
            "change_summary": "Client traversal behavior changed for paginated APIs.",
            "taxonomy_class": "D",
            "mutation_type": "D3_pagination_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "Pagination handling affects protocol-level client behavior.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "square_2025_04_16_webhook_retry",
            "source": "Square",
            "url": "https://developer.squareup.com/docs/changelog/connect-logs/2025-04-16",
            "date": "2025-04-16",
            "title": "Webhook retry schedule changed",
            "raw_text_excerpt": "maximum of 11 retry attempts for up to 24 hours.",
            "change_summary": "Webhook retry policy changed, affecting event-delivery robustness.",
            "taxonomy_class": "D",
            "mutation_type": "D6_retry_timeout_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": True,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Retry schedules are operational compatibility behavior.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "square_2025_04_16_marketplace_eligibility",
            "source": "Square",
            "url": "https://developer.squareup.com/docs/changelog/connect-logs/2025-04-16",
            "date": "2025-03-27",
            "title": "App Marketplace seller eligibility requirement",
            "raw_text_excerpt": "minimum of five active Square sellers.",
            "change_summary": "A listing eligibility business rule was introduced.",
            "taxonomy_class": "C",
            "mutation_type": "C4_business_rule_drift",
            "schema_visible": False,
            "semantic_change": True,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "Eligibility policy changes map to business-rule drift.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "google_calendar_2024_05_30_fromgmail",
            "source": "Google Calendar",
            "url": "https://workspaceupdates.googleblog.com/2024/05/google-calendar-api-event-type-fromgmail.html",
            "date": "2024-05-30",
            "title": "Events from Gmail use fromGmail event type",
            "raw_text_excerpt": "eventType will return fromGmail instead of default.",
            "change_summary": "An API value representation changed for Gmail-derived events.",
            "taxonomy_class": "B",
            "mutation_type": "B3_enum_value_change",
            "schema_visible": True,
            "semantic_change": True,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "The returned enum-like value changes and may alter client branching behavior.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "google_calendar_2024_05_30_update_restriction",
            "source": "Google Calendar",
            "url": "https://workspaceupdates.googleblog.com/2024/05/google-calendar-api-event-type-fromgmail.html",
            "date": "2024-05-30",
            "title": "Events from Gmail update restrictions",
            "raw_text_excerpt": "will only allow updates to reminders, colorId, visibility.",
            "change_summary": "A new rule restricts which fields can be updated on a category of events.",
            "taxonomy_class": "C",
            "mutation_type": "C4_business_rule_drift",
            "schema_visible": False,
            "semantic_change": True,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "high",
            "rationale": "A category-specific update eligibility rule is semantic policy drift.",
            "annotator": "auto",
            "needs_manual_review": False,
        },
        {
            "item_id": "paypal_2023_01_15_billtozip_format",
            "source": "PayPal",
            "url": "https://developer.paypal.com/api/nvp-soap/payflow/integration-guide/reference/revision-history/",
            "date": "2023-01-15",
            "title": "BILLTOZIP field correction",
            "raw_text_excerpt": "BILLTOZIP is an alphanumeric value.",
            "change_summary": "Documentation clarified/corrected a field representation constraint.",
            "taxonomy_class": "A",
            "mutation_type": "A2_format_change",
            "schema_visible": False,
            "semantic_change": False,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "Representation constraints can affect prompt/tool usage even when schema type stays string-like.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "paypal_2023_01_15_transactionid_response",
            "source": "PayPal",
            "url": "https://developer.paypal.com/api/nvp-soap/payflow/integration-guide/reference/revision-history/",
            "date": "2023-01-15",
            "title": "TRANSACTIONID response parameter documented",
            "raw_text_excerpt": "Added the TRANSACTIONID response parameter.",
            "change_summary": "A response parameter was added to API documentation.",
            "taxonomy_class": "B",
            "mutation_type": "B4_output_shape_change",
            "schema_visible": True,
            "semantic_change": False,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "Response parameter additions map to schema/output-shape evolution.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "paypal_ach_new_accounts",
            "source": "PayPal",
            "url": "https://developer.paypal.com/api/nvp-soap/payflow/integration-guide/reference/revision-history/",
            "date": "unknown",
            "title": "ACH not available for new accounts",
            "raw_text_excerpt": "ACH is no longer available for new accounts.",
            "change_summary": "A payment capability became unavailable for a class of accounts.",
            "taxonomy_class": "C",
            "mutation_type": "C4_business_rule_drift",
            "schema_visible": False,
            "semantic_change": True,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "medium",
            "rationale": "Payment eligibility changes map to semantic business policy drift.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
        {
            "item_id": "openapi_nullable_clarification",
            "source": "OpenAPI",
            "url": "https://github.com/OAI/OpenAPI-Specification/blob/main/proposals/2019-10-31-Clarify-Nullable.md",
            "date": "2019-10-31",
            "title": "Clarify nullable semantics",
            "raw_text_excerpt": "Clarify the semantics of nullable.",
            "change_summary": "A specification clarification changed how a representation constraint is interpreted.",
            "taxonomy_class": "A",
            "mutation_type": "A3_documentation_semantics_change",
            "schema_visible": False,
            "semantic_change": True,
            "protocol_operational": False,
            "likely_agent_relevant": True,
            "confidence": "low",
            "rationale": "Specification wording changes can alter tool descriptions or validators, but mapping needs review.",
            "annotator": "auto",
            "needs_manual_review": True,
        },
    ]


def _counts(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(collections.Counter(str(item.get(key, "unknown")) for item in items).items()))


def _latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def build_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    class_examples: dict[str, list[dict[str, str]]] = {k: [] for k in RUBRIC}
    for item in items:
        cls = str(item["taxonomy_class"])
        if len(class_examples.setdefault(cls, [])) < 4:
            class_examples[cls].append(
                {
                    "source": str(item["source"]),
                    "title": str(item["title"]),
                    "mutation_type": str(item["mutation_type"]),
                    "confidence": str(item["confidence"]),
                }
            )

    return {
        "scope_note": (
            "Lightweight plausibility grounding only; not a frequency estimate, "
            "not a production incident study, and not evidence of real agent failures."
        ),
        "rubric": RUBRIC,
        "total_changelog_items": len(items),
        "count_by_source": _counts(items, "source"),
        "count_by_taxonomy_class": _counts(items, "taxonomy_class"),
        "count_by_mutation_type": _counts(items, "mutation_type"),
        "schema_visible": {
            "true": sum(1 for item in items if item["schema_visible"]),
            "false": sum(1 for item in items if not item["schema_visible"]),
        },
        "schema_invisible": sum(1 for item in items if not item["schema_visible"]),
        "semantic_change": {
            "true": sum(1 for item in items if item["semantic_change"]),
            "false": sum(1 for item in items if not item["semantic_change"]),
        },
        "likely_agent_relevant_count": sum(1 for item in items if item["likely_agent_relevant"]),
        "confidence_distribution": _counts(items, "confidence"),
        "needs_manual_review_count": sum(1 for item in items if item["needs_manual_review"]),
        "needs_manual_review_item_ids": [
            str(item["item_id"]) for item in items if item["needs_manual_review"]
        ],
        "examples_per_class": class_examples,
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "item_id",
        "source",
        "url",
        "date",
        "title",
        "raw_text_excerpt",
        "change_summary",
        "taxonomy_class",
        "mutation_type",
        "schema_visible",
        "semantic_change",
        "protocol_operational",
        "likely_agent_relevant",
        "confidence",
        "rationale",
        "annotator",
        "needs_manual_review",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def write_annotation_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "item_id",
        "source",
        "title",
        "excerpt",
        "url",
        "date",
        "annotator_taxonomy_class",
        "annotator_mutation_type",
        "annotator_schema_visible",
        "annotator_semantic_change",
        "annotator_confidence",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "item_id": row["item_id"],
                    "source": row["source"],
                    "title": row["title"],
                    "excerpt": row["raw_text_excerpt"],
                    "url": row["url"],
                    "date": row["date"],
                    "annotator_taxonomy_class": "",
                    "annotator_mutation_type": "",
                    "annotator_schema_visible": "",
                    "annotator_semantic_change": "",
                    "annotator_confidence": "",
                    "notes": "",
                }
            )


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Changelog Grounding for Mutation Realism",
        "",
        "This is a lightweight plausibility grounding artifact. It does not estimate "
        "production frequencies and does not claim that any listed API change caused "
        "an agent failure.",
        "",
        "## Rubric",
    ]
    for cls, spec in RUBRIC.items():
        lines.append(f"- {cls}. {spec['name']}: {', '.join(spec['rules'])}.")
    lines.extend(
        [
            "",
            "## Summary",
            f"- total changelog items: {summary['total_changelog_items']}",
            f"- count by source: {summary['count_by_source']}",
            f"- count by taxonomy class: {summary['count_by_taxonomy_class']}",
            f"- count by mutation type: {summary['count_by_mutation_type']}",
            f"- schema-visible: {summary['schema_visible']['true']}",
            f"- schema-invisible: {summary['schema_visible']['false']}",
            f"- semantic-change: {summary['semantic_change']['true']}",
            f"- likely agent relevant: {summary['likely_agent_relevant_count']}",
            f"- confidence distribution: {summary['confidence_distribution']}",
            f"- needs manual review: {summary['needs_manual_review_count']}",
            "",
            "## Examples Per Class",
        ]
    )
    for cls, examples in summary["examples_per_class"].items():
        lines.append(f"### {cls}. {RUBRIC[cls]['name']}")
        if not examples:
            lines.append("- TODO-HIGH: add public changelog examples before submission.")
            continue
        for ex in examples:
            lines.append(
                f"- {ex['source']}: {ex['title']} ({ex['mutation_type']}, {ex['confidence']})"
            )
    lines.extend(
        [
            "",
            "## Manual Review Queue",
        ]
    )
    if summary["needs_manual_review_item_ids"]:
        for item_id in summary["needs_manual_review_item_ids"]:
            lines.append(f"- {item_id}")
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_latex(path: Path, summary: dict[str, Any]) -> None:
    rows = []
    for cls in ["A", "B", "C", "D"]:
        spec = RUBRIC[cls]
        examples = summary["examples_per_class"].get(cls, [])
        sources = []
        for ex in examples:
            label = f"{ex['source']} ({ex['mutation_type']})"
            if label not in sources:
                sources.append(label)
        relevance = {
            "A": "Grounds surface and representation perturbations such as field-format or documentation-semantics changes.",
            "B": "Grounds schema-contract mutations such as response-field, enum, or endpoint-shape changes.",
            "C": "Grounds semantic drift such as defaults, eligibility rules, and business-policy changes.",
            "D": "Grounds protocol and operational drift such as rate limits, permissions, pagination, and retry behavior.",
        }[cls]
        rows.append(
            " & ".join(
                [
                    _latex_escape(f"{cls}. {spec['name']}"),
                    _latex_escape("; ".join(spec["rules"][:4])),
                    _latex_escape("; ".join(sources[:4]) or "TODO-HIGH"),
                    _latex_escape(relevance),
                ]
            )
            + r" \\"
        )

    text = "\n".join(
        [
            "% Auto-generated by code/schema_mutation/changelog_realism.py",
            r"\begin{table*}[t]",
            r"\caption{Lightweight changelog grounding for mutation realism. The mapping is not a frequency estimate and does not claim observed agent failures in these APIs.}",
            r"\label{tab:changelog-mapping}",
            r"\centering",
            r"\footnotesize",
            r"\begin{tabularx}{\textwidth}{p{0.15\textwidth}p{0.31\textwidth}p{0.24\textwidth}X}",
            r"\toprule",
            r"Class & Real changelog patterns & Example sources & Relevance to mutation taxonomy \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabularx}",
            r"\vspace{0.3em}",
            r"\emph{Note.} Items are auto-mapped from public changelogs and release notes; ambiguous rows remain marked for manual review in the released annotation CSV.",
            r"\end{table*}",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--table-dir", type=Path, default=TABLE_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    items = curated_items()
    summary = build_summary(items)
    if args.dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.table_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(args.out_dir / "changelog_items.jsonl", items)
    write_csv(args.out_dir / "changelog_items.csv", items)
    write_annotation_csv(args.out_dir / "changelog_items_for_annotation.csv", items)
    (args.out_dir / "changelog_mapping_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_markdown(args.out_dir / "changelog_mapping_summary.md", summary)
    write_latex(args.table_dir / "changelog_mapping_auto.tex", summary)

    print(f"items={len(items)}")
    print(f"out_dir={args.out_dir}")
    print(f"table={args.table_dir / 'changelog_mapping_auto.tex'}")
    print(f"class_counts={summary['count_by_taxonomy_class']}")
    print(f"needs_manual_review={summary['needs_manual_review_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
