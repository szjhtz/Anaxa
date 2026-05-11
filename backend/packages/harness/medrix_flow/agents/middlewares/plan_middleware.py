"""Middleware for thread-level plan state injection and execution gating."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import Command

from medrix_flow.agents.plan_state import PLAN_LOCKED_TOOL_NAMES, PlanState, format_plan_for_prompt, plan_is_approved


class PlanMiddlewareState(AgentState):
    """Compatible with the `ThreadState` schema."""

    plan: NotRequired[PlanState | None]


def _plan_reminder_in_messages(messages: list[Any], plan: PlanState) -> bool:
    updated_at = plan.get("updated_at")
    for msg in messages:
        if not (isinstance(msg, HumanMessage) and getattr(msg, "name", None) == "plan_state"):
            continue
        if not updated_at:
            return True
        content = getattr(msg, "content", "")
        if isinstance(content, str) and f"updated_at: {updated_at}" in content:
            return True
    return False


def _plan_content(plan: PlanState) -> str:
    return format_plan_for_prompt(plan)


def _blocked_tool_message(request: ToolCallRequest, tool_name: str, status: str | None) -> ToolMessage:
    tool_call_id = str(request.tool_call.get("id") or "missing_id")
    status_label = status or "awaiting_approval"
    return ToolMessage(
        content=(
            f"Plan approval is required before using `{tool_name}`. "
            f"Current plan status: `{status_label}`. "
            "Please write or revise the plan first, then wait for the user to confirm it."
        ),
        tool_call_id=tool_call_id,
        name=tool_name,
        status="error",
    )


class PlanMiddleware(AgentMiddleware[PlanMiddlewareState]):
    """Inject the current plan into context and block execution before approval."""

    state_schema = PlanMiddlewareState

    def before_model(self, state: PlanMiddlewareState, runtime: Runtime) -> dict[str, Any] | None:  # noqa: ARG002
        plan = state.get("plan") or {}
        if not plan:
            return None

        messages = state.get("messages") or []
        if _plan_reminder_in_messages(messages, plan):
            return None

        reminder = HumanMessage(
            name="plan_state",
            content=(
                "<system_reminder>\n"
                "Current thread plan:\n"
                f"{_plan_content(plan)}\n"
                "If the plan is not approved yet, revise it or ask clarification. "
                "Do not start final execution until the user confirms the plan.\n"
                "</system_reminder>"
            ),
        )
        return {"messages": [reminder]}

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        tool_name = str(request.tool_call.get("name") or "")
        if tool_name == "ask_clarification" or tool_name == "write_plan":
            return handler(request)

        if tool_name not in PLAN_LOCKED_TOOL_NAMES:
            return handler(request)

        runtime = request.runtime
        state = getattr(runtime, "state", None) if runtime is not None else None
        plan = state.get("plan") if isinstance(state, dict) else None
        if plan_is_approved(plan):
            return handler(request)

        return _blocked_tool_message(request, tool_name, str((plan or {}).get("status")) if isinstance(plan, dict) else None)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        tool_name = str(request.tool_call.get("name") or "")
        if tool_name == "ask_clarification" or tool_name == "write_plan":
            return await handler(request)

        if tool_name not in PLAN_LOCKED_TOOL_NAMES:
            return await handler(request)

        runtime = request.runtime
        state = getattr(runtime, "state", None) if runtime is not None else None
        plan = state.get("plan") if isinstance(state, dict) else None
        if plan_is_approved(plan):
            return await handler(request)

        return _blocked_tool_message(request, tool_name, str((plan or {}).get("status")) if isinstance(plan, dict) else None)
