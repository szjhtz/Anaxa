from __future__ import annotations

from typing import Annotated, Any, cast

from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.typing import ContextT

from medrix_flow.agents.thread_state import ThreadState
from medrix_flow.config import get_app_config
from medrix_flow.config.paths import get_paths
from medrix_flow.models import create_chat_model
from medrix_flow.research import (
    RESEARCH_STAGES,
    ResearchQuestOrchestrator,
    ResearchQuestService,
    ResearchQuestSnapshot,
    ResearchRepository,
    ResearchStage,
)
from medrix_flow.research.orchestrator import ContentGenerator
from medrix_flow.runtime.db import SQLiteRuntimeDB


def _as_stage(value: str | None) -> ResearchStage | None:
    if value is None:
        return None
    if value not in RESEARCH_STAGES:
        raise ValueError(f"Unknown research stage {value!r}. Expected one of: {', '.join(RESEARCH_STAGES)}")
    return cast(ResearchStage, value)


def _message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def _manuscript_prompt_for(section_key: str, snapshot: ResearchQuestSnapshot) -> str:
    evidence = [
        {
            "claim": item.claim,
            "support_status": item.support_status,
            "source_title": item.source_title,
            "locator": item.locator,
        }
        for item in snapshot.evidence[:20]
    ]
    branches = [
        {
            "name": branch.name,
            "branch_type": branch.branch_type,
            "status": branch.status,
            "metrics": branch.metrics,
            "failure_summary": branch.failure_summary,
        }
        for branch in snapshot.experiment_branches[:10]
    ]
    return (
        "Draft one concise manuscript section for a research quest.\n"
        "Use LaTeX-friendly prose. Do not invent citations or unsupported claims.\n"
        f"Section key: {section_key}\n"
        f"Title: {snapshot.quest.title}\n"
        f"Topic: {snapshot.quest.topic}\n"
        f"Objective: {snapshot.quest.objective or 'not specified'}\n"
        f"Evidence records: {evidence}\n"
        f"Experiment branches: {branches}\n"
    )


def _build_content_generator(model_name: str | None) -> ContentGenerator:
    async def generate(section_key: str, snapshot: ResearchQuestSnapshot) -> str:
        llm = create_chat_model(model_name, thinking_enabled=False)
        response = await llm.ainvoke(_manuscript_prompt_for(section_key, snapshot))
        return _message_content_to_text(response.content).strip()

    return generate


def _resolve_thread_model_name(runtime: ToolRuntime[ContextT, ThreadState]) -> str | None:
    model_name = runtime.context.get("model_name")
    if isinstance(model_name, str) and model_name:
        return model_name
    runtime_config = getattr(runtime, "config", None)
    configurable = runtime_config.get("configurable") if isinstance(runtime_config, dict) else None
    if isinstance(configurable, dict):
        configured_model = configurable.get("model_name")
        if isinstance(configured_model, str) and configured_model:
            return configured_model
    return None


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
    auto_gates: list[str] | None = None,
    max_stages: int | None = None,
    quality_mode: str | None = None,
    quality_repair_budget: int | None = None,
) -> Command:
    """Start, inspect, or advance a staged research quest.

    Use this tool when the user wants an automatic research assistant,
    research lifecycle tracking, novelty checks, claim-level evidence mapping,
    experiment gates, reviewer loops, or a manuscript workspace. This tool
    coordinates the research quest ledger; use `academic_research` for heavy
    literature retrieval and `experiment_lab` for actual dataset execution.

    Args:
        action: One of `start`, `status`, `advance`, `gate`, or `run_pipeline`.
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
        auto_gates: Optional gate types to auto-approve for `run_pipeline`; defaults to config.
        max_stages: Optional max lifecycle stages to advance for `run_pipeline`; defaults to config.
        quality_mode: Optional quality gate mode for `run_pipeline`: `auto_repair`, `audit_only`, or `strict_gate`.
        quality_repair_budget: Optional max automatic quality-repair approvals for `run_pipeline`.
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
        orchestrator = ResearchQuestOrchestrator(service)

        resolved_quest_id = quest_id
        if not resolved_quest_id and action in {"status", "advance", "gate", "run_pipeline"}:
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
        elif action == "run_pipeline":
            if not resolved_quest_id:
                if not topic:
                    raise ValueError("quest_id is required for run_pipeline when no topic is supplied")
                quest = await service.create_quest(
                    thread_id=str(thread_id),
                    topic=topic,
                    scope=scope,
                    objective=objective,
                    metadata={"created_by": "research_assistant", "pipeline": "run_pipeline"},
                )
                resolved_quest_id = quest.quest_id
            config = get_app_config()
            model_name = config.research.manuscript_model or _resolve_thread_model_name(runtime)
            result = await orchestrator.run_pipeline(
                resolved_quest_id,
                auto_gates=auto_gates if auto_gates is not None else config.research.default_auto_gates,
                max_stages=max_stages if max_stages is not None else config.research.default_max_stages,
                quality_mode=quality_mode or config.research.default_quality_mode,
                repair_budget=quality_repair_budget
                if quality_repair_budget is not None
                else config.research.default_quality_repair_budget,
                content_generator=_build_content_generator(model_name),
            )
            message = (
                f"Research pipeline `{result.quest_id}` returned `{result.status}` at stage `{result.final_stage}`. "
                f"Stages executed: {len(result.stages_executed)}."
            )
            if result.blocked_gate:
                message += f" Blocked gate: `{result.blocked_gate}`."
            if result.error:
                message += f" Error: {result.error}"
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
            raise ValueError("action must be one of: start, status, advance, gate, run_pipeline")
    except Exception as exc:
        await db.close()
        return Command(update={"messages": [ToolMessage(f"Error: {exc}", tool_call_id=tool_call_id)]})

    await db.close()
    return Command(update={"messages": [ToolMessage(message, tool_call_id=tool_call_id)]})
