"""Abstract storage interface for custom skill lifecycle management."""

from __future__ import annotations

import re
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from medrix_flow.skills.types import SKILL_MD_FILE

_SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillStorage(ABC):
    def __init__(self, container_path: str = "/mnt/skills") -> None:
        self._container_root = container_path

    @staticmethod
    def validate_skill_name(name: str) -> str:
        normalized = name.strip()
        if not _SKILL_NAME_PATTERN.fullmatch(normalized):
            raise ValueError("Skill name must be hyphen-case using lowercase letters, digits, and hyphens only.")
        if len(normalized) > 64:
            raise ValueError("Skill name must be 64 characters or fewer.")
        return normalized

    @staticmethod
    def validate_relative_path(relative_path: str, base_dir: Path) -> Path:
        if not relative_path:
            raise ValueError("relative_path must not be empty.")
        resolved_base = base_dir.resolve()
        target = (resolved_base / relative_path).resolve()
        try:
            target.relative_to(resolved_base)
        except ValueError as exc:
            raise ValueError("relative_path must resolve within the skill directory.") from exc
        return target

    @staticmethod
    def validate_skill_markdown_content(name: str, content: str) -> None:
        from medrix_flow.skills.validation import _validate_skill_frontmatter

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_skill_dir = Path(tmp_dir) / SkillStorage.validate_skill_name(name)
            temp_skill_dir.mkdir(parents=True, exist_ok=True)
            (temp_skill_dir / SKILL_MD_FILE).write_text(content, encoding="utf-8")
            is_valid, message, parsed_name = _validate_skill_frontmatter(temp_skill_dir)
            if not is_valid:
                raise ValueError(message)
            if parsed_name != name:
                raise ValueError(f"Frontmatter name '{parsed_name}' must match requested skill name '{name}'.")

    def get_container_root(self) -> str:
        return self._container_root

    @abstractmethod
    def get_skills_root_path(self) -> Path:
        raise NotImplementedError

    def get_custom_skill_dir(self, name: str) -> Path:
        normalized_name = self.validate_skill_name(name)
        return self.get_skills_root_path() / "custom" / normalized_name

    def get_custom_skill_file(self, name: str) -> Path:
        normalized_name = self.validate_skill_name(name)
        return self.get_custom_skill_dir(normalized_name) / SKILL_MD_FILE

    def get_skill_history_file(self, name: str) -> Path:
        normalized_name = self.validate_skill_name(name)
        return self.get_skills_root_path() / "custom" / ".history" / f"{normalized_name}.jsonl"

    def ensure_custom_skill_is_editable(self, name: str) -> None:
        if self.custom_skill_exists(name):
            return
        if self.public_skill_exists(name):
            raise ValueError(f"'{name}' is a built-in skill. To customise it, create a new skill with the same name under skills/custom/.")
        raise FileNotFoundError(f"Custom skill '{name}' not found.")

    @abstractmethod
    def load_skills(self, *, enabled_only: bool = False) -> list:
        raise NotImplementedError

    @abstractmethod
    def read_custom_skill(self, name: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def write_custom_skill(self, name: str, relative_path: str, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_skill_from_archive(self, archive_path: str | Path) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete_custom_skill(self, name: str, *, history_meta: dict | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def custom_skill_exists(self, name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def public_skill_exists(self, name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def append_history(self, name: str, record: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_history(self, name: str) -> list[dict]:
        raise NotImplementedError
