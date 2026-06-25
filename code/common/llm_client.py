"""MimoClient · OpenAI 兼容客户端封装

核心职责：
- 自动读取项目根目录 .env（MIMO_API_KEY / MIMO_BASE_URL / MIMO_MODEL）
- 统一的同步 chat / 并发 chat_batch 接口
- 自动重试（tenacity）+ 限流 + 简单 token usage 统计
- CLI 自检模式：python -m code.common.llm_client

设计原则：
- 不依赖任何 LLM 框架，只用 openai 官方 SDK
- 所有 pilot 都用 MimoClient()，不要直接调 openai.OpenAI()，便于统一切换
"""
from __future__ import annotations

import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from dotenv import load_dotenv
from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)
from tqdm import tqdm

# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

# 找项目根 .env：从本文件向上找第一个含 .env 的目录
def _find_dotenv() -> Optional[Path]:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


_dotenv_path = _find_dotenv()
if _dotenv_path is not None:
    load_dotenv(_dotenv_path, override=False)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_LEVEL = os.getenv("PILOT_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mimo")


# ---------------------------------------------------------------------------
# Usage tracker
# ---------------------------------------------------------------------------


@dataclass
class UsageTracker:
    n_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    errors: int = 0
    started_at: float = field(default_factory=time.time)
    _lock: Any = field(default_factory=lambda: __import__("threading").Lock(), repr=False)

    def add(self, prompt_t: int, completion_t: int) -> None:
        with self._lock:
            self.n_calls += 1
            self.prompt_tokens += prompt_t
            self.completion_tokens += completion_t

    def add_error(self) -> None:
        with self._lock:
            self.errors += 1

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def summary(self) -> dict[str, Any]:
        elapsed = time.time() - self.started_at
        return {
            "n_calls": self.n_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "errors": self.errors,
            "elapsed_seconds": round(elapsed, 2),
            "avg_latency_s": round(elapsed / max(self.n_calls, 1), 3),
        }


# ---------------------------------------------------------------------------
# MimoClient
# ---------------------------------------------------------------------------


class MimoClient:
    """OpenAI-compatible client targeting Mimo.

    Args:
        api_key:    overrides MIMO_API_KEY env var
        base_url:   overrides MIMO_BASE_URL env var
        model:      overrides MIMO_MODEL env var
        timeout:    request timeout seconds
        max_retries: tenacity retry attempts (also passed to openai SDK)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("MIMO_API_KEY")
        self.base_url = base_url or os.getenv("MIMO_BASE_URL")
        self.model = model or os.getenv("MIMO_MODEL", "mimo-v2.5-pro")
        self.timeout = float(timeout or os.getenv("PILOT_REQUEST_TIMEOUT", "60"))
        self.max_retries = int(max_retries or os.getenv("PILOT_MAX_RETRIES", "3"))

        if not self.api_key:
            raise RuntimeError(
                "MIMO_API_KEY 未设置。请检查项目根目录 .env，或显式传入 api_key 参数。"
            )

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=0,  # 我们自己用 tenacity 控制
        )
        self.usage = UsageTracker()
        logger.debug(
            "MimoClient initialized · base=%s · model=%s · timeout=%s",
            self.base_url,
            self.model,
            self.timeout,
        )

    # ----- core call -----

    @retry(
        stop=stop_after_attempt(6),                               # 5 次重试
        wait=wait_exponential_jitter(initial=2, max=60, jitter=2),  # 2,4,8,16,32,60s + 抖动
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _call_once(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, int]]:
        resp = self._client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature if temperature is not None
                        else float(os.getenv("PILOT_DEFAULT_TEMPERATURE", "0.7")),
            max_tokens=max_tokens or int(os.getenv("PILOT_DEFAULT_MAX_TOKENS", "2048")),
            **kwargs,
        )
        text = resp.choices[0].message.content or ""
        finish_reason = resp.choices[0].finish_reason
        # mimo-v2.5-pro 是 reasoning 模型；reasoning 占 max_tokens 时 content 会空
        if not text:
            rc = getattr(resp.choices[0].message, "reasoning_content", None) or ""
            reasoning_tokens = (
                getattr(getattr(resp.usage, "completion_tokens_details", None),
                        "reasoning_tokens", 0) or 0
            )
            logger.warning(
                "empty content (finish=%s, reasoning_tokens=%d, reasoning_len=%d). "
                "请增大 max_tokens；reasoning 已截断 content。",
                finish_reason, reasoning_tokens, len(rc),
            )
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(resp.usage, "completion_tokens", 0) or 0,
        }
        return text, usage

    # ----- public sync API -----

    def chat(
        self,
        prompt: str | list[dict[str, str]],
        *,
        system: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Single-turn chat. ``prompt`` 可以是 str 或 messages list。"""
        if isinstance(prompt, str):
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt

        try:
            text, usage = self._call_once(messages, **kwargs)
            self.usage.add(usage["prompt_tokens"], usage["completion_tokens"])
            return text
        except Exception as e:
            self.usage.add_error()
            logger.error("chat() failed: %s", e)
            raise

    def chat_batch(
        self,
        prompts: Iterable[str | list[dict[str, str]]],
        *,
        n_workers: int = 8,
        progress: bool = True,
        **kwargs: Any,
    ) -> list[Optional[str]]:
        """Concurrent batch chat. 失败位置返回 None，方便调用方降级处理。"""
        prompts = list(prompts)
        results: list[Optional[str]] = [None] * len(prompts)

        def _worker(i: int, p: Any) -> tuple[int, Optional[str]]:
            try:
                return i, self.chat(p, **kwargs)
            except Exception as e:
                logger.warning("batch item %d failed: %s", i, e)
                return i, None

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(_worker, i, p) for i, p in enumerate(prompts)]
            iterator = as_completed(futures)
            if progress:
                iterator = tqdm(iterator, total=len(futures), desc="mimo")
            for fut in iterator:
                i, text = fut.result()
                results[i] = text
        return results


