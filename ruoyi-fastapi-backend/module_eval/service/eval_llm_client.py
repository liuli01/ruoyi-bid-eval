"""LLM 调用适配器 — 对接 RuoYi ``utils/ai_util.py`` 的 AiUtil 工厂

提供两条调用路径：
1. **优先路径** — 通过 ``AiUtil.get_model_from_factory()`` 获取 agno Model 实例，
   再调用 ``Model.ainvoke()``／``Model.invoke()`` 发送消息。
   如果传入了 ``model_id`` 和 ``query_db``，从 ``ai_models`` 表加载模型配置。
2. **降级路径** — 当 agno 不可用或调用异常时，退化为 httpx 直调 OpenAI 兼容 API。

用法::

    # 异步调用
    text = await EvalLlmClient.call_llm(messages)
    data = await EvalLlmClient.call_llm_with_json(messages, model_id=1, query_db=session)

    # 同步调用
    text = EvalLlmClient.call_llm_sync(messages)

    # 调整并发
    EvalLlmClient.set_max_concurrency(10)
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
import threading
import time as _time
from typing import Any

from utils.log_util import logger


class EvalLlmClient:
    """LLM 调用适配器

    特性：
    * 双路径：agno (优先) / httpx (降级)
    * 双模式：异步 (ainvoke) / 同步 (invoke)
    * 并发控制：asyncio.Semaphore / threading.Semaphore
    * 重试机制：指数退避 + 随机抖动
    * JSON 智能提取：完整解析 → 正则提取 → 异常
    """

    # 并发控制
    _async_semaphore: asyncio.Semaphore | None = None
    _sync_semaphore: threading.Semaphore | None = None

    # 重试
    _max_retries: int = 3
    _base_delay: float = 2.0

    # 默认推理参数
    _default_temperature: float = 0.1
    _default_max_tokens: int = 8192

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    @classmethod
    def set_max_concurrency(cls, n: int) -> None:
        """设置最大并发数（同步/异步信号量同时更新）"""
        cls._async_semaphore = asyncio.Semaphore(n)
        cls._sync_semaphore = threading.Semaphore(n)

    # ---- 异步 ----

    @classmethod
    async def call_llm(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None = None,
        query_db=None,
    ) -> str:
        """调用 LLM 获取文本回复（异步）

        :param messages:   对话消息 [{'role': 'system'|'user'|'assistant', 'content': str}, ...]
        :param model_id:   ai_models 表主键（为 ``None`` 时使用环境变量）
        :param query_db:   SQLAlchemy AsyncSession（传该参数时 ``model_id`` 才生效）
        :return:           LLM 回复文本
        """
        async with cls._get_async_semaphore():
            return await cls._call_with_retry_async(messages, model_id, query_db)

    @classmethod
    async def call_llm_with_json(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None = None,
        query_db=None,
    ) -> dict[str, Any]:
        """调用 LLM 并返回解析后的 JSON 字典（异步）"""
        messages = cls._inject_json_instruction(messages)
        text = await cls.call_llm(messages, model_id, query_db)
        return cls._extract_json(text)

    # ---- 同步 ----

    @classmethod
    def call_llm_sync(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None = None,
        query_db=None,
    ) -> str:
        """调用 LLM 获取文本回复（同步）"""
        with cls._get_sync_semaphore():
            return cls._call_with_retry_sync(messages, model_id, query_db)

    @classmethod
    def call_llm_with_json_sync(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None = None,
        query_db=None,
    ) -> dict[str, Any]:
        """调用 LLM 并返回解析后的 JSON 字典（同步）"""
        messages = cls._inject_json_instruction(messages)
        text = cls.call_llm_sync(messages, model_id, query_db)
        return cls._extract_json(text)

    # ------------------------------------------------------------------
    #  信号量
    # ------------------------------------------------------------------

    @classmethod
    def _get_async_semaphore(cls) -> asyncio.Semaphore:
        if cls._async_semaphore is None:
            max_conc = int(os.environ.get("LLM_MAX_CONCURRENCY", "5"))
            cls._async_semaphore = asyncio.Semaphore(max_conc)
        return cls._async_semaphore

    @classmethod
    def _get_sync_semaphore(cls) -> threading.Semaphore:
        if cls._sync_semaphore is None:
            max_conc = int(os.environ.get("LLM_MAX_CONCURRENCY", "5"))
            cls._sync_semaphore = threading.Semaphore(max_conc)
        return cls._sync_semaphore

    # ------------------------------------------------------------------
    #  重试
    # ------------------------------------------------------------------

    @classmethod
    async def _call_with_retry_async(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None,
        query_db,
    ) -> str:
        """异步重试包装"""
        last_exception: Exception | None = None
        for attempt in range(cls._max_retries):
            try:
                return await cls._call_single_async(messages, model_id, query_db)
            except Exception as exc:
                last_exception = exc
                if attempt < cls._max_retries - 1:
                    delay = cls._base_delay * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "LLM 调用失败 (尝试 %d/%d): %s, %.1fs 后重试",
                        attempt + 1,
                        cls._max_retries,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
        raise RuntimeError(
            f"LLM 调用全部重试失败 ({cls._max_retries} 次): {last_exception}"
        )

    @classmethod
    def _call_with_retry_sync(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None,
        query_db,
    ) -> str:
        """同步重试包装"""
        last_exception: Exception | None = None
        for attempt in range(cls._max_retries):
            try:
                return cls._call_single_sync(messages, model_id, query_db)
            except Exception as exc:
                last_exception = exc
                if attempt < cls._max_retries - 1:
                    delay = cls._base_delay * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "LLM 调用失败 (尝试 %d/%d): %s, %.1fs 后重试",
                        attempt + 1,
                        cls._max_retries,
                        exc,
                        delay,
                    )
                    _time.sleep(delay)
        raise RuntimeError(
            f"LLM 调用全部重试失败 ({cls._max_retries} 次): {last_exception}"
        )

    # ------------------------------------------------------------------
    #  单次调用（路径选择）
    # ------------------------------------------------------------------

    @classmethod
    async def _call_single_async(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None,
        query_db,
    ) -> str:
        """单次异步调用（优先 agno → 回退 httpx）"""
        try:
            return await cls._invoke_agno_async(messages, model_id, query_db)
        except ImportError:
            logger.info("agno 不可用，回退到 httpx 直调")
        except Exception as exc:
            logger.warning("agno 调用失败，回退到 httpx 直调: %s", exc)

        return await cls._invoke_httpx_async(messages, model_id, query_db)

    @classmethod
    def _call_single_sync(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None,
        query_db,
    ) -> str:
        """单次同步调用（优先 agno → 回退 httpx）"""
        try:
            return cls._invoke_agno_sync(messages, model_id, query_db)
        except ImportError:
            logger.info("agno 不可用，回退到 httpx 直调")
        except Exception as exc:
            logger.warning("agno 调用失败，回退到 httpx 直调: %s", exc)

        return cls._invoke_httpx_sync(messages, model_id, query_db)

    # ------------------------------------------------------------------
    #  路径一：agno Model
    # ------------------------------------------------------------------

    @classmethod
    async def _invoke_agno_async(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None,
        query_db,
    ) -> str:
        """通过 ``Model.ainvoke()`` 异步调用"""
        from agno.models.message import Message

        model = await cls._build_agno_model(model_id, query_db)
        agno_messages = [Message(role=m.get("role", "user"), content=m.get("content", "")) for m in messages]

        assistant_message = Message(role="assistant")
        response = await model.ainvoke(messages=agno_messages, assistant_message=assistant_message)

        content = getattr(response, "content", None)
        if not content:
            content = getattr(assistant_message, "content", None)
        return (content or "").strip()

    @classmethod
    def _invoke_agno_sync(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None,
        query_db,
    ) -> str:
        """通过 ``Model.invoke()`` 同步调用"""
        from agno.models.message import Message

        model = cls._build_agno_model_sync(model_id, query_db)
        agno_messages = [Message(role=m.get("role", "user"), content=m.get("content", "")) for m in messages]

        assistant_message = Message(role="assistant")
        response = model.invoke(messages=agno_messages, assistant_message=assistant_message)

        content = getattr(response, "content", None)
        if not content:
            content = getattr(assistant_message, "content", None)
        return (content or "").strip()

    @classmethod
    async def _build_agno_model(cls, model_id: int | None, query_db):
        """异步构建 agno Model 实例

        优先从数据库加载配置，否则使用环境变量。
        """
        # -- 从数据库加载 --
        if model_id is not None and query_db is not None:
            try:
                return await cls._load_model_from_db(model_id, query_db)
            except Exception as exc:
                logger.warning("从数据库加载模型配置失败，使用环境变量: %s", exc)

        # -- 环境变量降级 --
        return cls._build_model_from_env()

    @classmethod
    def _build_agno_model_sync(cls, model_id: int | None, query_db):
        """同步构建 agno Model 实例

        同步环境下无法使用 await，因此数据库方式仅在可同步执行时采用。
        由于 SQLAlchemy AsyncSession 通常不在同步上下文中使用，
        同步构建只使用环境变量降级。
        """
        if model_id is not None and query_db is not None:
            try:
                # 尝试在线程中运行异步加载
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(cls._load_model_from_db(model_id, query_db))
                finally:
                    loop.close()
            except Exception as exc:
                logger.warning("同步构建 agno model 失败，使用环境变量: %s", exc)

        return cls._build_model_from_env()

    @classmethod
    async def _load_model_from_db(cls, model_id: int, query_db):
        """从 ai_models 表加载并构建 agno Model（通用异步加载）"""
        from module_ai.dao.ai_model_dao import AiModelDao
        from module_ai.entity.vo.ai_model_vo import AiModelModel
        from utils.ai_util import AiUtil
        from utils.common_util import CamelCaseUtil
        from utils.crypto_util import CryptoUtil

        ai_model = await AiModelDao.get_ai_model_detail_by_id(query_db, model_id)
        if ai_model is None:
            raise ValueError(f"ai_models 表中不存在 model_id={model_id}")

        model_config = AiModelModel(**CamelCaseUtil.transform_result(ai_model))
        real_api_key = CryptoUtil.decrypt(model_config.api_key) if model_config.api_key else ""

        logger.info(
            "使用数据库模型配置: provider=%s, model_code=%s",
            model_config.provider,
            model_config.model_code,
        )

        return AiUtil.get_model_from_factory(
            provider=model_config.provider,
            model_code=model_config.model_code,
            model_name=model_config.model_name,
            api_key=real_api_key,
            base_url=model_config.base_url,
            temperature=model_config.temperature or cls._default_temperature,
            max_tokens=model_config.max_tokens or cls._default_max_tokens,
        )

    @classmethod
    def _build_model_from_env(cls):
        """从环境变量构建 agno Model（降级路径）

        环境变量:
            DS_PROVIDER  — 提供商名称，默认 ``DeepSeek``
            DS_MODEL     — 模型编码，默认 ``deepseek-chat``
            DS_API_KEY   — API 密钥
            DS_API_BASE  — 接口地址，默认 ``https://api.deepseek.com``
        """
        from utils.ai_util import AiUtil

        provider = os.environ.get("DS_PROVIDER", "DeepSeek")
        model_code = os.environ.get("DS_MODEL", "deepseek-chat")
        api_key = os.environ.get("DS_API_KEY", "")
        api_base = os.environ.get("DS_API_BASE", "https://api.deepseek.com")

        if not api_key:
            raise ValueError(
                "DS_API_KEY 未设置。请在环境变量或在 ai_models 表中配置模型。"
            )

        logger.info("使用环境变量模型配置: provider=%s, model_code=%s", provider, model_code)

        return AiUtil.get_model_from_factory(
            provider=provider,
            model_code=model_code,
            api_key=api_key,
            base_url=api_base,
            temperature=cls._default_temperature,
            max_tokens=cls._default_max_tokens,
        )

    # ------------------------------------------------------------------
    #  路径二：httpx 直调（降级）
    # ------------------------------------------------------------------

    @classmethod
    async def _invoke_httpx_async(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None,
        query_db,
    ) -> str:
        """通过 httpx.AsyncClient 直调 OpenAI 兼容 API（异步）"""
        import httpx

        api_key, api_base, model = await cls._resolve_httpx_config_async(model_id, query_db)

        url = f'{api_base.rstrip("/")}/chat/completions'
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": cls._default_temperature,
            "max_tokens": cls._default_max_tokens,
        }

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        result = data["choices"][0]["message"]["content"] or ""
        logger.info(
            "httpx 直调成功: model=%s, tokens=%s",
            model,
            data.get("usage", {}).get("total_tokens", "N/A"),
        )
        return result.strip()

    @classmethod
    def _invoke_httpx_sync(
        cls,
        messages: list[dict[str, Any]],
        model_id: int | None,
        query_db,
    ) -> str:
        """通过 httpx.Client 同步直调 OpenAI 兼容 API

        注意：同步降级路径只使用环境变量配置，不支持加载数据库模型。
        """
        import httpx

        api_key = os.environ.get("DS_API_KEY", "")
        api_base = os.environ.get("DS_API_BASE", "https://api.deepseek.com")
        model = os.environ.get("DS_MODEL", "deepseek-chat")

        url = f'{api_base.rstrip("/")}/chat/completions'
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": cls._default_temperature,
            "max_tokens": cls._default_max_tokens,
        }

        with httpx.Client(timeout=300) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        result = data["choices"][0]["message"]["content"] or ""
        logger.info(
            "httpx 直调成功: model=%s, tokens=%s",
            model,
            data.get("usage", {}).get("total_tokens", "N/A"),
        )
        return result.strip()

    @classmethod
    async def _resolve_httpx_config_async(
        cls,
        model_id: int | None,
        query_db,
    ) -> tuple[str, str, str]:
        """异步解析 httpx 直调需要的配置三元组 ``(api_key, api_base, model)``

        优先从数据库加载，失败后回退到环境变量。
        """
        if model_id is not None and query_db is not None:
            try:
                return await cls._load_httpx_config_from_db(model_id, query_db)
            except Exception as exc:
                logger.warning("[httpx] 从数据库加载配置失败，使用环境变量: %s", exc)

        return (
            os.environ.get("DS_API_KEY", ""),
            os.environ.get("DS_API_BASE", "https://api.deepseek.com"),
            os.environ.get("DS_MODEL", "deepseek-chat"),
        )

    @classmethod
    async def _load_httpx_config_from_db(
        cls,
        model_id: int,
        query_db,
    ) -> tuple[str, str, str]:
        """从 ai_models 表加载 httpx 直调需要的配置"""
        from module_ai.dao.ai_model_dao import AiModelDao
        from module_ai.entity.vo.ai_model_vo import AiModelModel
        from utils.common_util import CamelCaseUtil
        from utils.crypto_util import CryptoUtil

        ai_model = await AiModelDao.get_ai_model_detail_by_id(query_db, model_id)
        if ai_model is None:
            raise ValueError(f"ai_models 表中不存在 model_id={model_id}")

        model_config = AiModelModel(**CamelCaseUtil.transform_result(ai_model))
        api_key = CryptoUtil.decrypt(model_config.api_key) if model_config.api_key else os.environ.get("DS_API_KEY", "")
        api_base = model_config.base_url or os.environ.get("DS_API_BASE", "https://api.deepseek.com")
        model_code = model_config.model_code or os.environ.get("DS_MODEL", "deepseek-chat")

        logger.info("[httpx] 使用数据库模型配置: provider=%s, model_code=%s", model_config.provider, model_code)
        return api_key, api_base, model_code

    # ------------------------------------------------------------------
    #  JSON 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_json_instruction(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """在最后一条 user 消息后追加 JSON 格式要求（原地修改并返回）"""
        if messages and messages[-1].get("role") == "user":
            last_msg = messages[-1]["content"]
            if isinstance(last_msg, str) and "json" not in last_msg.lower():
                messages[-1]["content"] = last_msg + (
                    "\n\n请直接输出 JSON 格式，不要包含其他说明文字。"
                )
        return messages

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        """从 LLM 回复文本中提取并解析 JSON

        解析策略（依次尝试）：
        1. 完整字符串解析
        2. 去除代码围栏标记后解析
        3. 正则提取 ``{...}`` 对象
        4. 正则提取 ``[...]`` 数组
        """
        text = text.strip()

        # 1) 完整解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2) 去除 ```json ... ``` 围栏
        cleaned = text
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        if cleaned != text:
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        # 3) 正则提取 JSON 对象
        obj_match = re.search(r"\{.*\}", text, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except json.JSONDecodeError:
                pass

        # 4) 正则提取 JSON 数组
        arr_match = re.search(r"\[.*\]", text, re.DOTALL)
        if arr_match:
            try:
                result = json.loads(arr_match.group(0))
                return {"results": result}
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从 LLM 响应中解析 JSON: {text[:500]}")


__all__ = ["EvalLlmClient"]
