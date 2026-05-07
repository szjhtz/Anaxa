from __future__ import annotations

import abc
from typing import Any


class RunEventStore(abc.ABC):
    @abc.abstractmethod
    async def setup(self) -> None:
        pass

    @abc.abstractmethod
    async def put(
        self,
        *,
        thread_id: str,
        run_id: str,
        event_type: str,
        content: dict[str, Any],
        caller: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        pass

    @abc.abstractmethod
    async def put_batch(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def list_messages_by_run(
        self,
        thread_id: str,
        run_id: str,
        *,
        limit: int = 50,
        before_seq: int | None = None,
        after_seq: int | None = None,
    ) -> list[dict[str, Any]]:
        pass
