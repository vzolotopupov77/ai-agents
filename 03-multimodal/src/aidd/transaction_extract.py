from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class TransactionExtract(BaseModel):
    """Structured output: извлечение транзакции из пользовательского сообщения.

    Поле `reply` обязательно всегда:
    - found=True  → краткое подтверждение записи (дата, сумма, категория).
    - found=False → ответ финансового советника без записи в учёт.
    """

    found: bool
    reply: str

    # Обязательны при found=True; None допустим только при found=False
    flow: Optional[Literal["income", "expense"]] = None
    amount: Optional[float] = None
    tx_type: Optional[Literal["everyday", "periodic", "one-time"]] = None
    category: Optional[str] = None
    description: Optional[str] = None
    # ISO 8601 или null; при null используется текущее время
    timestamp: Optional[str] = None
