from __future__ import annotations

from pathlib import Path

from medrix_flow.config import get_app_config
from medrix_flow.skills.storage.base import SkillStorage
from medrix_flow.skills.storage.local import LocalSkillStorage

_default_skill_storage: SkillStorage | None = None
_default_skill_storage_key: tuple[str, str] | None = None


def get_or_new_skill_storage(*, skills_path: str | Path | None = None) -> SkillStorage:
    global _default_skill_storage, _default_skill_storage_key

    if skills_path is not None:
        config = get_app_config()
        return LocalSkillStorage(
            host_path=skills_path,
            container_path=config.skills.container_path,
        )

    config = get_app_config()
    key = (str(config.skills.get_skills_path()), config.skills.container_path)
    if _default_skill_storage is None or _default_skill_storage_key != key:
        _default_skill_storage = LocalSkillStorage(
            host_path=config.skills.get_skills_path(),
            container_path=config.skills.container_path,
        )
        _default_skill_storage_key = key
    return _default_skill_storage


def reset_skill_storage() -> None:
    global _default_skill_storage, _default_skill_storage_key
    _default_skill_storage = None
    _default_skill_storage_key = None


__all__ = [
    "LocalSkillStorage",
    "SkillStorage",
    "get_or_new_skill_storage",
    "reset_skill_storage",
]
