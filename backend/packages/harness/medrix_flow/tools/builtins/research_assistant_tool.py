from __future__ import annotations

from typing import Annotated, Any, cast

from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.typing import ContextT

from medrix_flow.agents.thread_state import ThreadState
from medrix_flow.config.paths import get_paths
from medrix_flow.research import RESEARCH_STAGES, ResearchQuestService, ResearchRepository, ResearchStage
from medrix_flow.runtime.db import SQLiteRuntimeDB


def _as_stage(value: str | None) -> ResearchStage | None:
    if value is None:
        return None
    if value not in RESEARCH_STAGES:
        raise ValueError(f"Unknown research stage {value!r}. Expected one of: {', '.join(RESEARCH_STAGES)}")
    return cast(ResearchStage, value)


@tool("research_assistant", parse_docstring=True)
async def research_assistant_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    action: str = "start",
    topic: str | None = None,
    quest_id: str | None = None,
    target_stage: str | None = None,
    inputs: dict[str, Any] | None = None,
    artifacts: list[str] | None = None,
    scope: str | None = None,
    objective: str | None = None,
    gate_stage: str | None = None,
    gate_type: str | None = None,
    gate_status: str = "approved",
    gate_reason: str | None = None,
) -> Command:
    """Start, inspect, or advance a staged research quest.

    Use this tool when the user wants an automatic research assistant,
    research lifecycle tracking, novelty checks, claim-level evidence mapping,
    experiment gates, reviewer loops, or a manuscript workspace. This tool
    coordinates the research quest ledger; use `academic_research` for heavy
    literature retrieval and `experiment_lab` for actual dataset execution.

    Args:
        action: One of `start`, `status`, `advance`, or `gate`.
        topic: Research topic. Required when starting a quest.
        quest_id: Existing research quest id. If omitted for status/advance,
            the latest quest for the current thread is used.
        target_stage: Optional immediate next lifecycle stage for `advance`.
        inputs: Structured stage inputs such as claims, idea, branches, metrics,
            academic_project_id, experiment_project_id, or completed_actions.
        artifacts: Artifact paths to attach to the ledger entry.
        scope: Optional research scope for a new quest.
        objective: Optional concrete research objective for a new quest.
        gate_stage: Stage guarded by a human gate when action is `gate`.
        gate_type: Gate type such as `experiment_execution`, `pre_review`, or `final_release`.
        gate_status: Gate status for action `gate`; defaults to `approved`.
        gate_reason: Optional human reason or note for the gate decision.
    """
    thread_id = runtime.context.get("thread_id")
    if not thread_id:
        return Command(update={"messages": [ToolMessage("Error: thread_id is required for research_assistant.", tool_call_id=tool_call_id)]})

    db = SQLiteRuntimeDB(get_paths().research_db_file)
    await db.connect()
    try:
        repository = ResearchRepository(db)
        await repository.setup()
        service = ResearchQuestService(repository)

        resolved_quest_id = quest_id
        if not resolved_quest_id and action in {"status", "advance", "gate"}:
            quests = await service.list_quests(str(thread_id))
            resolved_quest_id = quests[0].quest_id if quests else None

        if action == "start":
            if not topic:
                raise ValueError("topic is required when starting a research quest")
            quest = await service.create_quest(
                thread_id=str(thread_id),
                topic=topic,
                scope=scope,
                objective=objective,
                metadata={"created_by": "research_assistant"},
            )
            message = f"Research quest `{quest.quest_id}` started at stage `{quest.stage}` for topic: {quest.topic}"
        elif action == "status":
            if not resolved_quest_id:
                raise ValueError("quest_id is required and no quest exists for this thread")
            snapshot = await service.get_snapshot(resolved_quest_id)
            message = (
                f"Research quest `{snapshot.quest.quest_id}` is `{snapshot.quest.status}` at stage `{snapshot.quest.stage}`. "
                f"Evidence claims: {len(snapshot.evidence)}, branches: {len(snapshot.experiment_branches)}, "
                f"review reports: {len(snapshot.reviewer_reports)}, gates: {len(snapshot.gates)}."
            )
        elif action == "advance":
            if not resolved_quest_id:
                if not topic:
                    raise ValueError("quest_id is required for advance when no topic is supplied")
                quest = await service.create_quest(thread_id=str(thread_id), topic=topic, scope=scope, objective=objective)
                resolved_quest_id = quest.quest_id
            result = await service.advance_quest(
                resolved_quest_id,
                target_stage=_as_stage(target_stage),
                inputs=inputs or {},
                artifacts=artifacts or [],
                tool_name="research_assistant",
            )
            if result.blocked and result.required_gate:
                message = (
                    f"Research quest `{result.quest.quest_id}` is blocked before `{result.required_gate.stage}`. "
                    f"Required gate: `{result.required_gate.gate_type}`."
                )
            else:
                message = f"Research quest `{result.quest.quest_id}` advanced to `{result.quest.stage}`."
        elif action == "gate":
            if not resolved_quest_id:
                raise ValueError("quest_id is required and no quest exists for this thread")
            if not gate_stage or not gate_type:
                raise ValueError("gate_stage and gate_type are required for gate decisions")
            gate = await service.decide_gate(
                resolved_quest_id,
                stage=_as_stage(gate_stage) or "intake",
                gate_type=gate_type,
                status=gate_status,
                reason=gate_reason,
            )
            message = f"Research gate `{gate.gate_type}` for `{gate.stage}` is now `{gate.status}`."
        else:
            raise ValueError("action must be one of: start, status, advance, gate")
    except Exception as exc:
        await db.close()
        return Command(update={"messages": [ToolMessage(f"Error: {exc}", tool_call_id=tool_call_id)]})

    await db.close()
    return Command(update={"messages": [ToolMessage(message, tool_call_id=tool_call_id)]})
