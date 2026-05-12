"""Tests for recursive skills loading."""

import re
from pathlib import Path

from medrix_flow.agents.lead_agent.prompt import clear_skills_system_prompt_cache, get_skills_prompt_section
from medrix_flow.config.extensions_config import reset_extensions_config
from medrix_flow.skills.loader import get_skills_root_path, invalidate_skills_cache, load_skills
from medrix_flow.skills.types import Skill
from medrix_flow.skills.validation import _validate_skill_frontmatter


def _write_skill(skill_dir: Path, name: str, description: str) -> None:
    """Write a minimal SKILL.md for tests."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_get_skills_root_path_points_to_project_root_skills():
    """get_skills_root_path() should point to medrix-flow/skills (sibling of backend/), not backend/packages/skills."""
    path = get_skills_root_path()
    assert path.name == "skills", f"Expected 'skills', got '{path.name}'"
    assert (path.parent / "backend").is_dir(), (
        f"Expected skills path's parent to be project root containing 'backend/', but got {path}"
    )


def test_load_skills_discovers_nested_skills_and_sets_container_paths(tmp_path: Path):
    """Nested skills should be discovered recursively with correct container paths."""
    skills_root = tmp_path / "skills"

    _write_skill(skills_root / "public" / "root-skill", "root-skill", "Root skill")
    _write_skill(skills_root / "public" / "parent" / "child-skill", "child-skill", "Child skill")
    _write_skill(skills_root / "custom" / "team" / "helper", "team-helper", "Team helper")

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    by_name = {skill.name: skill for skill in skills}

    assert {"root-skill", "child-skill", "team-helper"} <= set(by_name)

    root_skill = by_name["root-skill"]
    child_skill = by_name["child-skill"]
    team_skill = by_name["team-helper"]

    assert root_skill.skill_path == "root-skill"
    assert root_skill.get_container_file_path() == "/mnt/skills/public/root-skill/SKILL.md"

    assert child_skill.skill_path == "parent/child-skill"
    assert child_skill.get_container_file_path() == "/mnt/skills/public/parent/child-skill/SKILL.md"

    assert team_skill.skill_path == "team/helper"
    assert team_skill.get_container_file_path() == "/mnt/skills/custom/team/helper/SKILL.md"


def test_load_skills_skips_hidden_directories(tmp_path: Path):
    """Hidden directories should be excluded from recursive discovery."""
    skills_root = tmp_path / "skills"

    _write_skill(skills_root / "public" / "visible" / "ok-skill", "ok-skill", "Visible skill")
    _write_skill(
        skills_root / "public" / "visible" / ".hidden" / "secret-skill",
        "secret-skill",
        "Hidden skill",
    )

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    names = {skill.name for skill in skills}

    assert "ok-skill" in names
    assert "secret-skill" not in names


def test_custom_skill_overrides_public_skill_with_same_name(tmp_path: Path):
    skills_root = tmp_path / "skills"

    _write_skill(skills_root / "public" / "shared", "shared-skill", "Public version")
    _write_skill(skills_root / "custom" / "shared", "shared-skill", "Custom version")

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    matches = [skill for skill in skills if skill.name == "shared-skill"]

    assert len(matches) == 1
    assert matches[0].category == "custom"
    assert matches[0].description == "Custom version"


def test_all_public_skills_parse_and_follow_name_conventions():
    """Built-in skills should not fail silently at runtime."""
    public_root = get_skills_root_path() / "public"
    skill_files = sorted(public_root.glob("*/SKILL.md"))
    assert skill_files
    directory_name_exceptions = {"vercel-deploy-claimable": "vercel-deploy"}

    for skill_file in skill_files:
        is_valid, message, parsed_name = _validate_skill_frontmatter(skill_file.parent)
        assert is_valid, f"{skill_file}: {message}"
        expected_name = directory_name_exceptions.get(skill_file.parent.name, skill_file.parent.name)
        assert parsed_name == expected_name, f"{skill_file}: frontmatter name {parsed_name!r} must be {expected_name!r}"

    skills = load_skills(enabled_only=True)
    names = {skill.name for skill in skills if skill.category == "public"}
    expected_names = {directory_name_exceptions.get(skill_file.parent.name, skill_file.parent.name) for skill_file in skill_files}
    assert expected_names <= names
    assert "bootstrap" in names


def test_skills_prompt_contains_metadata_not_skill_bodies(monkeypatch):
    """The main prompt may list skills, but should not inline SKILL.md bodies."""
    monkeypatch.setattr(
        "medrix_flow.config.get_app_config",
        lambda: type("Config", (), {"skills": type("Skills", (), {"container_path": "/mnt/skills"})()})(),
    )
    clear_skills_system_prompt_cache()

    rendered = get_skills_prompt_section()

    assert "<available_skills>" in rendered
    assert "<name>bootstrap</name>" in rendered
    assert "<location>/mnt/skills/public/bootstrap/SKILL.md</location>" in rendered
    assert "# Bootstrap Soul" not in rendered
    assert "# Deep Research Skill" not in rendered
    assert "## Workflow" not in rendered


def test_empirical_methods_guidance_uses_available_skill_path(monkeypatch, tmp_path: Path):
    from medrix_flow.agents.lead_agent import prompt as prompt_module

    skill = Skill(
        name="empirical-research-methods",
        description="Empirical methods",
        license=None,
        skill_dir=tmp_path / "custom" / "empirical-research-methods",
        skill_file=tmp_path / "custom" / "empirical-research-methods" / "SKILL.md",
        relative_path=Path("empirical-research-methods"),
        category="custom",
        enabled=True,
    )
    monkeypatch.setattr(prompt_module, "load_skills", lambda enabled_only=True: [skill])
    monkeypatch.setattr(
        "medrix_flow.config.get_app_config",
        lambda: type("Config", (), {"skills": type("Skills", (), {"container_path": "/custom/skills"})()})(),
    )

    rendered = prompt_module.get_empirical_research_methods_guidance()
    assert "/custom/skills/custom/empirical-research-methods/SKILL.md" in rendered
    assert prompt_module.get_empirical_research_methods_guidance({"bootstrap"}) == ""


def test_legacy_skill_key_controls_renamed_skill(monkeypatch, tmp_path: Path) -> None:
    extensions_path = tmp_path / "extensions_config.json"
    extensions_path.write_text(
        '{"mcpServers": {}, "skills": {"claude-to-medrix_flow": {"enabled": false}}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("MEDRIX_FLOW_EXTENSIONS_CONFIG_PATH", str(extensions_path))
    reset_extensions_config()
    try:
        invalidate_skills_cache()
        skills = load_skills(enabled_only=False)
        renamed = next(skill for skill in skills if skill.name == "claude-to-medrixflow")
        assert renamed.enabled is False
    finally:
        reset_extensions_config()
        invalidate_skills_cache()


def test_public_skill_text_preserves_progressive_disclosure_boundaries():
    public_root = get_skills_root_path() / "public"
    bodies = {
        skill_file.parent.name: skill_file.read_text(encoding="utf-8")
        for skill_file in sorted(public_root.glob("*/SKILL.md"))
    }

    assert "Read all the skills listed" not in bodies["surprise-me"]
    assert "ANY question" not in bodies["deep-research"]
    assert "before content generation tasks" not in bodies["deep-research"]

    frontend_body = bodies["frontend-design"]
    assert "standalone generated HTML projects" in frontend_body
    assert "does not apply when editing an existing product codebase" in frontend_body

    fireworks_frontmatter = re.search(r"^---\n(.*?)\n---", bodies["fireworks-tech-graph"], re.DOTALL)
    assert fireworks_frontmatter is not None
    assert "real data" in fireworks_frontmatter.group(1)
