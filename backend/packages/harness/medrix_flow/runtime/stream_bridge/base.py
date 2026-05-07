from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from typing import Any


class StreamBridge(abc.ABC):
    @abc.abstractmethod
    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    async def close(self, run_id: str) -> None:
        pass

    @abc.abstractmethod
    async def subscribe(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        pass
