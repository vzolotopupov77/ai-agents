"""Middleware для агента: PII masking и лимиты вызовов (LangChain ``AgentMiddleware``).

- ``PIIMiddleware``: см. словарь ``PATTERNS``
- Лимиты: ``ModelCallLimitMiddleware``, ``ToolCallLimitMiddleware`` — см. параметры ниже

Расширение PII: добавить запись в ``PATTERNS`` и передать имя в ``PIIMiddleware(...)``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse, ToolCallRequest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

Replacer = str | Callable[[re.Match[str]], str]

logger = logging.getLogger(__name__)

_LIMIT_MSG_MODEL = (
    "Запрос ограничен: превышено максимальное число обращений к модели. "
    "Пожалуйста, упростите запрос или начните новый диалог."
)
_LIMIT_MSG_TOOL = (
    "Запрос ограничен: превышено максимальное число вызовов инструментов. Операция прервана."
)
# Карта имён правил → (regex, замена для strategy="mask")
PATTERNS: dict[str, tuple[re.Pattern[str], Replacer]] = {
    "credit_card": (
        re.compile(r"\b(\d{4})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b"),
        lambda m: f"****-****-****-{m.group(4)}",
    ),
}


def _messages_since_last_human(messages: list) -> list:
    """Возвращает срез messages после последнего HumanMessage (текущий ход агента)."""
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return messages[i + 1 :]
    return messages


def _mask_text(text: str, pattern: re.Pattern[str], replacer: Replacer) -> str:
    return pattern.sub(replacer, text)


def _mask_aimessages_inplace_copy(
    messages: list[BaseMessage],
    pattern: re.Pattern[str],
    replacer: Replacer,
) -> list[BaseMessage]:
    """Возвращает новый список с замаскированным ``content`` у ``AIMessage`` (только str)."""
    out: list[BaseMessage] = []
    changed = False
    for msg in messages:
        if isinstance(msg, AIMessage):
            c = msg.content
            if isinstance(c, str) and c:
                new_c = _mask_text(c, pattern, replacer)
                if new_c != c:
                    out.append(msg.model_copy(update={"content": new_c}))
                    changed = True
                    continue
        out.append(msg)
    return messages if not changed else out


class PIIMiddleware(AgentMiddleware):
    """Маскирует PII в ответах модели (после вызова LLM), не трогая tool messages."""

    def __init__(
        self,
        pattern_name: str,
        *,
        strategy: str = "mask",
        apply_to_input: bool = False,
        apply_to_output: bool = True,
    ) -> None:
        super().__init__()
        if strategy != "mask":
            msg = f"Only strategy='mask' is supported, got {strategy!r}"
            raise ValueError(msg)
        if pattern_name not in PATTERNS:
            msg = f"Unknown PII pattern: {pattern_name!r}"
            raise KeyError(msg)
        self._pattern, self._replacer = PATTERNS[pattern_name]
        self.apply_to_input = apply_to_input
        self.apply_to_output = apply_to_output
        if apply_to_input:
            # YAGNI: ввод пользователя не маскируем — LLM и инструменты видят исходный текст.
            raise NotImplementedError(
                "apply_to_input=True is not supported; keep False so tools/LLM see real input."
            )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse | AIMessage:
        response = handler(request)
        if not self.apply_to_output:
            return response
        return self._mask_model_result(response)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | AIMessage:
        response = await handler(request)
        if not self.apply_to_output:
            return response
        return self._mask_model_result(response)

    def _mask_model_result(
        self, response: ModelResponse | AIMessage
    ) -> ModelResponse | AIMessage:
        if isinstance(response, AIMessage):
            c = response.content
            if isinstance(c, str) and c:
                new_c = _mask_text(c, self._pattern, self._replacer)
                if new_c != c:
                    return response.model_copy(update={"content": new_c})
            return response

        new_result = _mask_aimessages_inplace_copy(
            response.result, self._pattern, self._replacer
        )
        if new_result is response.result:
            return response
        return ModelResponse(
            result=new_result,
            structured_response=response.structured_response,
        )


def _ensure_exit_behavior_is_end(exit_behavior: str) -> None:
    if exit_behavior != "end":
        msg = (
            "Only exit_behavior='end' is implemented (Graceful AIMessage / ToolMessage), "
            f"got {exit_behavior!r}"
        )
        raise ValueError(msg)


class ModelCallLimitMiddleware(AgentMiddleware):
    """Ограничивает число вызовов LLM за один run агента (одно сообщение / resume).

    Считает ``AIMessage`` в текущем ходе (после последнего ``HumanMessage``).
    N-й вызов = len(прошлые AI в ходе) + 1. Не зависит от asyncio-контекста,
    поскольку LangGraph запускает каждый нод через ``copy_context()`` (изолированно).
    """

    def __init__(self, run_limit: int, *, exit_behavior: str = "end") -> None:
        super().__init__()
        if run_limit < 1:
            msg = f"run_limit must be >= 1, got {run_limit}"
            raise ValueError(msg)
        _ensure_exit_behavior_is_end(exit_behavior)
        self.run_limit = run_limit
        self.exit_behavior = exit_behavior

    def _call_number(self, request: ModelRequest) -> int:
        """Порядковый номер текущего вызова в рамках текущего хода (1-based)."""
        current_turn = _messages_since_last_human(request.state["messages"])
        past_ai = sum(1 for m in current_turn if isinstance(m, AIMessage))
        return past_ai + 1

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse | AIMessage:
        n = self._call_number(request)
        if n > self.run_limit:
            logger.warning("Model call limit exceeded: call=%s run_limit=%s", n, self.run_limit)
            return AIMessage(content=_LIMIT_MSG_MODEL)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | AIMessage:
        n = self._call_number(request)
        if n > self.run_limit:
            logger.warning("Model call limit exceeded: call=%s run_limit=%s", n, self.run_limit)
            return AIMessage(content=_LIMIT_MSG_MODEL)
        return await handler(request)


class ToolCallLimitMiddleware(AgentMiddleware):
    """Ограничивает суммарное число вызовов инструментов за один run агента.

    Источник истины — текущий ход (сообщения после последнего ``HumanMessage``):
    считаем прошлые ``ToolMessage`` + per-batch счётчик текущей группы вызовов.

    Все параллельные tool calls одного шага получают один и тот же объект
    ``request.state`` (LangGraph передаёт ссылку), поэтому ``id(request.state)``
    служит стабильным ключом батча. Инкремент атомарен — asyncio однопоточен.
    """

    def __init__(self, run_limit: int, *, exit_behavior: str = "end") -> None:
        super().__init__()
        if run_limit < 1:
            msg = f"run_limit must be >= 1, got {run_limit}"
            raise ValueError(msg)
        _ensure_exit_behavior_is_end(exit_behavior)
        self.run_limit = run_limit
        self.exit_behavior = exit_behavior
        # batch_id (id state-объекта) → кол-во вызовов текущего батча
        self._batch_counters: dict[int, int] = {}

    def _total_and_increment(self, request: ToolCallRequest) -> int:
        """Инкрементирует счётчик батча и возвращает суммарный номер вызова (1-based)."""
        current_turn = _messages_since_last_human(request.state["messages"])
        past = sum(1 for m in current_turn if isinstance(m, ToolMessage))
        batch_id = id(request.state)
        self._batch_counters[batch_id] = self._batch_counters.get(batch_id, 0) + 1
        return past + self._batch_counters[batch_id]

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable):
        total = self._total_and_increment(request)
        if total > self.run_limit:
            logger.warning("Tool call limit exceeded: total=%s run_limit=%s", total, self.run_limit)
            return ToolMessage(
                content=_LIMIT_MSG_TOOL,
                tool_call_id=request.tool_call["id"],
            )
        return handler(request)

    async def awrap_tool_call(self, request: ToolCallRequest, handler):
        total = self._total_and_increment(request)
        if total > self.run_limit:
            logger.warning("Tool call limit exceeded: total=%s run_limit=%s", total, self.run_limit)
            return ToolMessage(
                content=_LIMIT_MSG_TOOL,
                tool_call_id=request.tool_call["id"],
            )
        return await handler(request)
