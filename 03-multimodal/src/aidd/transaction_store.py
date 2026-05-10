from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from aidd.transaction import Transaction


_TX_TYPE_LABEL = {
    "everyday": "повседневные",
    "periodic": "периодические",
    "one-time": "разовые",
}


def _format_money(amount: Decimal) -> str:
    return str(amount.quantize(Decimal("0.01")))


class TransactionStore:
    """Хранение транзакций в памяти процесса, ключ — chat_id."""

    def __init__(self) -> None:
        self._chats: dict[int, list[Transaction]] = {}

    def add(self, chat_id: int, tx: Transaction) -> None:
        self._chats.setdefault(chat_id, []).append(tx)

    def get_all(self, chat_id: int) -> list[Transaction]:
        return list(self._chats.get(chat_id, []))

    def report_text(self, chat_id: int) -> str:
        """Текстовый отчёт без вызова LLM."""
        txs = self._chats.get(chat_id, [])
        if not txs:
            return "Нет записанных операций."

        total_income = Decimal("0")
        total_expense = Decimal("0")
        income_by_category: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        expense_by_category: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        expense_by_tx_type: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for tx in txs:
            amt = tx.amount
            if tx.flow == "income":
                total_income += amt
                income_by_category[tx.category] += amt
            else:
                total_expense += amt
                expense_by_category[tx.category] += amt
                expense_by_tx_type[tx.tx_type] += amt

        balance = total_income - total_expense
        count = len(txs)
        lines: list[str] = [
            f"Операций: {count}",
            f"Доходы: {_format_money(total_income)}",
            f"Расходы: {_format_money(total_expense)}",
            f"Баланс: {_format_money(balance)}",
            "",
            "Расходы по категориям:",
        ]
        for cat in sorted(expense_by_category, key=lambda c: expense_by_category[c], reverse=True):
            lines.append(f"  • {cat}: {_format_money(expense_by_category[cat])}")

        if income_by_category:
            lines.append("")
            lines.append("Доходы по категориям:")
            for cat in sorted(income_by_category, key=lambda c: income_by_category[c], reverse=True):
                lines.append(f"  • {cat}: {_format_money(income_by_category[cat])}")

        if expense_by_tx_type:
            lines.append("")
            lines.append("Расходы по типу:")
            for tkey in sorted(expense_by_tx_type, key=lambda k: expense_by_tx_type[k], reverse=True):
                label = _TX_TYPE_LABEL.get(tkey, tkey)
                lines.append(f"  • {label}: {_format_money(expense_by_tx_type[tkey])}")

        return "\n".join(lines)
