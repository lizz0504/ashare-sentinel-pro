# -*- coding: utf-8 -*-
"""
LLM Factory - 多模型AI调用工厂

支持: Qwen / DeepSeek / Zhipu
自动降级处理
"""

import logging
from typing import Optional
from httpx import AsyncClient, TimeoutException as HttpTimeout

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMFactory:
    """多模型AI调用工厂"""

    # API端点
    APIS = {
        "qwen": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    }

    # 模型名称
    MODELS = {
        "qwen": "qwen-max",
        "deepseek": "deepseek-chat",
        "zhipu": "glm-4"
    }

    # 中文显示名
    NAMES = {
        "qwen": "通义千问",
        "deepseek": "DeepSeek",
        "zhipu": "智谱GLM"
    }

    @classmethod
    async def fast_reply(
        cls,
        model: str,
        system: str,
        user: str,
        timeout: int = 30
    ) -> str:
        """快速调用模型"""
        caller = {
            "qwen": cls._call_qwen,
            "deepseek": cls._call_deepseek,
            "zhipu": cls._call_zhipu
        }.get(model)

        if caller:
            return await caller(system, user, timeout)
        return f"[错误] 未知模型: {model}"

    @classmethod
    async def _call_api(
        cls,
        url: str,
        headers: dict,
        payload: dict,
        timeout: int
    ) -> Optional[dict]:
        """通用API调用"""
        try:
            async with AsyncClient(timeout=timeout) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                return r.json()
        except HttpTimeout:
            logger.error(f"API timeout: {url}")
        except Exception as e:
            logger.error(f"API error: {e}")
        return None

    @classmethod
    async def _call_qwen(cls, system: str, user: str, timeout: int) -> str:
        """调用通义千问"""
        api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
        if not api_key:
            return "[错误] 未配置 DASHSCOPE_API_KEY"

        data = await cls._call_api(
            cls.APIS["qwen"],
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            {
                "model": cls.MODELS["qwen"],
                "input": {"messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ]},
                "parameters": {"max_tokens": 1000, "temperature": 0.8}
            },
            timeout
        )

        if data and "output" in data:
            return data["output"].get("text", "[错误] 响应格式异常")
        return "[错误] Qwen调用失败"

    @classmethod
    async def _call_deepseek(cls, system: str, user: str, timeout: int) -> str:
        """调用DeepSeek"""
        api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        if not api_key:
            logger.warning("DeepSeek未配置，降级到Qwen")
            return await cls._call_qwen(system, user, timeout)

        data = await cls._call_api(
            cls.APIS["deepseek"],
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            {
                "model": cls.MODELS["deepseek"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout
        )

        if data and "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        return "[错误] DeepSeek调用失败"

    @classmethod
    async def _call_zhipu(cls, system: str, user: str, timeout: int) -> str:
        """调用智谱GLM"""
        api_key = getattr(settings, 'ZHIPU_API_KEY', None)
        if not api_key:
            logger.warning("智谱未配置，降级到Qwen")
            return await cls._call_qwen(system, user, timeout)

        data = await cls._call_api(
            cls.APIS["zhipu"],
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            {
                "model": cls.MODELS["zhipu"],
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                "max_tokens": 1000,
                "temperature": 0.6
            },
            timeout
        )

        if data and "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        return "[错误] 智谱调用失败"

    @classmethod
    def get_name(cls, model: str) -> str:
        """获取模型显示名"""
        return cls.NAMES.get(model, model)

    @classmethod
    def get_available(cls) -> list:
        """获取可用模型列表"""
        models = []
        if getattr(settings, 'DASHSCOPE_API_KEY', None):
            models.append("qwen")
        if getattr(settings, 'DEEPSEEK_API_KEY', None):
            models.append("deepseek")
        if getattr(settings, 'ZHIPU_API_KEY', None):
            models.append("zhipu")
        return models or ["qwen"]
