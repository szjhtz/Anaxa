from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from .base import StreamBridge

END_SENTINEL = "__stream_end__"


class MemoryStreamBridge(StreamBridge):
    """In-memory event log for SSE joins.

    Each run keeps an append-only event buffer so late subscribers can replay
    what has already been emitted in the current process.
    """

    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._conditions: dict[str, asyncio.Condition] = defaultdict(asyncio.Condition)

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        condition = self._conditions[run_id]
        async with condition:
            self._events[run_id].append(event)
            condition.notify_all()

    async def close(self, run_id: str) -> None:
        await self.publish(run_id, {"event": END_SENTINEL, "data": {}})

    async def subscribe(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        condition = self._conditions[run_id]
        cursor = 0
        while True:
            async with condition:
                while cursor >= len(self._events[run_id]):
                    await condition.wait()
                event = self._events[run_id][cursor]
                cursor += 1
            yield event
            if event.get("event") == END_SENTINEL:
                break
