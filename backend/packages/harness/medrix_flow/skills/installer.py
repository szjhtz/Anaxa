"""Shared archive installation helpers for custom skills."""

from __future__ import annotations

import posixpath
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from .security_scanner import scan_skill_content

_PROMPT_INPUT_DIRS = {"references", "templates", "assets"}
_PROMPT_INPUT_SUFFIXES = frozenset({".json", ".markdown", ".md", ".rst", ".txt", ".yaml", ".yml"})


class SkillAlreadyExistsError(ValueError):
    """Raised when a skill with the same name already exists."""


class SkillSecurityScanError(ValueError):
    """Raised when an archive member is blocked by the security scanner."""


def is_unsafe_zip_member(info: zipfile.ZipInfo) -> bool:
    name = info.filename
    if not name:
        return False
    normalized = name.replace("\\", "/")
    if normalized.startswith("/"):
        return True
    path = PurePosixPath(normalized)
    if path.is_absolute() or PureWindowsPath(name).is_absolute():
        return True
    return ".." in path.parts


def is_symlink_member(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)


def should_ignore_archive_entry(path: Path) -> bool:
    return path.name.startswith(".") or path.name == "__MACOSX"


def resolve_skill_dir_from_archive(temp_path: Path) -> Path:
    items = [item for item in temp_path.iterdir() if not should_ignore_archive_entry(item)]
    if not items:
        raise ValueError("Skill archive is empty")
    if len(items) == 1 and items[0].is_dir():
        return items[0]
    return temp_path


def safe_extract_skill_archive(
    zip_ref: zipfile.ZipFile,
    dest_path: Path,
    max_total_size: int = 512 * 1024 * 1024,
) -> None:
    dest_root = dest_path.resolve()
    total_written = 0

    for info in zip_ref.infolist():
        if is_unsafe_zip_member(info):
            raise ValueError(f"Archive contains unsafe member path: {info.filename!r}")

        if is_symlink_member(info):
            continue

        normalized_name = posixpath.normpath(info.filename.replace("\\", "/"))
        member_path = dest_root.joinpath(*PurePosixPath(normalized_name).parts)
        if not member_path.resolve().is_relative_to(dest_root):
            raise ValueError(f"Zip entry escapes destination: {info.filename!r}")
        member_path.parent.mkdir(parents=True, exist_ok=True)

        if info.is_dir():
            member_path.mkdir(parents=True, exist_ok=True)
            continue

        with zip_ref.open(info) as src, member_path.open("wb") as dst:
            while chunk := src.read(65536):
                total_written += len(chunk)
                if total_written > max_total_size:
                    raise ValueError("Skill archive is too large or appears highly compressed.")
                dst.write(chunk)


def _is_script_support_file(rel_path: Path) -> bool:
    return bool(rel_path.parts) and rel_path.parts[0] == "scripts"


def _should_scan_support_file(rel_path: Path) -> bool:
    if _is_script_support_file(rel_path):
        return True
    return bool(rel_path.parts) and rel_path.parts[0] in _PROMPT_INPUT_DIRS and rel_path.suffix.lower() in _PROMPT_INPUT_SUFFIXES


def move_staged_skill_into_reserved_target(staging_target: Path, target: Path) -> None:
    installed = False
    reserved = False
    try:
        target.mkdir(mode=0o700)
        reserved = True
        for child in staging_target.iterdir():
            shutil.move(str(child), target / child.name)
        installed = True
    except FileExistsError as exc:
        raise SkillAlreadyExistsError(f"Skill '{target.name}' already exists") from exc
    finally:
        if reserved and not installed and target.exists():
            shutil.rmtree(target)


def scan_skill_archive_contents_or_raise(skill_dir: Path, skill_name: str) -> None:
    skill_md = skill_dir / "SKILL.md"
    result = scan_skill_content(skill_md.read_text(encoding="utf-8"), executable=False, location=f"{skill_name}/SKILL.md")
    if result.decision == "block":
        raise SkillSecurityScanError(f"Security scan blocked skill '{skill_name}': {result.reason}")

    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(skill_dir)
        if rel_path == Path("SKILL.md"):
            continue
        if path.name == "SKILL.md":
            raise SkillSecurityScanError(
                f"Security scan failed for skill '{skill_name}': nested SKILL.md is not allowed at {skill_name}/{rel_path.as_posix()}",
            )
        if not _should_scan_support_file(rel_path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise SkillSecurityScanError(
                f"Security scan failed for skill '{skill_name}': {rel_path.as_posix()} must be valid UTF-8",
            ) from exc
        result = scan_skill_content(
            content,
            executable=_is_script_support_file(rel_path),
            location=f"{skill_name}/{rel_path.as_posix()}",
        )
        if result.decision == "block":
            raise SkillSecurityScanError(f"Security scan blocked {skill_name}/{rel_path.as_posix()}: {result.reason}")
