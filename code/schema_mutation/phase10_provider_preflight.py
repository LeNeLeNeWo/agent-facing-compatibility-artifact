"""Provider preflight for Phase 10E-R1.

The script checks the intended Python environment and sends a tiny harmless
OpenAI-compatible chat request to each configured model. It writes a Markdown
report and does not print API keys or private endpoints.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "runs" / "schema_mutation" / "phase10" / "real_case_replay" / "smoke_r1" / "provider_preflight.md"
DEFAULT_MODELS = ["deepseek/deepseek-v4-flash", "dashscope/qwen-max"]

PROVIDERS = {
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


def sanitize(text: str) -> str:
    text = re.sub(r"https?://[^\s)]+", "[redacted-url]", text)
    for key, value in os.environ.items():
        if ("KEY" in key or "TOKEN" in key or "SECRET" in key) and value and len(value) >= 6:
            text = text.replace(value, "[redacted-secret]")
    return text[:700]


def provider_and_model(model_id: str) -> tuple[str, str]:
    if "/" not in model_id:
        return "", model_id
    return tuple(model_id.split("/", 1))  # type: ignore[return-value]


def provider_config(model_id: str) -> tuple[str, str, str | None, str]:
    provider, model = provider_and_model(model_id)
    cfg = PROVIDERS.get(provider)
    if cfg is None:
        return provider, model, None, ""
    api_key = <REDACTED_SECRET>(cfg["key"])
    base_url = os.getenv(cfg["base"]) or os.getenv(cfg["base_alias"]) or cfg["default_base"]
    return provider, model, api_key, base_url


def public_base_hint(base_url: str) -> str:
    if not base_url:
        return "unavailable"
    parsed = urlparse(base_url)
    host = parsed.hostname or "configured"
    return f"configured host={host}"


def check_model(model_id: str, timeout_s: int) -> dict[str, Any]:
    t0 = time.time()
    provider, model, api_key, base_url = provider_config(model_id)
    result: dict[str, Any] = {
        "model_id": model_id,
        "provider": provider,
        "key_present": bool(api_key),
        "base_hint": public_base_hint(base_url),
        "status": "not_run",
        "elapsed_s": 0.0,
        "error": None,
    }
    if OpenAI is None:
        result.update({"status": "failed", "error": "openai package unavailable"})
        return result
    if not provider or provider not in PROVIDERS:
        result.update({"status": "failed", "error": "unsupported provider prefix"})
        return result
    if not api_key:
        <REDACTED_SECRET>({"status": "provider_error", "error": f"{PROVIDERS[provider]['key']} not set"})
        return result
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_s, max_retries=0)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Reply with exactly OK."},
                {"role": "user", "content": "ping"},
            ],
            temperature=0.0,
            max_tokens=3,
        )
        text = (resp.choices[0].message.content or "").strip()
        result.update({"status": "ok", "response_nonempty": bool(text), "elapsed_s": round(time.time() - t0, 2)})
    except Exception as exc:  # noqa: BLE001
        low = str(exc).lower()
        status = "timeout" if "timeout" in low else "provider_error"
        result.update({"status": status, "error": sanitize(f"{type(exc).__name__}: {exc}"), "elapsed_s": round(time.time() - t0, 2)})
    return result


def write_report(path: Path, rows: list[dict[str, Any]], env: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 10E-R1 Provider Preflight",
        "",
        f"- Python executable: `{env['python_executable']}`",
        f"- Python version: `{env['python_version']}`",
        f"- tau_bench import: {env['tau_bench_ok']}",
        f"- tau_bench path: `{env.get('tau_bench_path') or 'n/a'}`",
        f"- openai import: {env['openai_ok']}",
        f"- dotenv loaded: {env['dotenv_loaded']}",
        "",
        "| model | key present | endpoint | status | elapsed | error |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['model_id']}` | {row['key_present']} | {row['base_hint']} | "
            f"{row['status']} | {row.get('elapsed_s', 0.0)} | {row.get('error') or ''} |"
        )
    lines.extend(
        [
            "",
            "No API keys or private endpoint URLs are printed in this report.",
            "No real Stripe/GitHub/third-party business API is called by this preflight.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout-s", type=int, default=45)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env()
    env: dict[str, Any] = {
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "dotenv_loaded": load_dotenv is not None,
        "openai_ok": OpenAI is not None,
        "tau_bench_ok": False,
        "tau_bench_path": None,
    }
    try:
        import tau_bench  # type: ignore

        env["tau_bench_ok"] = True
        env["tau_bench_path"] = getattr(tau_bench, "__file__", None)
    except Exception as exc:  # noqa: BLE001
        env["tau_bench_error"] = sanitize(f"{type(exc).__name__}: {exc}")
    models = [m.strip() for m in str(args.models).split(",") if m.strip()]
    rows = [check_model(model, timeout_s=args.timeout_s) for model in models] if env["tau_bench_ok"] else []
    write_report(args.output_md, rows, env)
    print(
        json.dumps(
            {
                "output_md": str(args.output_md),
                "tau_bench_ok": env["tau_bench_ok"],
                "openai_ok": env["openai_ok"],
                "status_counts": {s: sum(1 for r in rows if r.get("status") == s) for s in sorted({r.get("status") for r in rows})},
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if env["tau_bench_ok"] and all(r.get("status") == "ok" for r in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
