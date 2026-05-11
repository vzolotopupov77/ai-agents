from __future__ import annotations

from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator


class TransactionExtract(BaseModel):
    """Structured output: извлечение транзакции из пользовательского сообщения.

    Поле `reply` — текст для пользователя; если модель вернула null (часто у Ollama),
    трактуем как пустую строку и подставляем подтверждение из учёта при found=true.
    """

    found: bool
    reply: str = ""

    @field_validator("reply", mode="before")
    @classmethod
    def _reply_null_to_empty(cls, v: object) -> str:
        if v is None:
            return ""
        return v if isinstance(v, str) else str(v)

    # Обязательны при found=True; None допустим только при found=False
    flow: Optional[Literal["income", "expense"]] = None
    amount: Optional[float] = None
    tx_type: Optional[Literal["everyday", "periodic", "one-time"]] = None
    category: Optional[str] = None
    description: Optional[str] = None
    # ISO 8601 или null; при null используется текущее время. Некоторые модели шлют ключ "time".
    timestamp: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("timestamp", "time"),
    )
