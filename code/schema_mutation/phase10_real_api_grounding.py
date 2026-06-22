"""Build Phase 10A real-API evolution grounding artifacts.

The corpus produced by this script is intentionally lightweight and
conservative. It samples official public changelogs/release notes, stores only
short evidence snippets, and marks automatically inferred labels for human
review when the changelog text is ambiguous. It does not claim production
incident frequency or real agent failures.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
import textwrap
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "runs" / "schema_mutation" / "phase10" / "real_api_grounding"
USER_AGENT = "schema-mutation-phase10-grounding/1.0 (+public changelog sampling)"


@dataclass(frozen=True)
class Source:
    provider: str
    url: str
    source_type: str
    parser: str
    limit: int = 25


SOURCES = [
    Source("Stripe", "https://docs.stripe.com/changelog.md", "changelog", "markdown_table", 30),
    Source("GitHub", "https://github.blog/changelog/feed/", "changelog", "rss", 20),
    Source("Shopify", "https://shopify.dev/changelog", "changelog", "html", 20),
    Source("Slack", "https://docs.slack.dev/changelog/", "changelog", "html", 18),
    Source("Anthropic", "https://docs.anthropic.com/en/release-notes/api", "release_note", "html", 16),
    Source("OpenAI", "https://platform.openai.com/docs/changelog", "changelog", "html", 16),
    Source("Twilio", "https://www.twilio.com/en-us/changelog", "changelog", "html", 18),
    Source("Square", "https://developer.squareup.com/docs/changelog/connect", "changelog", "html", 18),
    Source("Microsoft Graph", "https://developer.microsoft.com/en-us/graph/changelog", "changelog", "html", 18),
    Source("Google Cloud", "https://cloud.google.com/release-notes", "release_note", "html", 18),
    Source("Meta Graph API", "https://developers.facebook.com/docs/graph-api/changelog/", "changelog", "html", 14),
    Source("AWS EC2", "https://docs.aws.amazon.com/AWSEC2/latest/APIReference/DocumentHistory.html", "release_note", "html", 12),
]


CANDIDATE_KEYWORDS = {
    "semantic": [
        "default",
        "behavior",
        "behaviour",
        "no longer",
        "now",
        "automatically",
        "eligible",
        "eligibility",
        "policy",
        "refund",
        "payment",
        "billing",
        "tax",
        "duties",
        "fee",
        "currency",
        "locale",
        "timezone",
        "region",
        "unit",
        "scale",
        "rounding",
        "minimum",
        "maximum",
        "calculate",
        "calculation",
        "interpret",
    ],
    "schema": [
        "field",
        "parameter",
        "property",
        "enum",
        "required",
        "removed",
        "renamed",
        "response",
        "object",
        "schema",
        "type",
    ],
    "protocol": [
        "rate limit",
        "authentication",
        "permission",
        "scope",
        "pagination",
        "webhook",
        "timeout",
        "retry",
        "429",
        "403",
        "400",
        "error",
        "quota",
        "deprecation",
    ],
    "surface": ["documentation", "description", "label", "name", "format", "display"],
}

BAD_TITLE_PATTERNS = [
    "terms of service",
    "privacy policy",
    "responsible disclosure",
    "terms and policies",
    "developer terms",
    "developer integration",
    "community",
    "cookbook",
    "learn docs",
    "programs, meetups",
    "built for builders",
    "enterprise scale",
    "privacy and security",
    "support for ai marketplace",
    "microsoft store",
    "certified refurbished",
    "english (united states)",
    "product changelog and announcements",
    "rss updates",
    "view all tags",
    "release notes for claude apps",
    "release notes stay organized",
    "subscribe to changelog",
    "get real-time notifications",
    "see additions and changes",
]

BAD_URL_PATTERNS = [
    "javascript:",
    "legal/",
    "/privacy",
    "/responsible-disclosure",
    "/community",
    "/cookbook",
    "microsoft.com/en-us/store",
    "techcommunity.microsoft.com",
    "wikipedia.org",
]


def _fetch(source: Source) -> tuple[str | None, dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    meta: dict[str, Any] = {
        "provider": source.provider,
        "url": source.url,
        "status": None,
        "error": None,
        "bytes": 0,
    }
    try:
        response = requests.get(source.url, headers=headers, timeout=30)
        meta["status"] = response.status_code
        meta["content_type"] = response.headers.get("content-type")
        meta["bytes"] = len(response.content)
        if response.status_code >= 400:
            meta["error"] = f"http_{response.status_code}"
            return None, meta
        return response.text, meta
    except Exception as exc:  # noqa: BLE001
        meta["error"] = f"{type(exc).__name__}: {exc}"
        return None, meta


def _clean(text: str) -> str:
    if "<" in (text or "") and ">" in (text or ""):
        try:
            text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
        except Exception:
            pass
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _short_snippet(text: str, max_words: int = 24) -> str:
    words = _clean(text).split()
    return " ".join(words[:max_words])


def _hash_id(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _looks_relevant(title: str, body: str) -> bool:
    low = f"{title} {body}".lower()
    if len(low) < 20:
        return False
    if any(p in low for p in BAD_TITLE_PATTERNS):
        return False
    return any(kw in low for group in CANDIDATE_KEYWORDS.values() for kw in group)


def _extract_date(text: str) -> str:
    patterns = [
        r"\b20\d{2}-\d{2}-\d{2}\b",
        r"\b20\d{2}-\d{2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+20\d{2}\b",
        r"\b20\d{2}\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            return m.group(0)
    return "unknown"


def parse_rss(source: Source, text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    root = ET.fromstring(text)
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else root.findall(".//item")
    for item in items:
        title = _clean(item.findtext("title") or "")
        link = _clean(item.findtext("link") or source.url)
        date = _clean(item.findtext("pubDate") or "")
        desc = _clean(item.findtext("description") or "")
        if _looks_relevant(title, desc):
            rows.append({"title": title, "url": link, "date": date or _extract_date(desc), "body": desc})
        if len(rows) >= source.limit:
            break
    return rows


def parse_markdown_table(source: Source, text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_date = "unknown"
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("## "):
            current_date = _extract_date(line)
        if not line.startswith("| ["):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", cells[0])
        if not m:
            continue
        title, href = _clean(m.group(1)), m.group(2)
        body = " | ".join(cells[1:4])
        if _looks_relevant(title, body):
            rows.append(
                {
                    "title": title,
                    "url": urljoin(source.url, href),
                    "date": current_date,
                    "body": _clean(body),
                }
            )
        if len(rows) >= source.limit:
            break
    return rows


def parse_html(source: Source, text: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        tag.decompose()
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    candidates = []
    for tag in soup.find_all(["article", "h1", "h2", "h3", "li", "p", "a"], limit=5000):
        href = tag.get("href") if hasattr(tag, "get") else None
        text_low = _clean(tag.get_text(" ", strip=True)).lower()
        href_low = str(href or "").lower()
        if href and not any(x in href_low for x in ("changelog", "release", "docs/", "graph-api", "api")):
            continue
        if href and any(p in href_low for p in BAD_URL_PATTERNS):
            continue
        if any(p in text_low for p in BAD_TITLE_PATTERNS):
            continue
        candidates.append(tag)
    for node in candidates:
        title = _clean(node.get_text(" ", strip=True))
        if not (18 <= len(title) <= 220):
            continue
        if title.lower() in seen:
            continue
        seen.add(title.lower())
        href = node.get("href") if hasattr(node, "get") else None
        if not href:
            link = node.find("a", href=True)
            href = link["href"] if link else source.url
        url = urljoin(source.url, href)
        if any(p in url.lower() for p in BAD_URL_PATTERNS):
            continue
        body_parts = []
        nxt = node.find_next_sibling()
        for _ in range(2):
            if nxt is None:
                break
            body_parts.append(_clean(nxt.get_text(" ", strip=True)))
            nxt = nxt.find_next_sibling()
        body = _clean(" ".join(body_parts))[:500]
        if _looks_relevant(title, body):
            rows.append({"title": title, "url": url, "date": _extract_date(f"{title} {body}"), "body": body})
        if len(rows) >= source.limit:
            break
    return rows


def classify(title: str, body: str) -> dict[str, Any]:
    text = f"{title} {body}".lower()
    has_schema = any(kw in text for kw in CANDIDATE_KEYWORDS["schema"])
    has_protocol = any(kw in text for kw in CANDIDATE_KEYWORDS["protocol"])
    has_semantic = any(kw in text for kw in CANDIDATE_KEYWORDS["semantic"])
    has_surface = any(kw in text for kw in CANDIDATE_KEYWORDS["surface"])

    c_subclass = "none"
    if any(kw in text for kw in ["unit", "scale", "rounding", "minimum", "maximum", "precision", "amount", "fee", "digit", "digits"]):
        c_subclass = "C1_unit_scale"
    if any(kw in text for kw in ["currency", "locale", "timezone", "time zone", "region", "country", "language"]):
        c_subclass = "C2_currency_locale"
    if any(kw in text for kw in ["default", "automatically", "fallback", "behavior", "behaviour", "sort", "calculate", "calculation"]):
        c_subclass = "C3_default_behavior"
    if c_subclass == "none" and any(kw in text for kw in ["eligible", "eligibility", "policy", "no longer", "allowed", "require", "refund", "payment", "billing", "tax", "duties"]):
        c_subclass = "C4_business_rule"

    if has_semantic and has_schema:
        taxonomy = "mixed"
    elif has_semantic:
        taxonomy = "C"
    elif has_schema:
        taxonomy = "B"
    elif has_protocol:
        taxonomy = "D"
    elif has_surface:
        taxonomy = "A"
    else:
        taxonomy = "unclear"

    if has_protocol and taxonomy == "C" and c_subclass == "none":
        taxonomy = "D"
    if has_protocol and has_semantic:
        taxonomy = "mixed"

    schema_visible = True if taxonomy in {"B", "mixed"} and has_schema else False if taxonomy == "C" else "unknown"
    runtime_visible = True if any(kw in text for kw in ["error", "400", "403", "429", "warning", "response"]) else "unknown"
    relevance = "high" if taxonomy in {"C", "mixed", "D"} else "medium" if taxonomy == "B" else "low"
    confidence = "high" if taxonomy == "C" and c_subclass != "none" and not has_schema else "medium" if taxonomy != "unclear" else "low"
    if _extract_date(f"{title} {body}") == "unknown" and taxonomy == "C":
        confidence = "medium"
    needs_review = confidence != "high" or taxonomy in {"mixed", "unclear"}

    rationale = {
        "C": f"Semantic behavior keyword matched; subclass={c_subclass}.",
        "B": "Schema-contract keyword matched.",
        "D": "Protocol/operational keyword matched.",
        "A": "Surface/representation keyword matched.",
        "mixed": f"Both schema/protocol and semantic keywords matched; subclass={c_subclass}.",
        "unclear": "Insufficient automated evidence for a confident taxonomy label.",
    }[taxonomy]
    return {
        "taxonomy_class": taxonomy,
        "c_subclass": c_subclass if taxonomy in {"C", "mixed"} else "none",
        "schema_visible": schema_visible,
        "runtime_visible": runtime_visible,
        "agent_task_relevance": relevance,
        "confidence": confidence,
        "label_rationale": rationale,
        "needs_human_review": needs_review,
    }


def collect_corpus() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fetch_log: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    for source in SOURCES:
        text, meta = _fetch(source)
        fetch_log.append(meta)
        if text is None:
            continue
        if source.parser == "rss":
            raw_entries = parse_rss(source, text)
        elif source.parser == "markdown_table":
            raw_entries = parse_markdown_table(source, text)
        else:
            raw_entries = parse_html(source, text)
        for idx, raw in enumerate(raw_entries, 1):
            classified = classify(raw["title"], raw.get("body", ""))
            entry_id = f"{source.provider.lower().replace(' ', '_')}_{_hash_id(raw['title'], raw.get('url'), idx)}"
            body = _clean(raw.get("body", ""))
            entries.append(
                {
                    "entry_id": entry_id,
                    "provider": source.provider,
                    "source_type": source.source_type,
                    "url": raw.get("url") or source.url,
                    "date": raw.get("date") or "unknown",
                    "title": raw["title"],
                    "short_paraphrase": paraphrase(raw["title"], classified),
                    "evidence_snippet": _short_snippet(body or raw["title"]),
                    **classified,
                }
            )
    # Deduplicate title+provider pairs while preserving provider diversity.
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        key = (entry["provider"], entry["title"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    deduped.sort(key=lambda e: (e["provider"], str(e.get("date")), e["title"]))
    return deduped, fetch_log


def paraphrase(title: str, classified: dict[str, Any]) -> str:
    taxonomy = classified["taxonomy_class"]
    if taxonomy == "C":
        return f"Official changelog entry indicates semantic behavior relevant to {classified['c_subclass']}."
    if taxonomy == "mixed":
        return f"Official changelog entry appears to combine schema/protocol edits with semantic behavior changes."
    if taxonomy == "B":
        return "Official changelog entry indicates a schema-contract change."
    if taxonomy == "D":
        return "Official changelog entry indicates an operational or protocol behavior change."
    if taxonomy == "A":
        return "Official changelog entry indicates a surface or representation change."
    return "Official changelog entry is retained for review but is not confidently classified."


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def summarize(entries: list[dict[str, Any]], fetch_log: list[dict[str, Any]]) -> dict[str, Any]:
    by_provider = collections.Counter(e["provider"] for e in entries)
    by_class = collections.Counter(e["taxonomy_class"] for e in entries)
    by_sub = collections.Counter(e["c_subclass"] for e in entries if e["taxonomy_class"] in {"C", "mixed"})
    schema_invisible_c = [
        e for e in entries
        if e["taxonomy_class"] == "C" and e["schema_visible"] is False and e["confidence"] in {"high", "medium"}
    ]
    high_c = [
        e for e in entries
        if e["taxonomy_class"] == "C" and e["confidence"] == "high"
    ]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_entries": len(entries),
        "providers_successful": sorted(by_provider),
        "provider_count": len(by_provider),
        "entries_by_provider": dict(by_provider),
        "entries_by_taxonomy_class": dict(by_class),
        "c_class_entries_by_subclass": dict(by_sub),
        "schema_invisible_c_class_candidates": len(schema_invisible_c),
        "high_confidence_c_class_examples": len(high_c),
        "runtime_visible_distribution": dict(collections.Counter(str(e["runtime_visible"]) for e in entries)),
        "fetch_log": fetch_log,
        "top_c_examples": high_c[:10],
        "limitations": [
            "Automatic labels are conservative and require human review before paper integration.",
            "This is a public-changelog corpus estimate, not a production incident frequency estimate.",
            "Some provider pages are dynamic; parser failures or noisy entries are recorded in fetch_log.",
        ],
    }


def select_case_candidates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Hand-pick from the fetched corpus using title patterns that make a clear
    # before/after wrapper feasible. The entries still come from official
    # sources; this only avoids choosing noisy navigation snippets.
    preferred_patterns = [
        ("C3_default_behavior", re.compile(r"safer .*defaults|will default|default to", re.I)),
        ("C1_unit_scale", re.compile(r"minimum cacheable prompt length|15 digits|unit|scale", re.I)),
        ("C4_business_rule", re.compile(r"eligibility|card brand restrictions|no longer billed|data retention", re.I)),
        ("C2_currency_locale", re.compile(r"regional endpoint|data residency|all regions|currency|locale", re.I)),
    ]
    selected: list[dict[str, Any]] = []
    for subclass, pattern in preferred_patterns:
        candidates = [
            e for e in entries
            if e["taxonomy_class"] == "C"
            and e["c_subclass"] == subclass
            and e["confidence"] in {"high", "medium"}
            and str(e.get("url", "")).startswith("http")
            and not any(p in str(e.get("title", "")).lower() for p in BAD_TITLE_PATTERNS)
            and pattern.search(str(e.get("title", "")))
        ]
        if not candidates:
            continue
        # Prefer dated entries, then non-AI/business APIs where available.
        candidates.sort(key=lambda e: (e.get("date") == "unknown", e["provider"] in {"OpenAI", "Anthropic"}, len(e["title"])))
        e = candidates[0]
        case_id = f"real_{subclass.lower()}_{_hash_id(e['provider'], e['title'])}"
        selected.append(
            {
                "case_id": case_id,
                "provider": e["provider"],
                "source_url": e["url"],
                "real_change_type": subclass.split("_", 1)[0],
                "before_semantics": "Use the pre-change behavior described or implied by the official changelog.",
                "after_semantics": f"Official entry: {e['title']}",
                "why_schema_invisible_or_semantic": e["label_rationale"],
                "agent_task_template": task_template_for(subclass),
                "possible_tool_schema": "Keep endpoint name and JSON field types stable; change only runtime interpretation.",
                "possible_old_api_wrapper_behavior": old_behavior_for(subclass),
                "possible_new_api_wrapper_behavior": new_behavior_for(subclass, e),
                "possible_oracle": oracle_for(subclass),
                "expected_o0_failure_mode": "Syntactically valid call succeeds at the tool layer but final state violates changed semantics.",
                "expected_visible_recovery_condition": "Expose the changed rule as a structured policy error or migration note.",
                "risks": "Requires human review of the official entry before paper use; wrapper should not claim a real production outage.",
            }
        )
        if len(selected) >= 3:
            break
    return selected


def task_template_for(subclass: str) -> str:
    return {
        "C1_unit_scale": "Agent must choose an amount, quantity, weight, fee, or threshold whose unit/scale changed.",
        "C2_currency_locale": "Agent must make a payment, payout, report, or date/locale-sensitive choice under changed defaults.",
        "C3_default_behavior": "Agent omits an optional setting whose default behavior changed.",
        "C4_business_rule": "Agent must satisfy an eligibility, billing, payment, refund, or policy rule that changed.",
    }.get(subclass, "Agent task exercising the changed semantic behavior.")


def old_behavior_for(subclass: str) -> str:
    return {
        "C1_unit_scale": "Old wrapper interprets numeric value using original unit/scale.",
        "C2_currency_locale": "Old wrapper interprets currency/locale defaults using original region settings.",
        "C3_default_behavior": "Old wrapper applies the previous default when the optional field is omitted.",
        "C4_business_rule": "Old wrapper permits the previously accepted business-rule path.",
    }.get(subclass, "Old wrapper preserves pre-change semantics.")


def new_behavior_for(subclass: str, entry: dict[str, Any]) -> str:
    return f"New wrapper applies the official changed semantics summarized by: {entry['short_paraphrase']}"


def oracle_for(subclass: str) -> str:
    return {
        "C1_unit_scale": "Deterministically check final state value after unit/scale conversion.",
        "C2_currency_locale": "Check final currency/locale-sensitive state against the changed interpretation.",
        "C3_default_behavior": "Check that omitted optional fields produce the expected changed default outcome.",
        "C4_business_rule": "Check that final state satisfies the changed eligibility/policy rule.",
    }.get(subclass, "Deterministic final-state oracle for the changed semantics.")


def write_summary(summary: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    (OUT_DIR / "api_evolution_corpus_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Phase 10A Real API Evolution Corpus Summary",
        "",
        "This is a public-changelog corpus estimate, not a production incident frequency estimate.",
        "",
        f"- Total entries: {summary['total_entries']}",
        f"- Providers: {summary['provider_count']} ({', '.join(summary['providers_successful'])})",
        f"- Schema-invisible C-class candidates: {summary['schema_invisible_c_class_candidates']}",
        f"- High-confidence C-class examples: {summary['high_confidence_c_class_examples']}",
        "",
        "## Entries by Provider",
    ]
    for provider, n in sorted(summary["entries_by_provider"].items()):
        lines.append(f"- {provider}: {n}")
    lines += ["", "## Taxonomy Distribution"]
    for cls, n in sorted(summary["entries_by_taxonomy_class"].items()):
        lines.append(f"- {cls}: {n}")
    lines += ["", "## C-Class Subclasses"]
    for sub, n in sorted(summary["c_class_entries_by_subclass"].items()):
        lines.append(f"- {sub}: {n}")
    lines += ["", "## Top High-Confidence C-Class Examples"]
    for e in summary["top_c_examples"]:
        lines.append(f"- {e['provider']} | {e['date']} | {e['title']} | {e['c_subclass']} | {e['url']}")
    lines += ["", "## Case Candidates"]
    for c in candidates:
        lines.append(f"- {c['case_id']} ({c['provider']}): {c['real_change_type']} | {c['source_url']}")
    lines += ["", "## Limitations"]
    for item in summary["limitations"]:
        lines.append(f"- {item}")
    (OUT_DIR / "api_evolution_corpus_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cases(candidates: list[dict[str, Any]]) -> None:
    (OUT_DIR / "real_change_case_candidates.json").write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    lines = ["# Real Semantic-Change Case Candidates", ""]
    for c in candidates:
        lines += [
            f"## {c['case_id']}",
            "",
            f"- Provider: {c['provider']}",
            f"- Source: {c['source_url']}",
            f"- Type: {c['real_change_type']}",
            f"- Why semantic: {c['why_schema_invisible_or_semantic']}",
            f"- Task template: {c['agent_task_template']}",
            f"- Oracle: {c['possible_oracle']}",
            f"- Risks: {c['risks']}",
            "",
        ]
    (OUT_DIR / "real_change_case_candidates.md").write_text("\n".join(lines), encoding="utf-8")


def write_total_report_if_possible(summary: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    oracle_summary_path = ROOT / "runs" / "schema_mutation" / "phase10" / "oracle_validation" / "oracle_validation_summary.json"
    nonobvious_path = ROOT / "runs" / "schema_mutation" / "phase10" / "nonobviousness" / "nonobviousness_plan_report.md"
    oracle_summary = json.loads(oracle_summary_path.read_text(encoding="utf-8")) if oracle_summary_path.exists() else None
    lines = [
        "# Phase 10A Real Grounding Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- Real API evolution corpus generated: yes ({summary['total_entries']} entries, {summary['provider_count']} providers).",
        f"- High-confidence C-class examples found: {summary['high_confidence_c_class_examples']}.",
        f"- Real-change case candidates selected: {len(candidates)}.",
        f"- Oracle validation packet generated: {'yes' if oracle_summary_path.exists() else 'not yet'}.",
        f"- Non-obviousness control plan generated: {'yes' if nonobvious_path.exists() else 'not yet'}.",
        "- Blockers: none for planning; human review is required before paper integration.",
        "",
        "## 2. Real API Grounding Results",
        "",
        f"- Corpus size: {summary['total_entries']}",
        f"- Providers: {', '.join(summary['providers_successful'])}",
        f"- Taxonomy distribution: {summary['entries_by_taxonomy_class']}",
        f"- C-class subclass distribution: {summary['c_class_entries_by_subclass']}",
        f"- Schema-invisible C-class candidates: {summary['schema_invisible_c_class_candidates']}",
        "",
        "Top examples are listed in `api_evolution_corpus_summary.md`.",
        "",
        "## 3. Real-Change Case Candidates",
    ]
    for c in candidates:
        lines.append(f"- {c['case_id']}: {c['provider']} {c['real_change_type']} ({c['source_url']})")
    lines += ["", "## 4. Oracle Validation"]
    if oracle_summary:
        lines += [
            f"- Total sampled records: {oracle_summary.get('total_samples')}",
            f"- Sample counts: {oracle_summary.get('sample_counts')}",
            f"- Baseline oracle violation rate: {oracle_summary.get('baseline_oracle_violation_rate')}",
            f"- Suspicious samples: {oracle_summary.get('suspicious_count')}",
        ]
    else:
        lines.append("- Not generated yet.")
    lines += [
        "",
        "## 5. Non-Obviousness Control Plan",
        "",
        f"- Plan report: {'generated' if nonobvious_path.exists() else 'not generated yet'}",
        "- Recommended next action: inspect smoke shard manually, then run only the smoke shard in Phase 10B.",
        "",
        "## 6. What Not To Claim Yet",
        "",
        "- Do not claim production frequency yet; this corpus samples public changelogs.",
        "- Do not claim human-validated oracle precision until manual review is done.",
        "- Do not claim stronger reasoning fails until Phase 10B runs the non-obviousness controls.",
        "- Do not merge real API grounding into the paper until case candidates are reviewed.",
    ]
    out = ROOT / "runs" / "schema_mutation" / "phase10" / "phase10a_real_grounding_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    entries, fetch_log = collect_corpus()
    write_jsonl(OUT_DIR / "api_evolution_corpus.jsonl", entries)
    (OUT_DIR / "source_fetch_log.json").write_text(
        json.dumps(fetch_log, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    summary = summarize(entries, fetch_log)
    candidates = select_case_candidates(entries)
    write_cases(candidates)
    write_summary(summary, candidates)
    write_total_report_if_possible(summary, candidates)
    print(f"entries={len(entries)} providers={summary['provider_count']} out={OUT_DIR}")
    print(f"high_confidence_c={summary['high_confidence_c_class_examples']} schema_invisible_c={summary['schema_invisible_c_class_candidates']}")
    return 0 if len(entries) >= 100 and summary["provider_count"] >= 8 else 2


if __name__ == "__main__":
    raise SystemExit(main())
