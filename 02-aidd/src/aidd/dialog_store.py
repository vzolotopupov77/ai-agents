from __future__ import annotations


class DialogStore:
    """Хранение истории диалогов в памяти процесса, ключ — chat_id."""

    def __init__(self, max_messages: int) -> None:
        if max_messages < 1:
            msg = "max_messages must be at least 1"
            raise ValueError(msg)
        self._max_messages = max_messages
        self._chats: dict[int, list[dict[str, str]]] = {}

    def get(self, chat_id: int) -> list[dict[str, str]]:
        """Текущая история (без новой реплики пользователя)."""
        return list(self._chats.get(chat_id, []))

    def add_turn(self, chat_id: int, user_text: str, assistant_text: str) -> None:
        """Добавить пару user/assistant и обрезать до max_messages сообщений в сумме."""
        history = self._chats.setdefault(chat_id, [])
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})
        if len(history) > self._max_messages:
            del history[:-self._max_messages]
