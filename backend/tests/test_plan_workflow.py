from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import END
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from medrix_flow.agents.lead_agent import prompt as prompt_module
from medrix_flow.agents.middlewares.plan_middleware import PlanMiddleware
from medrix_flow.agents.plan_state import build_plan_state
from medrix_flow.tools.builtins.plan_tool import write_plan_tool


def test_write_plan_stores_awaiting_approval_plan_and_stops() -> None:
    runtime = SimpleNamespace(state={})

    result = write_plan_tool.func(
        runtime=runtime,
        summary="Build a literature-backed experiment bundle",
        phases=["Survey benchmarks", "Design ablations"],
        deliverables=["experiment_contract.json", "manuscript.tex"],
        open_questions=["Target venue?"],
        acceptance_criteria=["Claims map to evidence"],
        risk_points=["Dataset access may be restricted"],
        status="approved",
        revision_note="Initial plan",
        tool_call_id="tc-plan",
    )

    assert isinstance(result, Command)
    assert result.goto == END
    plan = result.update["plan"]
    assert plan["status"] == "awaiting_approval"
    assert plan["revision_count"] == 1
    assert plan["phases"] == ["Survey benchmarks", "Design ablations"]
    assert isinstance(result.update["messages"][0], ToolMessage)


def test_write_plan_increments_revision_count() -> None:
    existing = build_plan_state(
        existing=None,
        summary="First draft",
        phases=["Phase 1"],
        deliverables=["draft.md"],
    )
    runtime = SimpleNamespace(state={"plan": existing})

    result = write_plan_tool.func(
        runtime=runtime,
        summary="Revised draft",
        phases=["Phase 1", "Phase 2"],
        deliverables=["draft.md", "audit.json"],
        tool_call_id="tc-plan",
    )

    plan = result.update["plan"]
    assert plan["revision_count"] == 2
    assert len(plan["revisions"]) == 2
    assert plan["summary"] == "Revised draft"


def test_plan_middleware_blocks_locked_tools_until_approved() -> None:
    middleware = PlanMiddleware()
    called = False

    def handler(request: ToolCallRequest) -> ToolMessage:
        nonlocal called
        called = True
        return ToolMessage("ok", tool_call_id="tc-tool")

    request = ToolCallRequest(
        tool_call={"name": "present_files", "id": "tc-tool", "args": {}},
        tool=None,
        state={},
        runtime=SimpleNamespace(state={"plan": {"status": "awaiting_approval"}}),
    )

    result = middleware.wrap_tool_call(request, handler)

    assert called is False
    assert isinstance(result, ToolMessage)
    assert result.status == "error"
    assert "Plan approval is required" in str(result.content)


def test_plan_middleware_blocks_file_writes_until_approved() -> None:
    middleware = PlanMiddleware()
    called = False

    def handler(request: ToolCallRequest) -> ToolMessage:
        nonlocal called
        called = True
        return ToolMessage("ok", tool_call_id="tc-tool")

    request = ToolCallRequest(
        tool_call={"name": "write_file", "id": "tc-tool", "args": {}},
        tool=None,
        state={},
        runtime=SimpleNamespace(state={"plan": {"status": "awaiting_approval"}}),
    )

    result = middleware.wrap_tool_call(request, handler)

    assert called is False
    assert isinstance(result, ToolMessage)
    assert result.status == "error"


def test_plan_middleware_allows_execution_after_approval() -> None:
    middleware = PlanMiddleware()
    called = False

    def handler(request: ToolCallRequest) -> ToolMessage:
        nonlocal called
        called = True
        return ToolMessage("ok", tool_call_id="tc-tool")

    request = ToolCallRequest(
        tool_call={"name": "present_files", "id": "tc-tool", "args": {}},
        tool=None,
        state={},
        runtime=SimpleNamespace(state={"plan": {"status": "approved"}}),
    )

    result = middleware.wrap_tool_call(request, handler)

    assert called is True
    assert isinstance(result, ToolMessage)
    assert result.content == "ok"


def test_plan_middleware_refreshes_plan_reminder_when_plan_changes() -> None:
    middleware = PlanMiddleware()
    state = {
        "messages": [
            HumanMessage(
                name="plan_state",
                content="<thread_plan>\nupdated_at: 2026-01-01T00:00:00+00:00\n</thread_plan>",
            )
        ],
        "plan": {
            "summary": "Updated plan",
            "status": "awaiting_approval",
            "updated_at": "2026-01-02T00:00:00+00:00",
        },
    }

    result = middleware.before_model(state, runtime=SimpleNamespace())

    assert result is not None
    assert result["messages"][0].name == "plan_state"
    assert "Updated plan" in result["messages"][0].content
    assert "updated_at: 2026-01-02T00:00:00+00:00" in result["messages"][0].content


def test_plan_prompt_section_is_only_in_plan_mode(monkeypatch) -> None:
    monkeypatch.setattr(prompt_module, "_get_memory_context", lambda agent_name=None, thread_id=None: "")
    monkeypatch.setattr(prompt_module, "get_agent_soul", lambda agent_name: "")
    monkeypatch.setattr(prompt_module, "get_skills_prompt_section", lambda available_skills=None: "")
    monkeypatch.setattr(prompt_module, "get_deferred_tools_prompt_section", lambda: "")
    monkeypatch.setattr(prompt_module, "load_skills", lambda enabled_only=True: [])

    normal = prompt_module.apply_prompt_template()
    plan_mode = prompt_module.apply_prompt_template(plan_mode=True)

    assert "<plan_mode_system>" not in normal
    assert "<plan_mode_system>" in plan_mode
    assert "write_plan" in plan_mode
