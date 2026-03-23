"""LLM服务模块"""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM
from ..config import get_settings

# 全局LLM实例
_llm_instance = None
_llm_signature = None


def _normalize_openai_compatible_base_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if not url:
        return url

    # OpenAI Python SDK expects base_url like https://host/v1
    # If user provides only scheme+host (no path), append /v1.
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        path = parsed.path or ""

        # 常见误配：把具体接口路径写进了base_url，导致后续再拼接一次
        # 例如 base_url=.../v1/chat/completions -> 实际请求变成 /v1/chat/completions/chat/completions
        normalized_path = path
        lower_path = normalized_path.lower().rstrip("/")
        if lower_path.endswith("/chat/completions"):
            normalized_path = normalized_path[: -(len("/chat/completions"))]
            if not normalized_path:
                normalized_path = "/"

        parsed = parsed._replace(path=normalized_path)
        url = parsed.geturl()

        if parsed.path in {"", "/"}:
            return url.rstrip("/") + "/v1"

    return url


def _mask_key(api_key: str) -> str:
    key = (api_key or "").strip()
    if not key:
        return "<empty>"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}***{key[-4:]}(len={len(key)})"


def get_llm() -> HelloAgentsLLM:
    """
    获取LLM实例(单例模式)
    
    Returns:
        HelloAgentsLLM实例
    """
    global _llm_instance
    global _llm_signature
    
    # 重新加载 backend/.env（开发时改Key不需要依赖文件watch/重启）
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=True)

    settings = get_settings()

    # 以LLM_*为准（避免PowerShell里设置了OPENAI_API_KEY时覆盖LLM_API_KEY）
    env_model = (os.getenv("LLM_MODEL_ID") or settings.openai_model or "").strip()
    env_api_key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    env_base_url = (os.getenv("LLM_BASE_URL") or settings.openai_base_url or "").strip()
    env_base_url = _normalize_openai_compatible_base_url(env_base_url)

    signature = (env_model, env_base_url, env_api_key)
    if _llm_instance is None or _llm_signature != signature:
        _llm_signature = signature

        # 显式传参，避免HelloAgentsLLM内部按OPENAI_API_KEY优先级选错key
        _llm_instance = HelloAgentsLLM(
            model=env_model or None,
            api_key=env_api_key or None,
            base_url=env_base_url or None,
            provider="custom",
        )

        print(f"✅ LLM服务初始化成功")
        print(f"   提供商: {_llm_instance.provider}")
        print(f"   模型: {_llm_instance.model}")
        print(f"   Base URL: {_llm_instance.base_url}")
        print(f"   API Key: {_mask_key(_llm_instance.api_key)}")
    
    return _llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance
    global _llm_signature
    _llm_instance = None
    _llm_signature = None