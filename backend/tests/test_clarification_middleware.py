from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import ToolMessage
from langgraph.graph import END
from langgraph.prebuilt.tool_node import ToolCallRequest

from medrix_flow.agents.middlewares.clarification_middleware import ClarificationMiddleware


def _request(*, synthetic_data_mode: bool, question: str, context: str | None = None) -> ToolCallRequest:
    return ToolCallRequest(
        tool_call={
            "name": "ask_clarification",
            "id": "tc-clarify",
            "args": {
                "question": question,
                "clarification_type": "missing_info",
                "context": context,
                "options": [
                    "Upload full data and parameters",
                    "Use assumptions to continue",
                ],
            },
        },
        tool=None,
        state={},
        runtime=SimpleNamespace(context={"synthetic_data_mode": synthetic_data_mode}),
    )


def test_synthetic_mode_suppresses_experiment_data_clarification() -> None:
    middleware = ClarificationMiddleware()
    called = False

    def handler(request: ToolCallRequest) -> ToolMessage:
        nonlocal called
        called = True
        return ToolMessage("should not run", tool_call_id="tc-clarify")

    result = middleware.wrap_tool_call(
        _request(
            synthetic_data_mode=True,
            question="请上传完整赛题、实验数据、参数、消融设定、图表数值、页数、引用格式和附录要求。",
            context="The PDF paper needs complete experimental results and format requirements.",
        ),
        handler,
    )

    assert called is False
    assert result.goto != END
    assert result.update is not None
    message = result.update["messages"][0]
    assert message.name == "ask_clarification"
    assert "Synthetic Experiment Mode is enabled" in str(message.content)
    assert "Continue by generating reasonable simulation assumptions" in str(message.content)


def test_normal_mode_still_interrupts_for_missing_experiment_data() -> None:
    middleware = ClarificationMiddleware()

    result = middleware.wrap_tool_call(
        _request(
            synthetic_data_mode=False,
            question="Please provide experiment data and parameters.",
        ),
        lambda request: ToolMessage("unused", tool_call_id="tc-clarify"),
    )

    assert result.goto == END
    assert result.update is not None
    message = result.update["messages"][0]
    assert message.name == "ask_clarification"
    assert message.additional_kwargs["clarification"]["question"] == "Please provide experiment data and parameters."


def test_synthetic_mode_still_interrupts_for_official_template_requirements() -> None:
    middleware = ClarificationMiddleware()

    result = middleware.wrap_tool_call(
        _request(
            synthetic_data_mode=True,
            question="Please upload the official contest statement, exact template, page limit, and citation style.",
        ),
        lambda request: ToolMessage("unused", tool_call_id="tc-clarify"),
    )

    assert result.goto == END
    assert result.update is not None
    message = result.update["messages"][0]
    assert message.name == "ask_clarification"
    assert "official contest statement" in str(message.content)
