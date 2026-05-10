from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Transaction:
    """Запись учёта дохода или расхода (хранится в памяти процесса)."""

    timestamp: datetime
    flow: Literal["income", "expense"]
    amount: Decimal
    tx_type: Literal["everyday", "periodic", "one-time"]
    category: str
    description: str
