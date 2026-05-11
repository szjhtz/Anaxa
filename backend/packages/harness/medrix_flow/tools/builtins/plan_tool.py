"""Structured plan writer for plan-mode tasks."""

from __future__ import annotations

from typing import Annotated

from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.graph import END
from langgraph.types import Command
from langgraph.typing import ContextT

from medrix_flow.agents.plan_state import build_plan_state, normalize_plan_status
from medrix_flow.agents.thread_state import ThreadState


@tool("write_plan", parse_docstring=True)
def write_plan_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    summary: str,
    phases: list[str],
    deliverables: list[str],
    tool_call_id: Annotated[str, InjectedToolCallId],
    open_questions: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    risk_points: list[str] | None = None,
    status: str = "awaiting_approval",
    revision_note: str | None = None,
) -> Command:
    """Write or revise the structured plan for a complex task.

    Use this tool during plan mode to create a structured plan before any
    final execution. The plan is stored in thread state for the main
    conversation approval card.

    Args:
        summary: Short summary of the intended work.
        phases: Ordered list of phases or stages.
        deliverables: Expected outputs after approval.
        open_questions: Remaining unknowns or user decisions.
        acceptance_criteria: Conditions that should be met before completion.
        risk_points: Known risks, dependencies, or constraints.
        status: Plan status to record. Non-approved tool output is coerced to
            a pre-approval state so the user remains in control.
        revision_note: Optional note describing what changed in this revision.
    """
    try:
        if runtime.state is None:
            raise ValueError("Thread runtime state is not available")

        existing_plan = runtime.state.get("plan") or {}
        normalized_status = normalize_plan_status(status)
        if normalized_status == "approved":
            normalized_status = "awaiting_approval"

        plan = build_plan_state(
            existing=existing_plan if isinstance(existing_plan, dict) else None,
            summary=summary,
            phases=phases,
            deliverables=deliverables,
            open_questions=open_questions,
            acceptance_criteria=acceptance_criteria,
            risk_points=risk_points,
            status=normalized_status,
            source="agent",
            note=revision_note or summary,
        )
        message = (
            "Plan saved and awaiting approval."
            if plan.get("revision_count", 0) <= 1
            else "Plan revised and awaiting approval."
        )
        return Command(
            update={
                "plan": plan,
                "messages": [ToolMessage(message, tool_call_id=tool_call_id)],
            },
            goto=END,
        )
    except Exception as exc:
        return Command(update={"messages": [ToolMessage(f"Error: {exc}", tool_call_id=tool_call_id)]})
