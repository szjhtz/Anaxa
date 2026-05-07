#!/usr/bin/env python3
"""Health checks for local MedrixFlow development/runtime prerequisites."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import yaml
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
HARNESS_ROOT = BACKEND_ROOT / "packages" / "harness"

sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(HARNESS_ROOT))

from medrix_flow.setup import collect_referenced_env_vars, find_config_path, find_env_path, read_raw_config  # noqa: E402
from medrix_flow.config.paths import Paths  # noqa: E402


def _ok(label: str, detail: str) -> bool:
    print(f"  ✓ {label}: {detail}")
    return True


def _fail(label: str, detail: str) -> bool:
    print(f"  ✗ {label}: {detail}")
    return False


def _check_config_version(raw_config: dict) -> bool:
    example_path = PROJECT_ROOT / "config.example.yaml"
    if not example_path.exists():
        return _fail("config version", "config.example.yaml is missing")

    with open(example_path, encoding="utf-8") as handle:
        example_config = yaml.safe_load(handle) or {}

    user_version = int(raw_config.get("config_version", 0) or 0)
    example_version = int(example_config.get("config_version", 0) or 0)
    if user_version < example_version:
        return _fail(
            "config version",
            f"config.yaml is version {user_version}, latest is {example_version} (run `make config-upgrade`)",
        )
    return _ok("config version", f"{user_version}")


def _check_models(raw_config: dict) -> bool:
    models = raw_config.get("models") or []
    if not models:
        return _fail("models", "no models configured")
    return _ok("models", f"{len(models)} configured")


def _check_env_vars(raw_config: dict) -> bool:
    env_file_values = dotenv_values(find_env_path())
    env_values = {**env_file_values, **os.environ}
    missing = sorted(
        name for name in collect_referenced_env_vars(raw_config) if not env_values.get(name)
    )
    if missing:
        return _fail("env vars", f"missing values for: {', '.join(missing)}")
    return _ok("env vars", "all referenced variables are present")


def _check_sandbox(raw_config: dict) -> bool:
    sandbox = raw_config.get("sandbox") or {}
    sandbox_use = str(sandbox.get("use", ""))
    if any(token in sandbox_use.lower() for token in ("aio", "docker", "container")):
        if shutil.which("docker") or shutil.which("container"):
            return _ok("sandbox prerequisites", "container runtime available")
        return _fail("sandbox prerequisites", "docker/container runtime not found")
    return _ok("sandbox prerequisites", "local sandbox path selected")


def _check_writable_path(label: str, path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8"):
            pass
    except Exception as exc:
        return _fail(label, f"{path} is not writable ({exc})")
    return _ok(label, str(path))


def _check_runtime_and_checkpointer(raw_config: dict) -> bool:
    base_dir = Path(os.getenv("MEDRIX_FLOW_HOME", BACKEND_ROOT / ".medrix-flow"))
    paths = Paths(base_dir)
    results = [_check_writable_path("runtime db", paths.runtime_db_file)]

    checkpointer = raw_config.get("checkpointer") or {}
    if checkpointer.get("type") == "sqlite":
        conn = str(checkpointer.get("connection_string") or "checkpoints.db")
        target = Path(conn) if Path(conn).is_absolute() else base_dir / conn
        results.append(_check_writable_path("checkpointer db", target))
    return all(results)


def main() -> int:
    print("==========================================")
    print("  MedrixFlow Doctor")
    print("==========================================")
    print()

    try:
        config_path = find_config_path()
        raw_config = read_raw_config()
    except Exception as exc:
        print(f"  ✗ config: {exc}")
        return 1

    print(f"Config path: {config_path}")
    print(f"Env path:    {find_env_path()}")
    print()

    checks = [
        _check_config_version(raw_config),
        _check_models(raw_config),
        _check_env_vars(raw_config),
        _check_sandbox(raw_config),
        _check_runtime_and_checkpointer(raw_config),
    ]

    print()
    if all(checks):
        print("Doctor result: healthy")
        return 0

    print("Doctor result: issues found")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
