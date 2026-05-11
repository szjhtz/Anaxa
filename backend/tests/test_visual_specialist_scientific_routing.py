from pathlib import Path

from medrix_flow.agents.lead_agent.prompt_enhancements import VISUAL_SKILL_NAMES
from medrix_flow.subagents.builtins.visual_specialist import VISUAL_SPECIALIST_CONFIG


def test_visual_skill_names_include_scientific_image_prompting() -> None:
    assert "scientific-image-prompting" in VISUAL_SKILL_NAMES


def test_visual_specialist_prompt_contains_scientific_routing_contract() -> None:
    prompt = VISUAL_SPECIALIST_CONFIG.system_prompt
    assert "data_figure" in prompt
    assert "deterministic_diagram" in prompt
    assert "ai_scientific_illustration" in prompt
    assert "scientific-image-prompting" in prompt
    assert "currently active image provider/model from Settings" in prompt


def test_visual_prompt_requires_visual_intent(monkeypatch) -> None:
    from medrix_flow.agents.lead_agent import prompt as prompt_module
    from medrix_flow.skills.types import Skill

    visual_skill = Skill(
        name="chart-visualization",
        description="Make charts",
        license=None,
        skill_dir=Path("/tmp/chart-visualization"),
        skill_file=Path("/tmp/chart-visualization/SKILL.md"),
        relative_path=Path("chart-visualization"),
        category="public",
        enabled=True,
    )

    monkeypatch.setattr(prompt_module, "_get_memory_context", lambda agent_name=None, thread_id=None: "")
    monkeypatch.setattr(prompt_module, "get_agent_soul", lambda agent_name: "")
    monkeypatch.setattr(prompt_module, "get_skills_prompt_section", lambda available_skills=None: "")
    monkeypatch.setattr(prompt_module, "get_deferred_tools_prompt_section", lambda: "")
    monkeypatch.setattr(prompt_module, "load_skills", lambda enabled_only=True: [visual_skill])

    non_visual = prompt_module.apply_prompt_template()
    visual = prompt_module.apply_prompt_template(visual_output_intent=True)

    assert "<visual_quality_system>" not in non_visual
    assert "<visual_quality_system>" in visual


def test_synthetic_data_mode_prompt_is_explicitly_gated(monkeypatch) -> None:
    from medrix_flow.agents.lead_agent import prompt as prompt_module

    monkeypatch.setattr(prompt_module, "_get_memory_context", lambda agent_name=None, thread_id=None: "")
    monkeypatch.setattr(prompt_module, "get_agent_soul", lambda agent_name: "")
    monkeypatch.setattr(prompt_module, "get_skills_prompt_section", lambda available_skills=None: "")
    monkeypatch.setattr(prompt_module, "get_deferred_tools_prompt_section", lambda: "")
    monkeypatch.setattr(prompt_module, "load_skills", lambda enabled_only=True: [])

    normal = prompt_module.apply_prompt_template()
    synthetic = prompt_module.apply_prompt_template(synthetic_data_mode=True)

    assert "<synthetic_data_mode>" not in normal
    assert "<synthetic_data_mode>" in synthetic
    assert "supported_by_simulation" in synthetic
    assert "Never fabricate third-party objective facts" in synthetic
    assert "SYNTHETIC EXPERIMENT MODE OVERRIDE" in synthetic
    assert "Do NOT call `ask_clarification` merely because experiment data" in synthetic
    assert synthetic.index("<synthetic_data_mode>") < synthetic.index("<clarification_system>")


def test_visual_quality_tools_require_visual_intent(monkeypatch) -> None:
    from medrix_flow.tools import tools as tools_module

    class _Config:
        tools = []
        models = []
        tool_search = type("ToolSearch", (), {"enabled": False})()

        def get_model_config(self, model_name):
            return None

    class _Skill:
        name = "chart-visualization"

    monkeypatch.setattr(tools_module, "get_app_config", lambda: _Config())
    monkeypatch.setattr("medrix_flow.skills.load_skills", lambda enabled_only=True: [_Skill()])

    non_visual = tools_module.get_available_tools(visual_output_intent=False, include_mcp=False)
    visual = tools_module.get_available_tools(visual_output_intent=True, include_mcp=False)

    non_visual_names = {tool.name for tool in non_visual}
    visual_names = {tool.name for tool in visual}

    assert "visual_quality_check" not in non_visual_names
    assert "visual_refinement_check" not in non_visual_names
    assert "visual_quality_check" in visual_names
    assert "visual_refinement_check" in visual_names