# ---------------------------------------------------------------------------
# DeepSeekClient (added 2026-06-10)
# ---------------------------------------------------------------------------


class DeepSeekClient(MimoClient):
    """OpenAI-compatible client targeting DeepSeek.

    Reads DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL from env.
    Defaults: base_url=https://api.deepseek.com/v1, model=deepseek-v4-flash.

    Usage:
        c = DeepSeekClient()
        ans = c.chat("hello", temperature=0.0)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY 未设置。请检查项目根目录 .env，或显式传入 api_key 参数。"
            )
        super().__init__(
            api_key=api_key,
            base_url=base_url or os.getenv(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
            ),
            model=model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# DashScopeClient (added 2026-06-10 evening)
# ---------------------------------------------------------------------------


class DashScopeClient(MimoClient):
    """OpenAI-compatible client targeting Alibaba DashScope (百炼).

    DashScope hosts many models behind one endpoint:
      - Alibaba: qwen3.7-max, qwen-max, gui-plus
      - Meta:    llama-4-maverick-17b-128e-instruct
      - Moonshot: kimi-k2.6
      - Zhipu:   glm-5.1
      - MiniMax: MiniMax-M2.5
      - Baichuan: baichuan2-turbo

    Reads DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL / DASHSCOPE_MODEL from env.
    Defaults: base_url=https://dashscope.aliyuncs.com/compatible-mode/v1.

    Usage:
        c = DashScopeClient(model="llama-4-maverick-17b-128e-instruct")
        ans = c.chat("hello")

    Note: pass `model=` explicitly because there is no single sensible
    default — callers usually want to test multiple model IDs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY 未设置。请检查项目根目录 .env，"
                "或显式传入 api_key 参数。"
            )
        super().__init__(
            api_key=api_key,
            base_url=base_url or os.getenv(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            model=model or os.getenv("DASHSCOPE_MODEL", "qwen-max"),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# SiliconFlowClient (added 2026-06-10 evening)
# ---------------------------------------------------------------------------


class SiliconFlowClient(MimoClient):
    """OpenAI-compatible client targeting SiliconFlow / SiliconCloud.

    Endpoint: https://api.siliconflow.cn/v1
    Model ID convention: '<vendor>/<model>' e.g. 'deepseek-ai/DeepSeek-V3.2',
    'meta-llama/Meta-Llama-3.1-70B-Instruct' (if still hosted), 'Qwen/Qwen2.5-...'.

    Reads SILICONFLOW_API_KEY / SILICONFLOW_BASE_URL / SILICONFLOW_MODEL.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        if not api_key:
            raise RuntimeError(
                "SILICONFLOW_API_KEY 未设置。请检查项目根目录 .env，"
                "或显式传入 api_key 参数。"
            )
        super().__init__(
            api_key=api_key,
            base_url=base_url or os.getenv(
                "SILICONFLOW_BASE_URL",
                "https://api.siliconflow.cn/v1",
            ),
            model=model or os.getenv(
                "SILICONFLOW_MODEL",
                "deepseek-ai/DeepSeek-V3.2",
            ),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Family factory
# ---------------------------------------------------------------------------


def make_client(family: str = "mimo", **kwargs: Any) -> MimoClient:
    """Factory to create an LLM client by family name.

    Args:
        family: 'mimo' | 'deepseek' | 'dashscope' | 'siliconflow' (case-insensitive)
        **kwargs: forwarded to the client class (e.g. model='meta-llama/...')

    Returns:
        Subclass of MimoClient with appropriate defaults.

    Raises:
        ValueError: if family is unknown
    """
    f = family.lower().strip()
    if f == "mimo":
        return MimoClient(**kwargs)
    if f == "deepseek":
        return DeepSeekClient(**kwargs)
    if f == "dashscope":
        return DashScopeClient(**kwargs)
    if f in ("siliconflow", "silicon", "sf"):
        return SiliconFlowClient(**kwargs)
    raise ValueError(
        f"Unknown LLM family: {family!r}. "
        f"Supported: 'mimo', 'deepseek', 'dashscope', 'siliconflow'."
    )


# ---------------------------------------------------------------------------
# Self-test CLI
# ---------------------------------------------------------------------------


def _self_test() -> int:
    """python -m code.common.llm_client [--family mimo|deepseek] → 自检 LLM 连接。"""
    # parse --family from argv
    family = "mimo"
    if "--family" in sys.argv:
        try:
            idx = sys.argv.index("--family")
            family = sys.argv[idx + 1]
        except (ValueError, IndexError):
            pass

    try:
        c = make_client(family)
        ans = c.chat(
            "请用一句话回答：你是哪个模型？",
            temperature=0.0,
            max_tokens=1024,  # reasoning 模型需要给 reasoning_content 留余量
        )
        print(
            f"[{type(c).__name__}] OK · family={family} · model={c.model} · base={c.base_url}\n"
            f"[response] {ans.strip()}\n"
            f"[usage] {c.usage.summary()}"
        )
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"[{family}] FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_self_test())
