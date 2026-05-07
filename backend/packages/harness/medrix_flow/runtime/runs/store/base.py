from __future__ import annotations

import abc
from typing import Any


class RunStore(abc.ABC):
    @abc.abstractmethod
    async def setup(self) -> None:
        """Create tables / indexes if needed."""

    @abc.abstractmethod
    async def put(
        self,
        run_id: str,
        *,
        thread_id: str,
        assistant_id: str | None,
        status: str,
        multitask_strategy: str,
        source: str,
        metadata: dict[str, Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        pre_message_count: int = 0,
        persisted_message_count: int = 0,
        messages_complete: bool = False,
        error: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> None:
        pass

    @abc.abstractmethod
    async def get(self, run_id: str) -> dict[str, Any] | None:
        pass

    @abc.abstractmethod
    async def list_by_thread(self, thread_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def update_status(self, run_id: str, status: str, *, error: str | None = None, updated_at: str | None = None) -> None:
        pass

    @abc.abstractmethod
    async def update_materialization(
        self,
        run_id: str,
        *,
        persisted_message_count: int,
        messages_complete: bool,
        updated_at: str | None = None,
    ) -> None:
        pass
