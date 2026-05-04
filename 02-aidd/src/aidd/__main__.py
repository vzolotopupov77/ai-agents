"""Точка входа для ``python -m aidd``."""

from __future__ import annotations

import asyncio

from aidd.main import main


if __name__ == "__main__":
    asyncio.run(main())
