from __future__ import annotations

import importlib
from types import SimpleNamespace

from medrix_flow.config.app_config import AppConfig, ResearchConfig
from medrix_flow.config.sandbox_config import SandboxConfig
from medrix_flow.research import PipelineRunResult

research_tool_module = importlib.import_module("medrix_flow.tools.builtins.research_assistant_tool")


def _make_runtime(tmp_path, *, model_name: str | None = "thread-model") -> SimpleNamespace:
    context = {"thread_id": "thread-research-tool"}
    if model_name:
        context["model_name"] = model_name
    return SimpleNamespace(
        state={},
        context=context,
        config={"configurable": {"model_name": model_name}} if model_name else {},
    )


def _make_config() -> AppConfig:
    return AppConfig(
        models=[],
        sandbox=SandboxConfig(use="medrix_flow.sandbox.local:LocalSandboxProvider"),
        research=ResearchConfig(
            manuscript_model="configured-manuscript-model",
            default_auto_gates=["pre_review"],
            default_max_stages=4,
            default_quality_mode="strict_gate",
            default_quality_repair_budget=1,
        ),
    )


def test_research_assistant_run_pipeline_action_dispatches(monkeypatch, tmp_path):
    captured: dict = {}
    generated = {}

    class DummyPaths:
        research_db_file = tmp_path / "research.sqlite3"

    async def fake_run_pipeline(self, quest_id, **kwargs):
        captured["quest_id"] = quest_id
        captured.update(kwargs)
        generated["content"] = await kwargs["content_generator"]("introduction", SimpleNamespace())
        return PipelineRunResult(
            quest_id=quest_id,
            status="stopped_at_max_stages",
            final_stage="evidence_verified",
            message="stopped",
        )

    def fake_build_content_generator(model_name):
        captured["model_name"] = model_name

        async def generate(section_key, snapshot):
            return f"{model_name}:{section_key}:{type(snapshot).__name__}"

        return generate

    monkeypatch.setattr(research_tool_module, "get_paths", lambda: DummyPaths())
    monkeypatch.setattr(research_tool_module, "get_app_config", _make_config)
    monkeypatch.setattr(research_tool_module, "_build_content_generator", fake_build_content_generator)
    monkeypatch.setattr(research_tool_module.ResearchQuestOrchestrator, "run_pipeline", fake_run_pipeline)

    result = research_tool_module.research_assistant_tool.coroutine(
        runtime=_make_runtime(tmp_path),
        tool_call_id="tc-research",
        action="run_pipeline",
        quest_id="rq-existing",
        auto_gates=["experiment_execution"],
        max_stages=2,
        quality_mode="audit_only",
        quality_repair_budget=3,
    )

    import asyncio

    command = asyncio.run(result)
    message = command.update["messages"][0].content

    assert captured["quest_id"] == "rq-existing"
    assert captured["auto_gates"] == ["experiment_execution"]
    assert captured["max_stages"] == 2
    assert captured["quality_mode"] == "audit_only"
    assert captured["repair_budget"] == 3
    assert captured["model_name"] == "configured-manuscript-model"
    assert generated["content"] == "configured-manuscript-model:introduction:SimpleNamespace"
    assert "Research pipeline `rq-existing` returned `stopped_at_max_stages`" in message


def test_research_assistant_run_pipeline_uses_config_defaults(monkeypatch, tmp_path):
    captured: dict = {}

    class DummyPaths:
        research_db_file = tmp_path / "research.sqlite3"

    async def fake_run_pipeline(self, quest_id, **kwargs):
        captured.update(kwargs)
        return PipelineRunResult(
            quest_id=quest_id,
            status="blocked_on_gate",
            final_stage="experiment_planned",
            blocked_gate="experiment_execution",
            message="blocked",
        )

    monkeypatch.setattr(research_tool_module, "get_paths", lambda: DummyPaths())
    monkeypatch.setattr(research_tool_module, "get_app_config", _make_config)
    monkeypatch.setattr(research_tool_module, "_build_content_generator", lambda model_name: captured.setdefault("model_name", model_name))
    monkeypatch.setattr(research_tool_module.ResearchQuestOrchestrator, "run_pipeline", fake_run_pipeline)

    import asyncio

    command = asyncio.run(
        research_tool_module.research_assistant_tool.coroutine(
            runtime=_make_runtime(tmp_path),
            tool_call_id="tc-research",
            action="run_pipeline",
            quest_id="rq-existing",
        )
    )

    assert captured["auto_gates"] == ["pre_review"]
    assert captured["max_stages"] == 4
    assert captured["quality_mode"] == "strict_gate"
    assert captured["repair_budget"] == 1
    assert captured["model_name"] == "configured-manuscript-model"
    assert "Blocked gate: `experiment_execution`." in command.update["messages"][0].content
