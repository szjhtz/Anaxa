from __future__ import annotations

from typing import Any

from .service import ResearchQuestService
from .types import ResearchAdvanceResult, ResearchQuest, ResearchStage


class ResearchQuestOrchestrator:
    """Thin orchestration facade for end-to-end research lifecycle actions.

    The service owns persistence and deterministic stage handlers. This facade
    gives agent tools and future schedulers a stable place to coordinate longer
    workflows without coupling them directly to router request models.
    """

    def __init__(self, service: ResearchQuestService) -> None:
        self._service = service

    async def start(
        self,
        *,
        thread_id: str,
        topic: str,
        title: str | None = None,
        scope: str | None = None,
        objective: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchQuest:
        return await self._service.create_quest(
            thread_id=thread_id,
            topic=topic,
            title=title,
            scope=scope,
            objective=objective,
            metadata=metadata,
        )

    async def advance(
        self,
        quest_id: str,
        *,
        target_stage: ResearchStage | None = None,
        inputs: dict[str, Any] | None = None,
        artifacts: list[str] | None = None,
        tool_name: str | None = None,
        model_name: str | None = None,
    ) -> ResearchAdvanceResult:
        return await self._service.advance_quest(
            quest_id,
            target_stage=target_stage,
            inputs=inputs,
            artifacts=artifacts,
            tool_name=tool_name,
            model_name=model_name,
        )
